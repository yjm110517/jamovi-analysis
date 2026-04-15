"""Extractor for correlation matrix results."""

import re
from typing import Any

from jamovi_runner.formatting import format_number, format_p_value
from jamovi_runner.extract._utils import find_first_named_element, table_rows


def build_corr_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "matrix")
    if element is None or not element.HasField("table"):
        return []

    rows = table_rows(element.table)
    pair_rows: list[dict[str, Any]] = []
    for row in rows:
        target = row.get(".name[r]")
        if not target:
            continue
        for key, value in row.items():
            match = re.match(r"(.+)\[r\]$", key)
            if not match:
                continue
            other = match.group(1)
            if other.startswith(".") or value is None:
                continue
            pair_rows.append(
                {
                    "Variable 1": other,
                    "Variable 2": target,
                    "r": format_number(value),
                    "df": format_number(row.get(f"{other}[rdf]")),
                    "p": format_p_value(row.get(f"{other}[rp]")),
                    "N": format_number(row.get(f"{other}[n]")),
                }
            )
    return [{"title": "Key Results", "rows": pair_rows[:12]}] if pair_rows else []
