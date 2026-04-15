"""Extractor for reliability analysis results."""

from typing import Any

from jamovi_runner.formatting import format_number
from jamovi_runner.extract._utils import find_first_named_element, table_rows


def build_reliability_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "scale")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    for row in table_rows(element.table):
        rows.append(
            {
                "Scale": row.get("name") or "",
                "Mean": format_number(row.get("mean")),
                "SD": format_number(row.get("sd")),
                "Cronbach Alpha": format_number(row.get("alpha")),
                "McDonalds Omega": format_number(row.get("omega")),
            }
        )
    return [{"title": "Scale Reliability", "rows": rows}]
