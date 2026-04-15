"""Low-level utilities for walking jamovi result trees and extracting values."""

import re
from typing import Any, Iterable, Sequence

PLACEHOLDER_LABEL_RE = re.compile(r"^(var\d*|overall|total)$", re.IGNORECASE)


def cell_value(cell: Any) -> Any:
    fields = cell.ListFields()
    if not fields:
        return None
    descriptor, value = fields[0]
    if descriptor.name == "o":
        return None
    return value


def clean_value(value: Any) -> Any:
    if value in ("", ".", "—"):
        return None
    return value


def is_placeholder_label(value: Any) -> bool:
    text = str(clean_value(value) or "").strip()
    if not text:
        return True
    return bool(PLACEHOLDER_LABEL_RE.fullmatch(text))


def normalize_label_text(value: Any) -> str:
    text = str(clean_value(value) or "").strip()
    if not text or text in {"-", "—"}:
        return ""
    return text


def first_present_value(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = clean_value(mapping.get(key))
        if value is not None:
            return value
    return None


def first_present_label(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = normalize_label_text(mapping.get(key))
        if text:
            return text
    return ""


def has_any_value(mapping: dict[str, Any], keys: Sequence[str]) -> bool:
    return any(clean_value(mapping.get(key)) is not None for key in keys)


def format_pair_label(row_dict: dict[str, Any]) -> str:
    left = first_present_label(row_dict, "var1", "lhs", "left")
    right = first_present_label(row_dict, "var2", "rhs", "right")
    if left and right:
        return f"{left} - {right}"
    fallback = first_present_label(row_dict, "pair", "comparison", "vars", "var", "name", ".name")
    if fallback:
        return fallback
    return left or right


def table_rows(table: Any) -> list[dict[str, Any]]:
    columns = list(table.columns)
    row_count = max((len(column.cells) for column in columns), default=0)
    rows: list[dict[str, Any]] = []
    for row_index in range(row_count):
        row: dict[str, Any] = {}
        for column in columns:
            row[column.name] = clean_value(cell_value(column.cells[row_index])) if row_index < len(column.cells) else None
        rows.append(row)
    return rows


def walk_result_elements(node: Any) -> Iterable[Any]:
    yield node
    if node.HasField("group"):
        for child in node.group.elements:
            yield from walk_result_elements(child)
    if node.HasField("array"):
        for child in node.array.elements:
            yield from walk_result_elements(child)


def find_first_named_element(root: Any, name: str) -> Any | None:
    for node in walk_result_elements(root):
        if getattr(node, "name", "") == name:
            return node
    return None


def find_all_named_elements(root: Any, name: str) -> list[Any]:
    return [node for node in walk_result_elements(root) if getattr(node, "name", "") == name]
