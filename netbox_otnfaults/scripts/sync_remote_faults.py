from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import re
from typing import Any

import requests
from dcim.models import Region, Site
from django.contrib.auth import get_user_model
from django.db import transaction
from extras.scripts import BooleanVar, IntegerVar, Script, StringVar
from netbox_contract.models import ServiceProvider

from netbox_otnfaults.models import (
    BareFiberService,
    CircuitService,
    OtnFault,
    OtnFaultImpact,
)


DATETIME_FIELDS = {
    "fault_occurrence_time",
    "fault_recovery_time",
    "dispatch_time",
    "departure_time",
    "arrival_time",
    "repair_time",
    "closure_time",
    "manager_review_time",
    "noc_review_time",
    "service_interruption_time",
    "service_recovery_time",
}

DECIMAL_FIELDS = {
    "interruption_longitude",
    "interruption_latitude",
}

PROVINCE_SUFFIXES = [
    "壮族自治区",
    "回族自治区",
    "维吾尔自治区",
    "特别行政区",
    "自治区",
    "省",
    "市",
]

SITE_REDUNDANT_SUFFIX_RE = re.compile(r"[(（]?(机房|节点|中心)[)）]?$")


class SyncResult:
    def __init__(self, status: str, instance: Any | None = None, reason: str | None = None) -> None:
        self.status = status
        self.instance = instance
        self.reason = reason


def build_api_session(api_token: str) -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"Accept": "application/json"})
    if api_token:
        session.headers["Authorization"] = f"Token {api_token}"
    return session


def fetch_paginated_api(
    session: requests.Session,
    url: str,
    *,
    verify_ssl: bool,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_url = url
    next_params = params

    while next_url:
        response = session.get(next_url, params=next_params, timeout=30, verify=verify_ssl)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "results" not in payload:
            raise ValueError(f"Unexpected API response from {next_url}")

        page_results = payload.get("results") or []
        if not isinstance(page_results, list):
            raise ValueError(f"Unexpected results payload from {next_url}")

        results.extend(page_results)
        next_url = payload.get("next")
        next_params = None

    return results


def fetch_paginated_api_from_candidates(
    session: requests.Session,
    candidate_urls: list[str],
    *,
    verify_ssl: bool,
    params: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    last_error: Exception | None = None

    for candidate_url in candidate_urls:
        try:
            return (
                fetch_paginated_api(
                    session,
                    candidate_url,
                    verify_ssl=verify_ssl,
                    params=params,
                ),
                candidate_url,
            )
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code == 404:
                last_error = exc
                continue
            raise

    if last_error is not None:
        raise last_error
    raise ValueError("No API candidate URLs were provided")


def build_api_collection_candidates(base_url: str, collection: str) -> list[str]:
    prefixes = [
        "netbox_otnfaults",
        "otnfaults",
        "netbox_otnfaults-api",
    ]
    return [f"{base_url}/api/plugins/{prefix}/{collection}/" for prefix in prefixes]


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_scalar(field_name: str, value: Any) -> Any:
    if field_name in DATETIME_FIELDS:
        return _parse_datetime(value)
    if field_name in DECIMAL_FIELDS:
        return _parse_decimal(value)
    return value


def _first_match(model: Any, **criteria: Any) -> Any | None:
    return model.objects.filter(**criteria).first()


def _candidate_values(payload: dict[str, Any] | None, keys: list[str]) -> list[str]:
    if not payload:
        return []

    values: list[str] = []
    for key in keys:
        value = payload.get(key)
        if value in (None, ""):
            continue
        normalized = str(value).strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def _object_value(obj: Any, attr_name: str) -> str | None:
    value = getattr(obj, attr_name, None)
    if callable(value):
        value = value()
    if value in (None, ""):
        return None
    return str(value).strip()


def _match_from_text_values(model: Any, values: list[str], attr_names: list[str]) -> Any | None:
    if not values:
        return None

    for obj in model.objects.all():
        for attr_name in attr_names:
            obj_value = _object_value(obj, attr_name)
            if obj_value and obj_value in values:
                return obj
    return None


def _normalize_region_text(value: str) -> str:
    normalized = value.strip()
    if "/" in normalized:
        normalized = normalized.split("/")[-1].strip()
    for suffix in PROVINCE_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _expand_region_values(values: list[str]) -> list[str]:
    expanded: list[str] = []
    for value in values:
        for candidate in (value, _normalize_region_text(value)):
            if candidate and candidate not in expanded:
                expanded.append(candidate)
    return expanded


def _normalize_site_text(value: str) -> str:
    normalized = value.strip()
    normalized = SITE_REDUNDANT_SUFFIX_RE.sub("", normalized).strip()
    return "".join(ch.lower() for ch in normalized if ch.isalnum())


def _expand_site_values(values: list[str]) -> list[str]:
    expanded: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in expanded:
            expanded.append(normalized)
        collapsed = _normalize_site_text(value)
        if collapsed and collapsed not in expanded:
            expanded.append(collapsed)
    return expanded


def _resolve_user(payload: dict[str, Any] | None) -> Any | None:
    if not payload:
        return None
    user_model = get_user_model()
    values = _candidate_values(payload, ["display", "name", "full_name", "username", "email"])
    user = _match_from_text_values(
        user_model,
        values,
        ["display", "full_name", "get_full_name", "username", "email", "name"],
    )
    if user is not None:
        return user

    username = payload.get("username")
    if username:
        return _first_match(user_model, username=username)
    return None


def _resolve_site(payload: dict[str, Any] | None) -> Any | None:
    if not payload:
        return None
    values = _expand_site_values(_candidate_values(payload, ["display", "name", "slug"]))
    site = _match_from_text_values(Site, values, ["display", "name", "slug"])
    if site is not None:
        return site
    for obj in Site.objects.all():
        for attr_name in ["display", "name", "slug"]:
            obj_value = _object_value(obj, attr_name)
            if obj_value and _normalize_site_text(obj_value) in values:
                return obj
    slug = payload.get("slug")
    if slug:
        site = _first_match(Site, slug=slug)
        if site:
            return site
    name = payload.get("name")
    if name:
        return _first_match(Site, name=name)
    return None


def _resolve_region(payload: dict[str, Any] | None) -> Any | None:
    if not payload:
        return None
    values = _expand_region_values(_candidate_values(payload, ["display", "name", "slug"]))
    region = _match_from_text_values(Region, values, ["display", "name", "slug"])
    if region is not None:
        return region
    for obj in Region.objects.all():
        for attr_name in ["display", "name", "slug"]:
            obj_value = _object_value(obj, attr_name)
            if obj_value and _normalize_region_text(obj_value) in values:
                return obj
    region = _match_from_text_values(Region, values, ["display", "name", "slug"])
    if region is not None:
        return region
    slug = payload.get("slug")
    if slug:
        region = _first_match(Region, slug=slug)
        if region:
            return region
    name = payload.get("name")
    if name:
        return _first_match(Region, name=name)
    return None


def _resolve_service_provider(payload: dict[str, Any] | None) -> Any | None:
    if not payload:
        return None
    values = _candidate_values(payload, ["display", "name"])
    provider = _match_from_text_values(ServiceProvider, values, ["display", "name"])
    if provider is not None:
        return provider
    name = payload.get("name")
    if name:
        return _first_match(ServiceProvider, name=name)
    return None


def _resolve_bare_fiber_service(payload: dict[str, Any] | None) -> Any | None:
    if not payload:
        return None
    values = _candidate_values(payload, ["display", "name", "slug"])
    service = _match_from_text_values(BareFiberService, values, ["display", "name", "slug"])
    if service is not None:
        return service
    slug = payload.get("slug")
    if slug:
        service = _first_match(BareFiberService, slug=slug)
        if service:
            return service
    name = payload.get("name")
    if name:
        return _first_match(BareFiberService, name=name)
    return None


def _resolve_circuit_service(payload: dict[str, Any] | None) -> Any | None:
    if not payload:
        return None
    values = _candidate_values(payload, ["display", "name", "slug"])
    service = _match_from_text_values(CircuitService, values, ["display", "name", "slug", "special_line_name"])
    if service is not None:
        return service
    slug = payload.get("slug")
    if slug:
        service = _first_match(CircuitService, slug=slug)
        if service:
            return service
    name = payload.get("name")
    if name:
        return _first_match(CircuitService, name=name)
    return None


def _resolve_sites(
    payloads: list[dict[str, Any]] | None,
    *,
    script: Script,
    context: str,
) -> list[Any]:
    resolved: list[Any] = []
    for payload in payloads or []:
        site = _resolve_site(payload)
        if site is not None:
            resolved.append(site)
            continue
        label = payload.get("slug") or payload.get("name") or "unknown-site"
        script.log_warning(f"{context}: 本地未找到站点 {label}，已跳过该关联。")
    return resolved


def _resolve_users(
    payloads: list[dict[str, Any]] | None,
    *,
    script: Script,
    context: str,
) -> list[Any]:
    resolved: list[Any] = []
    for payload in payloads or []:
        user = _resolve_user(payload)
        if user is not None:
            resolved.append(user)
            continue
        label = payload.get("username") or "unknown-user"
        script.log_warning(f"{context}: 本地未找到用户 {label}，已跳过该关联。")
    return resolved


def _assign_scalar_fields(instance: Any, payload: dict[str, Any], field_names: list[str]) -> None:
    for field_name in field_names:
        if field_name in payload:
            setattr(instance, field_name, _normalize_scalar(field_name, payload.get(field_name)))


def sync_fault_payload(script: Script, payload: dict[str, Any], *, dry_run: bool) -> SyncResult:
    fault_number = payload.get("fault_number")
    if not fault_number:
        script.log_warning("发现缺少 fault_number 的远端故障记录，已跳过。")
        return SyncResult(status="skipped", reason="missing-fault-number")

    duty_officer = _resolve_user(payload.get("duty_officer"))
    if duty_officer is None:
        username = (payload.get("duty_officer") or {}).get("username") or "unknown-user"
        script.log_warning(f"故障 {fault_number}: 本地未找到值守人员 {username}，已跳过。")
        return SyncResult(status="skipped", reason="missing-duty-officer")

    site_a = _resolve_site(payload.get("interruption_location_a"))
    if site_a is None:
        site_label = (payload.get("interruption_location_a") or {}).get("slug") or (payload.get("interruption_location_a") or {}).get("name") or "unknown-site"
        script.log_warning(f"故障 {fault_number}: 本地未找到 A 端站点 {site_label}，已跳过。")
        return SyncResult(status="skipped", reason="missing-site-a")

    z_sites = _resolve_sites(payload.get("interruption_location"), script=script, context=f"故障 {fault_number}")
    operations_managers = _resolve_users(payload.get("operations_manager"), script=script, context=f"故障 {fault_number}")

    province = _resolve_region(payload.get("province"))
    if payload.get("province") and province is None:
        label = (payload.get("province") or {}).get("slug") or (payload.get("province") or {}).get("name") or "unknown-region"
        script.log_warning(f"故障 {fault_number}: 本地未找到区域 {label}，该字段将留空。")

    line_manager = _resolve_user(payload.get("line_manager"))
    if payload.get("line_manager") and line_manager is None:
        label = (payload.get("line_manager") or {}).get("username") or "unknown-user"
        script.log_warning(f"故障 {fault_number}: 本地未找到线路主管 {label}，该字段将留空。")

    handling_unit = _resolve_service_provider(payload.get("handling_unit"))
    if payload.get("handling_unit") and handling_unit is None:
        label = (payload.get("handling_unit") or {}).get("name") or "unknown-provider"
        script.log_warning(f"故障 {fault_number}: 本地未找到处理单位 {label}，该字段将留空。")

    fault = _first_match(OtnFault, fault_number=fault_number)
    status = "updated" if fault is not None else "created"
    if fault is None:
        fault = OtnFault()

    fault.fault_number = fault_number
    fault.duty_officer = duty_officer
    fault.interruption_location_a = site_a
    fault.province = province
    fault.line_manager = line_manager
    fault.handling_unit = handling_unit

    _assign_scalar_fields(
        fault,
        payload,
        [
            "fault_occurrence_time",
            "fault_recovery_time",
            "fault_category",
            "interruption_reason",
            "interruption_reason_detail",
            "fault_details",
            "interruption_longitude",
            "interruption_latitude",
            "urgency",
            "first_report_source",
            "resource_type",
            "resource_owner",
            "cable_route",
            "maintenance_mode",
            "dispatch_time",
            "departure_time",
            "arrival_time",
            "repair_time",
            "timeout",
            "timeout_reason",
            "handler",
            "recovery_mode",
            "fault_status",
            "closure_time",
            "power_data_type",
            "power_recovery_mode",
            "power_maintenance_mode",
            "manager_reviewed",
            "manager_reviewer",
            "manager_review_time",
            "noc_reviewed",
            "noc_reviewer",
            "noc_review_time",
            "comments",
        ],
    )

    if not dry_run:
        with transaction.atomic():
            fault.save()
            fault.interruption_location.set(z_sites)
            fault.operations_manager.set(operations_managers)

    return SyncResult(status=status, instance=fault)


def sync_impact_payload(
    script: Script,
    fault: Any,
    payload: dict[str, Any],
    *,
    dry_run: bool,
) -> SyncResult:
    service_type = payload.get("service_type")
    if service_type not in {"bare_fiber", "circuit"}:
        script.log_warning(f"故障 {getattr(fault, 'fault_number', 'unknown')}: 发现未知业务类型 {service_type!r}，已跳过影响业务。")
        return SyncResult(status="skipped", reason="unsupported-service-type")

    bare_fiber_service = None
    circuit_service = None
    if service_type == "bare_fiber":
        bare_fiber_service = _resolve_bare_fiber_service(payload.get("bare_fiber_service"))
        if bare_fiber_service is None:
            label = (payload.get("bare_fiber_service") or {}).get("slug") or (payload.get("bare_fiber_service") or {}).get("name") or "unknown-bare-fiber"
            script.log_warning(f"故障 {getattr(fault, 'fault_number', 'unknown')}: 本地未找到裸纤业务 {label}，已跳过该影响业务。")
            return SyncResult(status="skipped", reason="missing-bare-fiber-service")
    else:
        circuit_service = _resolve_circuit_service(payload.get("circuit_service"))
        if circuit_service is None:
            label = (payload.get("circuit_service") or {}).get("slug") or (payload.get("circuit_service") or {}).get("name") or "unknown-circuit"
            script.log_warning(f"故障 {getattr(fault, 'fault_number', 'unknown')}: 本地未找到电路业务 {label}，已跳过该影响业务。")
            return SyncResult(status="skipped", reason="missing-circuit-service")

    impact = None
    fault_is_saved = getattr(fault, "pk", None) is not None
    if fault_is_saved:
        if bare_fiber_service is not None:
            impact = _first_match(OtnFaultImpact, otn_fault=fault, bare_fiber_service=bare_fiber_service)
        if circuit_service is not None:
            impact = _first_match(OtnFaultImpact, otn_fault=fault, circuit_service=circuit_service)

    status = "updated" if impact is not None else "created"
    if impact is None:
        impact = OtnFaultImpact()

    impact.otn_fault = fault
    impact.service_type = service_type
    impact.bare_fiber_service = bare_fiber_service
    impact.circuit_service = circuit_service
    impact.service_site_a = _resolve_site(payload.get("service_site_a"))

    if payload.get("service_site_a") and impact.service_site_a is None:
        label = (payload.get("service_site_a") or {}).get("slug") or (payload.get("service_site_a") or {}).get("name") or "unknown-site"
        script.log_warning(f"故障 {getattr(fault, 'fault_number', 'unknown')}: 本地未找到业务 A 端站点 {label}，该字段将留空。")

    _assign_scalar_fields(
        impact,
        payload,
        [
            "service_interruption_time",
            "service_recovery_time",
            "comments",
        ],
    )

    service_site_z = _resolve_sites(
        payload.get("service_site_z"),
        script=script,
        context=f"故障 {getattr(fault, 'fault_number', 'unknown')} 的影响业务",
    )

    if not dry_run:
        with transaction.atomic():
            impact.save()
            impact.service_site_z.set(service_site_z)

    return SyncResult(status=status, instance=impact)


def _compose_report(summary: dict[str, int], *, dry_run: bool, sync_impacts: bool) -> str:
    lines = [
        "# 远端 NetBox 故障同步结果",
        "",
        f"- 模式: {'模拟执行' if dry_run else '正式写入'}",
        f"- 故障新增: {summary['faults_created']}",
        f"- 故障更新: {summary['faults_updated']}",
        f"- 故障跳过: {summary['faults_skipped']}",
    ]
    if sync_impacts:
        lines.extend(
            [
                f"- 影响业务新增: {summary['impacts_created']}",
                f"- 影响业务更新: {summary['impacts_updated']}",
                f"- 影响业务跳过: {summary['impacts_skipped']}",
            ]
        )
    return "\n".join(lines)


class SyncRemoteFaults(Script):
    class Meta:
        name = "同步远端 NetBox 故障数据"
        description = "从另一台 NetBox 插件 API 拉取故障与影响业务数据，并按故障编号同步到本机。"
        commit_default = True

    base_url = StringVar(
        description="远端 NetBox 根地址",
        default="http://192.168.30.177",
    )
    api_token = StringVar(
        description="远端 NetBox API Token，可留空",
        default="",
        required=False,
    )
    verify_ssl = BooleanVar(
        description="是否校验远端 HTTPS 证书",
        default=False,
    )
    sync_impacts = BooleanVar(
        description="是否同步故障影响业务",
        default=True,
    )
    page_limit = IntegerVar(
        description="远端 API 单页拉取数量",
        default=100,
    )
    dry_run = BooleanVar(
        description="模拟模式：仅预览同步结果，不写入本地数据库",
        default=True,
    )

    def run(self, data: dict[str, Any], commit: bool) -> str:
        dry_run = bool(data.get("dry_run", True) or not commit)
        sync_impacts = bool(data.get("sync_impacts", True))
        verify_ssl = bool(data.get("verify_ssl", False))
        base_url = _normalize_base_url(data.get("base_url") or "http://192.168.30.177")
        session = build_api_session((data.get("api_token") or "").strip())
        page_limit = int(data.get("page_limit") or 100)
        summary = {
            "faults_created": 0,
            "faults_updated": 0,
            "faults_skipped": 0,
            "impacts_created": 0,
            "impacts_updated": 0,
            "impacts_skipped": 0,
        }

        self.log_info(f"开始从 {base_url} 拉取故障数据。")
        if dry_run:
            self.log_warning("当前为模拟模式，不会写入任何本地数据。")

        fault_candidates = build_api_collection_candidates(base_url, "faults")
        try:
            remote_faults, resolved_faults_url = fetch_paginated_api_from_candidates(
                session,
                fault_candidates,
                verify_ssl=verify_ssl,
                params={"limit": page_limit},
            )
        except Exception as exc:
            self.log_failure(f"拉取远端故障列表失败: {exc}")
            return _compose_report(summary, dry_run=dry_run, sync_impacts=sync_impacts)

        if resolved_faults_url != fault_candidates[0]:
            self.log_info(f"远端故障 API 路径已自动切换为 {resolved_faults_url}")
        self.log_info(f"成功获取 {len(remote_faults)} 条远端故障记录。")
        remote_fault_map = {
            payload.get("id"): payload
            for payload in remote_faults
            if payload.get("id") is not None and payload.get("fault_number")
        }
        local_faults_by_number: dict[str, Any] = {}

        for payload in remote_faults:
            result = sync_fault_payload(self, payload, dry_run=dry_run)
            if result.status == "created":
                summary["faults_created"] += 1
            elif result.status == "updated":
                summary["faults_updated"] += 1
            else:
                summary["faults_skipped"] += 1

            if result.instance is not None and payload.get("fault_number"):
                local_faults_by_number[payload["fault_number"]] = result.instance

        if sync_impacts:
            impact_candidates = build_api_collection_candidates(base_url, "impacts")
            try:
                remote_impacts, resolved_impacts_url = fetch_paginated_api_from_candidates(
                    session,
                    impact_candidates,
                    verify_ssl=verify_ssl,
                    params={"limit": page_limit},
                )
            except Exception as exc:
                self.log_failure(f"拉取远端影响业务列表失败: {exc}")
                return _compose_report(summary, dry_run=dry_run, sync_impacts=sync_impacts)

            if resolved_impacts_url != impact_candidates[0]:
                self.log_info(f"远端影响业务 API 路径已自动切换为 {resolved_impacts_url}")
            self.log_info(f"成功获取 {len(remote_impacts)} 条远端影响业务记录。")
            for payload in remote_impacts:
                remote_fault_payload = remote_fault_map.get(payload.get("otn_fault"))
                if not remote_fault_payload:
                    self.log_warning("发现引用未知远端故障 ID 的影响业务，已跳过。")
                    summary["impacts_skipped"] += 1
                    continue

                fault_number = remote_fault_payload.get("fault_number")
                local_fault = local_faults_by_number.get(fault_number) or _first_match(OtnFault, fault_number=fault_number)
                if local_fault is None:
                    self.log_warning(f"影响业务关联的本地故障 {fault_number} 不存在，已跳过。")
                    summary["impacts_skipped"] += 1
                    continue

                result = sync_impact_payload(self, local_fault, payload, dry_run=dry_run)
                if result.status == "created":
                    summary["impacts_created"] += 1
                elif result.status == "updated":
                    summary["impacts_updated"] += 1
                else:
                    summary["impacts_skipped"] += 1

        self.log_success("远端 NetBox 故障同步完成。")
        return _compose_report(summary, dry_run=dry_run, sync_impacts=sync_impacts)
