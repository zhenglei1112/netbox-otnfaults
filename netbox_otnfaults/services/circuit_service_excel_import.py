from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET


XML_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
TARGET_HEADERS = ("业务门类", "业务组", "专线名称", "电路编号")


@dataclass(frozen=True)
class CircuitServiceExcelRow:
    row_number: int
    business_category: str
    service_group: str
    special_line_name: str
    circuit_number: str
    bandwidth: str | None = None
    business_manager: str | None = None


def normalize_business_category_label(value: str) -> str:
    cleaned = (value or "").strip()
    label = re.sub(r"^\d+\s*[.、，,．]?\s*", "", cleaned)
    if label == "航信":
        label = "中航信"
    return label


def read_circuit_service_excel_rows(path: str | Path, sheet_name: str = "最终数据") -> list[CircuitServiceExcelRow]:
    workbook_path = Path(path)
    with ZipFile(workbook_path) as workbook:
        shared_strings = _read_shared_strings(workbook)
        worksheet_path = _find_sheet_path(workbook, sheet_name)
        worksheet = ET.fromstring(workbook.read(worksheet_path))
        rows = worksheet.findall(".//a:sheetData/a:row", XML_NS)

        if not rows:
            return []

        header_map = _row_to_column_values(rows[0], shared_strings)
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
        for col, header in header_map.items():
            if header and "带宽" in header:
                bandwidth_column = col
            if header and header.strip() == "业务主管":
                business_manager_column = col

        records: list[CircuitServiceExcelRow] = []
        for row in rows[2:]:
            values = _row_to_column_values(row, shared_strings)
            business_category = _clean_cell(values.get(required_columns["业务门类"]))
            service_group = _clean_cell(values.get(required_columns["业务组"]))
            special_line_name = _clean_cell(values.get(required_columns["专线名称"]))
            circuit_number = _clean_cell(values.get(required_columns["电路编号"]))
            bandwidth = _clean_cell(values.get(bandwidth_column)) if bandwidth_column else None
            business_manager = _clean_cell(values.get(business_manager_column)) if business_manager_column else None
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
