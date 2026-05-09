from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET


XML_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
TARGET_HEADERS: tuple[str, ...] = ("业务门类", "业务组", "专线名称", "电路编号")
EXTRA_FIELD_HEADER_MAP: dict[str, str] = {
    "需求单号": "request_number",
    "需求单扫描件 （上传）": "request_attachment",
    "需求单扫描件（上传）": "request_attachment",
    "配置完成日期": "configuration_completed_date",
    "配置人": "configuration_person",
    "服务测试开始日期": "service_test_start_date",
    "服务开通时间": "service_open_time",
    "历年开通单附件 （上传）": "opening_order_attachment",
    "历年开通单附件（上传）": "opening_order_attachment",
    "服务测试结束时间": "service_test_end_time",
    "服务结束时间": "service_end_time",
    "资源回收时间 （专线关闭）": "resource_recycle_time",
    "资源回收时间（专线关闭）": "resource_recycle_time",
    "资源回收实施人": "resource_recycle_person",
    "变更单号": "change_number",
    "变更日期": "change_date",
    "变更实施人": "change_person",
    "历次变更单 （上传）": "change_order_attachment",
    "历次变更单（上传）": "change_order_attachment",
    "互联信息": "interconnection_info",
    "承载系统 (多选）": "carrier_system",
    "承载系统（多选）": "carrier_system",
    "签约主体": "contracting_party",
    "客户对象": "customer_object",
    "客户A端": "customer_a_end",
    "干线A端-站点": "trunk_a_site",
    "干线A端-站点属性": "trunk_a_site_attribute",
    "干线A端-A网元": "trunk_a_ne",
    "干线A端-A单板": "trunk_a_board",
    "干线A端-A端口": "trunk_a_port",
    "客户Z端": "customer_z_end",
    "干线Z端-站点": "trunk_z_site",
    "干线Z端-站点属性": "trunk_z_site_attribute",
    "干线Z端-Z网元": "trunk_z_ne",
    "干线Z端-Z单板": "trunk_z_board",
    "干线Z端-Z端口": "trunk_z_port",
    "收费属性": "charge_attribute",
    "销售人员": "sales_person",
    "合同开通时间": "contract_open_time",
    "合同结束时间": "contract_end_time",
    "合同编号": "contract_number",
    "合同名称": "contract_name",
    "立项项目编号": "project_approval_number",
    "项目名称": "project_name",
    "执行是否异常": "execution_exception",
    "执行异常原因": "execution_exception_reason",
}


@dataclass(frozen=True)
class CircuitServiceExcelRow:
    row_number: int
    business_category: str
    service_group: str
    special_line_name: str
    circuit_number: str
    bandwidth: str | None = None
    business_manager: str | None = None
    sla_level: str | None = None
    operation_status: str | None = None
    ring_protection: str | None = None
    is_external_business: str | None = None
    extra_fields: dict[str, str] | None = None


def normalize_business_category_label(value: str) -> str:
    cleaned = (value or "").strip()
    label = re.sub(r"^\d+\s*[.、，,．]?\s*", "", cleaned)
    if label == "航信":
        label = "中航信"
    return label


def read_circuit_service_excel_rows(path: str | Path | BinaryIO, sheet_name: str = "最终数据") -> list[CircuitServiceExcelRow]:
    workbook_source = Path(path) if isinstance(path, str) else path
    with ZipFile(workbook_source) as workbook:
        shared_strings = _read_shared_strings(workbook)
        worksheet_path = _find_sheet_path(workbook, sheet_name)
        worksheet = ET.fromstring(workbook.read(worksheet_path))
        rows = worksheet.findall(".//a:sheetData/a:row", XML_NS)

        if not rows:
            return []

        header_map = _row_to_column_values(rows[0], shared_strings)
        combined_header_map = _build_combined_header_map(rows, shared_strings)
        required_columns = {
            header: column
            for column, header in header_map.items()
            if header in TARGET_HEADERS
        }
        missing_headers = [header for header in TARGET_HEADERS if header not in required_columns]
        if missing_headers:
            raise ValueError(f"Excel 缺少必要列: {', '.join(missing_headers)}")

        bandwidth_column = None
        business_manager_column = None
        sla_level_column = None
        operation_status_column = None
        ring_protection_column = None
        for col, header in header_map.items():
            if header and "带宽" in header:
                bandwidth_column = col
            if header and header.strip() == "业务主管":
                business_manager_column = col
            if header and "SLA" in header.upper():
                sla_level_column = col
            if header and "运行状态" in header:
                operation_status_column = col
            if header and "环网保护" in header:
                ring_protection_column = col
            if header and "对部服务" in header:
                is_external_business_column = col
        
        is_external_business_column = is_external_business_column if 'is_external_business_column' in locals() else None
        extra_field_columns = {
            column: field_key
            for column, header in combined_header_map.items()
            if header in EXTRA_FIELD_HEADER_MAP
            for field_key in (EXTRA_FIELD_HEADER_MAP[header],)
        }

        records: list[CircuitServiceExcelRow] = []
        for row in rows[2:]:
            values = _row_to_column_values(row, shared_strings)
            business_category = _clean_cell(values.get(required_columns["业务门类"]))
            service_group = _clean_cell(values.get(required_columns["业务组"]))
            special_line_name = _clean_cell(values.get(required_columns["专线名称"]))
            circuit_number = _clean_cell(values.get(required_columns["电路编号"]))
            bandwidth = _clean_cell(values.get(bandwidth_column)) if bandwidth_column else None
            business_manager = _clean_cell(values.get(business_manager_column)) if business_manager_column else None
            sla_level = _clean_cell(values.get(sla_level_column)) if sla_level_column else None
            operation_status = _clean_cell(values.get(operation_status_column)) if operation_status_column else None
            ring_protection = _clean_cell(values.get(ring_protection_column)) if ring_protection_column else None
            is_external_business = _clean_cell(values.get(is_external_business_column)) if is_external_business_column else None
            extra_fields = {
                field_key: value
                for column, field_key in extra_field_columns.items()
                if (value := _clean_cell(values.get(column)))
            }
            if not any((business_category, service_group, special_line_name, circuit_number)):
                continue
            records.append(
                CircuitServiceExcelRow(
                    row_number=int(row.attrib["r"]),
                    business_category=business_category,
                    service_group=service_group,
                    special_line_name=special_line_name,
                    circuit_number=circuit_number,
                    bandwidth=bandwidth,
                    business_manager=business_manager,
                    sla_level=sla_level,
                    operation_status=operation_status,
                    ring_protection=ring_protection,
                    is_external_business=is_external_business,
                    extra_fields=extra_fields,
                )
            )

        return records


def _read_shared_strings(workbook: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    shared_strings_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in shared_strings_root.findall("a:si", XML_NS):
        parts = [text_node.text or "" for text_node in item.findall(".//a:t", XML_NS)]
        values.append("".join(parts))
    return values


def _find_sheet_path(workbook: ZipFile, sheet_name: str) -> str:
    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root
    }
    sheets_node = workbook_root.find("a:sheets", XML_NS)

    for sheet in sheets_node if sheets_node is not None else []:
        if sheet.attrib["name"] != sheet_name:
            continue
        rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        return f"xl/{rel_map[rel_id]}"

    raise ValueError(f"未找到工作表: {sheet_name}")


def _row_to_column_values(row: ET.Element, shared_strings: list[str]) -> dict[str, str | None]:
    values: dict[str, str | None] = {}
    for cell in row.findall("a:c", XML_NS):
        ref = cell.attrib.get("r", "")
        column = re.match(r"[A-Z]+", ref)
        if column is None:
            continue
        values[column.group(0)] = _cell_value(cell, shared_strings)
    return values


def _build_combined_header_map(rows: list[ET.Element], shared_strings: list[str]) -> dict[str, str]:
    first_row = _row_to_column_values(rows[0], shared_strings)
    second_row = _row_to_column_values(rows[1], shared_strings) if len(rows) > 1 else {}
    columns = sorted(set(first_row) | set(second_row), key=_column_index)

    combined: dict[str, str] = {}
    current_parent = ""
    for column in columns:
        parent = _clean_cell(first_row.get(column))
        child = _clean_cell(second_row.get(column))
        if parent:
            current_parent = parent
        if child and current_parent:
            combined[column] = f"{current_parent}-{child}"
        else:
            combined[column] = parent or child
    return combined


def _column_index(column: str) -> int:
    index = 0
    for char in column:
        index = index * 26 + ord(char) - ord("A") + 1
    return index


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str | None:
    value_node = cell.find("a:v", XML_NS)
    inline_node = cell.find("a:is", XML_NS)

    if inline_node is not None:
        return "".join(text_node.text or "" for text_node in inline_node.findall(".//a:t", XML_NS))
    if value_node is None:
        return None

    raw_value = value_node.text or ""
    if cell.attrib.get("t") == "s":
        return shared_strings[int(raw_value)]
    return raw_value


def _clean_cell(value: str | None) -> str:
    return (value or "").strip()
