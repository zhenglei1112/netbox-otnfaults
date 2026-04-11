import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "netbox_otnfaults" / "scripts" / "sync_remote_faults.py"


class _Var:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs


class _FakeQuerySet:
    def __init__(self, items):
        self._items = list(items)

    def first(self):
        return self._items[0] if self._items else None

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


class _FakeManager:
    def __init__(self, items=None):
        self._items = list(items or [])

    def filter(self, **criteria):
        for value in criteria.values():
            if hasattr(value, "pk") and getattr(value, "pk", None) is None:
                raise ValueError("Model instances passed to related filters must be saved.")
        matched = []
        for item in self._items:
            ok = True
            for key, value in criteria.items():
                if getattr(item, key, None) != value:
                    ok = False
                    break
            if ok:
                matched.append(item)
        return _FakeQuerySet(matched)

    def add(self, item) -> None:
        if item not in self._items:
            self._items.append(item)

    def all(self):
        return list(self._items)

    def count(self) -> int:
        return len(self._items)


class _FakeRelation:
    def __init__(self, items=None) -> None:
        self.items = list(items or [])

    def set(self, items) -> None:
        self.items = list(items)

    def all(self):
        return list(self.items)

    def count(self) -> int:
        return len(self.items)

    def first(self):
        return self.items[0] if self.items else None


class _FakeUser:
    objects = _FakeManager()

    def __init__(self, username: str, email: str = "", display: str | None = None, full_name: str | None = None) -> None:
        self.username = username
        self.email = email
        self.display = display or username
        self.full_name = full_name or self.display

    def get_full_name(self) -> str:
        return self.full_name


class _FakeSite:
    objects = _FakeManager()

    def __init__(self, name: str, slug: str, display: str | None = None) -> None:
        self.name = name
        self.slug = slug
        self.display = display or name


class _FakeRegion:
    objects = _FakeManager()

    def __init__(self, name: str, slug: str, display: str | None = None) -> None:
        self.name = name
        self.slug = slug
        self.display = display or name


class _FakeServiceProvider:
    objects = _FakeManager()

    def __init__(self, name: str) -> None:
        self.name = name
        self.display = name


class _FakeBareFiberService:
    objects = _FakeManager()

    def __init__(self, name: str, slug: str) -> None:
        self.name = name
        self.slug = slug
        self.display = name


class _FakeCircuitService:
    objects = _FakeManager()

    def __init__(self, name: str, slug: str) -> None:
        self.name = name
        self.slug = slug
        self.display = name


class _FakeOtnFault:
    objects = _FakeManager()
    save_calls = 0
    next_pk = 1

    def __init__(self, **kwargs) -> None:
        self.interruption_location = _FakeRelation()
        self.operations_manager = _FakeRelation()
        self.pk = kwargs.pop("pk", None)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def save(self) -> None:
        if self.pk is None:
            self.pk = type(self).next_pk
            type(self).next_pk += 1
        type(self).save_calls += 1
        type(self).objects.add(self)


class _FakeOtnFaultImpact:
    objects = _FakeManager()
    save_calls = 0
    next_pk = 1

    def __init__(self, **kwargs) -> None:
        self.service_site_z = _FakeRelation()
        self.pk = kwargs.pop("pk", None)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def save(self) -> None:
        if self.pk is None:
            self.pk = type(self).next_pk
            type(self).next_pk += 1
        type(self).save_calls += 1
        type(self).objects.add(self)


class _DummyScript:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def log_info(self, message: str) -> None:
        self.messages.append(("info", message))

    def log_warning(self, message: str) -> None:
        self.messages.append(("warning", message))

    def log_success(self, message: str) -> None:
        self.messages.append(("success", message))

    def log_failure(self, message: str) -> None:
        self.messages.append(("failure", message))


class _FakeResponse:
    def __init__(self, payload) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _FakeHttpError(Exception):
    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"{status_code} Client Error: Not Found for url: {url}")
        self.response = types.SimpleNamespace(status_code=status_code, url=url)


class _FakeErrorResponse:
    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url

    def raise_for_status(self) -> None:
        raise _FakeHttpError(self.status_code, self.url)

    def json(self):
        raise AssertionError("json() should not be called when raise_for_status() fails")


class _FakeSession:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.trust_env = True
        self.headers = {}
        self.calls: list[dict[str, object]] = []

    def get(self, url, params=None, timeout=None, verify=None):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
                "verify": verify,
            }
        )
        if not self.responses:
            raise AssertionError("Unexpected extra HTTP request")
        return self.responses.pop(0)


def _reset_fake_state() -> None:
    _FakeUser.objects = _FakeManager()
    _FakeSite.objects = _FakeManager()
    _FakeRegion.objects = _FakeManager()
    _FakeServiceProvider.objects = _FakeManager()
    _FakeBareFiberService.objects = _FakeManager()
    _FakeCircuitService.objects = _FakeManager()
    _FakeOtnFault.objects = _FakeManager()
    _FakeOtnFault.save_calls = 0
    _FakeOtnFault.next_pk = 1
    _FakeOtnFaultImpact.objects = _FakeManager()
    _FakeOtnFaultImpact.save_calls = 0
    _FakeOtnFaultImpact.next_pk = 1


def _install_import_stubs() -> None:
    _reset_fake_state()

    extras_module = types.ModuleType("extras")
    extras_scripts_module = types.ModuleType("extras.scripts")

    class _Script:
        pass

    extras_scripts_module.Script = _Script
    extras_scripts_module.StringVar = _Var
    extras_scripts_module.BooleanVar = _Var
    extras_scripts_module.IntegerVar = _Var
    sys.modules["extras"] = extras_module
    sys.modules["extras.scripts"] = extras_scripts_module

    django_module = types.ModuleType("django")
    django_contrib_module = types.ModuleType("django.contrib")
    django_auth_module = types.ModuleType("django.contrib.auth")
    django_auth_module.get_user_model = lambda: _FakeUser
    django_db_module = types.ModuleType("django.db")
    django_db_transaction_module = types.ModuleType("django.db.transaction")

    @contextmanager
    def _atomic():
        yield

    django_db_transaction_module.atomic = _atomic

    sys.modules["django"] = django_module
    sys.modules["django.contrib"] = django_contrib_module
    sys.modules["django.contrib.auth"] = django_auth_module
    sys.modules["django.db"] = django_db_module
    sys.modules["django.db.transaction"] = django_db_transaction_module

    dcim_module = types.ModuleType("dcim")
    dcim_models_module = types.ModuleType("dcim.models")
    dcim_models_module.Site = _FakeSite
    dcim_models_module.Region = _FakeRegion
    sys.modules["dcim"] = dcim_module
    sys.modules["dcim.models"] = dcim_models_module

    contract_module = types.ModuleType("netbox_contract")
    contract_models_module = types.ModuleType("netbox_contract.models")
    contract_models_module.ServiceProvider = _FakeServiceProvider
    sys.modules["netbox_contract"] = contract_module
    sys.modules["netbox_contract.models"] = contract_models_module

    plugin_module = types.ModuleType("netbox_otnfaults")
    plugin_models_module = types.ModuleType("netbox_otnfaults.models")
    plugin_models_module.OtnFault = _FakeOtnFault
    plugin_models_module.OtnFaultImpact = _FakeOtnFaultImpact
    plugin_models_module.BareFiberService = _FakeBareFiberService
    plugin_models_module.CircuitService = _FakeCircuitService
    sys.modules["netbox_otnfaults"] = plugin_module
    sys.modules["netbox_otnfaults.models"] = plugin_models_module

    requests_module = types.ModuleType("requests")
    requests_module.Session = lambda: _FakeSession([])
    sys.modules["requests"] = requests_module


def _load_script_module():
    _install_import_stubs()
    spec = importlib.util.spec_from_file_location("test_sync_remote_faults_module", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SyncRemoteFaultsHttpTestCase(unittest.TestCase):
    def test_fetch_paginated_api_collects_all_pages_and_sets_token_header(self) -> None:
        module = _load_script_module()
        session = _FakeSession(
            [
                _FakeResponse(
                    {
                        "results": [{"id": 1, "fault_number": "F20260411001"}],
                        "next": "http://remote/api/plugins/netbox_otnfaults/faults/?limit=2&offset=2",
                    }
                ),
                _FakeResponse(
                    {
                        "results": [{"id": 2, "fault_number": "F20260411002"}],
                        "next": None,
                    }
                ),
            ]
        )
        module.requests.Session = lambda: session

        built_session = module.build_api_session("demo-token")
        payloads = module.fetch_paginated_api(
            built_session,
            "http://remote/api/plugins/netbox_otnfaults/faults/",
            verify_ssl=False,
            params={"limit": 2},
        )

        self.assertEqual([item["fault_number"] for item in payloads], ["F20260411001", "F20260411002"])
        self.assertIs(built_session, session)
        self.assertIs(session.trust_env, False)
        self.assertEqual(session.headers["Authorization"], "Token demo-token")
        self.assertEqual(session.calls[0]["url"], "http://remote/api/plugins/netbox_otnfaults/faults/")
        self.assertEqual(session.calls[0]["params"], {"limit": 2})
        self.assertEqual(session.calls[1]["url"], "http://remote/api/plugins/netbox_otnfaults/faults/?limit=2&offset=2")
        self.assertIsNone(session.calls[1]["params"])

    def test_fetch_paginated_api_from_candidates_falls_back_to_otnfaults_prefix_after_404(self) -> None:
        module = _load_script_module()
        session = _FakeSession(
            [
                _FakeErrorResponse(404, "http://remote/api/plugins/netbox_otnfaults/faults/?limit=100"),
                _FakeResponse(
                    {
                        "results": [{"id": 1, "fault_number": "F20260411001"}],
                        "next": None,
                    }
                ),
            ]
        )

        payloads, selected_url = module.fetch_paginated_api_from_candidates(
            session,
            [
                "http://remote/api/plugins/netbox_otnfaults/faults/",
                "http://remote/api/plugins/otnfaults/faults/",
            ],
            verify_ssl=False,
            params={"limit": 100},
        )

        self.assertEqual([item["fault_number"] for item in payloads], ["F20260411001"])
        self.assertEqual(selected_url, "http://remote/api/plugins/otnfaults/faults/")
        self.assertEqual(session.calls[0]["url"], "http://remote/api/plugins/netbox_otnfaults/faults/")
        self.assertEqual(session.calls[1]["url"], "http://remote/api/plugins/otnfaults/faults/")


class SyncRemoteFaultsUpsertTestCase(unittest.TestCase):
    def test_resolve_site_matches_display_text_with_room_suffix_variants(self) -> None:
        module = _load_script_module()
        site = _FakeSite("太仓中继机房", "taicang-room", display="太仓中继机房")
        _FakeSite.objects.add(site)

        resolved = module._resolve_site({"slug": "site-42a0a7dd", "display": "太仓中继"})

        self.assertIs(resolved, site)

    def test_resolve_region_matches_normalized_province_variants(self) -> None:
        module = _load_script_module()
        yunnan = _FakeRegion("云南", "yunnan")
        beijing = _FakeRegion("北京", "beijing")
        xinjiang = _FakeRegion("新疆维吾尔自治区", "xinjiang")
        for region in [yunnan, beijing, xinjiang]:
            _FakeRegion.objects.add(region)

        self.assertIs(module._resolve_region({"name": "云南省"}), yunnan)
        self.assertIs(module._resolve_region({"display": "北京市"}), beijing)
        self.assertIs(module._resolve_region({"name": "新疆"}), xinjiang)

    def test_sync_fault_payload_resolves_people_sites_and_region_by_display_text(self) -> None:
        module = _load_script_module()
        duty_officer = _FakeUser("user-zjw", display="张嘉雯")
        operations_manager = _FakeUser("user-hezh", display="何志宏")
        site_a = _FakeSite("郑州", "zhengzhou", display="郑州")
        region = _FakeRegion("河南联通", "henan-unicom", display="河南联通")
        for item, manager in [
            (duty_officer, _FakeUser.objects),
            (operations_manager, _FakeUser.objects),
            (site_a, _FakeSite.objects),
            (region, _FakeRegion.objects),
        ]:
            manager.add(item)

        payload = {
            "id": 102,
            "fault_number": "F20260411002",
            "duty_officer": {"username": "remote-zjw", "display": "张嘉雯"},
            "interruption_location_a": {"slug": "site-42a0a7dd", "display": "郑州"},
            "interruption_location": [],
            "fault_occurrence_time": "2026-04-11T08:30:00+08:00",
            "province": {"slug": "hnltgw", "display": "河南联通"},
            "operations_manager": [{"username": "remote-hezh", "display": "何志宏"}],
            "fault_status": "processing",
        }

        result = module.sync_fault_payload(_DummyScript(), payload, dry_run=False)

        self.assertEqual(result.status, "created")
        self.assertEqual(result.instance.duty_officer.username, "user-zjw")
        self.assertEqual(result.instance.interruption_location_a.slug, "zhengzhou")
        self.assertEqual(result.instance.province.slug, "henan-unicom")
        self.assertEqual(result.instance.operations_manager.first().username, "user-hezh")

    def test_sync_fault_payload_updates_existing_fault_by_fault_number(self) -> None:
        module = _load_script_module()
        duty_officer = _FakeUser("alice")
        line_manager = _FakeUser("line-manager")
        noc_manager = _FakeUser("noc-manager")
        site_a = _FakeSite("Alpha", "alpha")
        site_z = _FakeSite("Beta", "beta")
        region = _FakeRegion("Fujian", "fujian")
        provider = _FakeServiceProvider("Team A")
        for item, manager in [
            (duty_officer, _FakeUser.objects),
            (line_manager, _FakeUser.objects),
            (noc_manager, _FakeUser.objects),
            (site_a, _FakeSite.objects),
            (site_z, _FakeSite.objects),
            (region, _FakeRegion.objects),
            (provider, _FakeServiceProvider.objects),
        ]:
            manager.add(item)

        existing_fault = _FakeOtnFault(
            fault_number="F20260411001",
            fault_details="old details",
        )
        _FakeOtnFault.objects.add(existing_fault)

        payload = {
            "id": 101,
            "fault_number": "F20260411001",
            "duty_officer": {"username": "alice"},
            "interruption_location_a": {"slug": "alpha", "name": "Alpha"},
            "interruption_location": [{"slug": "beta", "name": "Beta"}],
            "fault_occurrence_time": "2026-04-10T08:30:00+08:00",
            "fault_recovery_time": "2026-04-10T09:15:00+08:00",
            "fault_category": "fiber_break",
            "interruption_reason": "construction",
            "fault_details": "updated details",
            "interruption_longitude": "118.123456",
            "interruption_latitude": "25.123456",
            "province": {"slug": "fujian", "name": "Fujian"},
            "line_manager": {"username": "line-manager"},
            "operations_manager": [{"username": "noc-manager"}],
            "maintenance_mode": "self",
            "handling_unit": {"name": "Team A"},
            "dispatch_time": "2026-04-10T08:35:00+08:00",
            "timeout": False,
            "handler": "ops-user",
            "fault_status": "closed",
            "comments": "synced comment",
        }

        result = module.sync_fault_payload(_DummyScript(), payload, dry_run=False)

        self.assertEqual(result.status, "updated")
        self.assertIs(result.instance, existing_fault)
        self.assertEqual(existing_fault.duty_officer.username, "alice")
        self.assertEqual(existing_fault.interruption_location.first().slug, "beta")
        self.assertEqual(existing_fault.operations_manager.first().username, "noc-manager")
        self.assertEqual(existing_fault.fault_details, "updated details")
        self.assertEqual(str(existing_fault.interruption_longitude), "118.123456")
        self.assertEqual(existing_fault.handling_unit.name, "Team A")
        self.assertEqual(_FakeOtnFault.save_calls, 1)
        self.assertEqual(_FakeOtnFault.objects.count(), 1)

    def test_sync_impact_payload_updates_existing_impact_without_creating_duplicate(self) -> None:
        module = _load_script_module()
        fault = _FakeOtnFault(fault_number="F20260411001", pk=1)
        circuit = _FakeCircuitService("Circuit-001", "circuit-001")
        site_z = _FakeSite("Beta", "beta")
        _FakeCircuitService.objects.add(circuit)
        _FakeSite.objects.add(site_z)

        existing_impact = _FakeOtnFaultImpact(
            otn_fault=fault,
            service_type="circuit",
            circuit_service=circuit,
            comments="old impact",
        )
        _FakeOtnFaultImpact.objects.add(existing_impact)

        payload = {
            "id": 501,
            "service_type": "circuit",
            "circuit_service": {"slug": "circuit-001", "name": "Circuit-001"},
            "service_interruption_time": "2026-04-10T08:31:00+08:00",
            "service_recovery_time": "2026-04-10T09:01:00+08:00",
            "service_site_z": [{"slug": "beta", "name": "Beta"}],
            "comments": "updated impact",
        }

        result = module.sync_impact_payload(_DummyScript(), fault, payload, dry_run=False)

        self.assertEqual(result.status, "updated")
        self.assertIs(result.instance, existing_impact)
        self.assertEqual(existing_impact.comments, "updated impact")
        self.assertEqual(existing_impact.service_site_z.first().slug, "beta")
        self.assertEqual(_FakeOtnFaultImpact.objects.count(), 1)
        self.assertEqual(_FakeOtnFaultImpact.save_calls, 1)

    def test_sync_impact_payload_dry_run_does_not_filter_with_unsaved_fault_instance(self) -> None:
        module = _load_script_module()
        fault = _FakeOtnFault(fault_number="F20260411003")
        circuit = _FakeCircuitService("Circuit-002", "circuit-002")
        _FakeCircuitService.objects.add(circuit)

        payload = {
            "id": 701,
            "service_type": "circuit",
            "circuit_service": {"slug": "circuit-002", "name": "Circuit-002"},
            "service_interruption_time": "2026-04-10T10:31:00+08:00",
            "comments": "dry-run impact",
        }

        result = module.sync_impact_payload(_DummyScript(), fault, payload, dry_run=True)

        self.assertEqual(result.status, "created")
        self.assertIs(result.instance.otn_fault, fault)

    def test_sync_impact_payload_skips_when_required_service_is_missing(self) -> None:
        module = _load_script_module()
        script = _DummyScript()
        fault = _FakeOtnFault(fault_number="F20260411001")

        payload = {
            "id": 601,
            "service_type": "circuit",
            "circuit_service": {"slug": "missing-circuit", "name": "Missing Circuit"},
            "service_interruption_time": "2026-04-10T08:31:00+08:00",
            "comments": "impact comment",
        }

        result = module.sync_impact_payload(script, fault, payload, dry_run=False)

        self.assertEqual(result.status, "skipped")
        self.assertEqual(_FakeOtnFaultImpact.objects.count(), 0)
        self.assertTrue(
            any(
                level == "warning" and "missing-circuit" in message
                for level, message in script.messages
            )
        )


if __name__ == "__main__":
    unittest.main()
