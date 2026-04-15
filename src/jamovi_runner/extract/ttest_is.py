"""Extractor for independent-samples t-test results."""

from typing import Any

from jamovi_runner.formatting import format_number, format_p_value
from jamovi_runner.extract._utils import find_first_named_element, table_rows


def build_ttest_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "ttest")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    for row_dict in table_rows(element.table):
        for suffix in ("stud", "welc", "mann"):
            if row_dict.get(f"stat[{suffix}]") is None and row_dict.get(f"p[{suffix}]") is None:
                continue

            row = {
                "Variable": row_dict.get("var") or "",
                "Test": row_dict.get(f"name[{suffix}]") or suffix,
                "Statistic": format_number(row_dict.get(f"stat[{suffix}]")),
                "df": format_number(row_dict.get(f"df[{suffix}]")),
                "p": format_p_value(row_dict.get(f"p[{suffix}]")),
            }
            if row_dict.get(f"es[{suffix}]") is not None:
                label = row_dict.get(f"esType[{suffix}]") or "Effect Size"
                row[str(label)] = format_number(row_dict.get(f"es[{suffix}]"))
            rows.append(row)

    sections = [{"title": "Key Results", "rows": rows}] if rows else []
    descriptives = find_first_named_element(root, "desc")
    if descriptives is not None and descriptives.HasField("table"):
        desc_rows = []
        for row in table_rows(descriptives.table):
            desc_rows.append(
                {
                    "Variable": row.get("dep") or "",
                    "Group 1": row.get("group[1]") or "",
                    "N 1": format_number(row.get("num[1]")),
                    "Mean 1": format_number(row.get("mean[1]")),
                    "SD 1": format_number(row.get("sd[1]")),
                    "Group 2": row.get("group[2]") or "",
                    "N 2": format_number(row.get("num[2]")),
                    "Mean 2": format_number(row.get("mean[2]")),
                    "SD 2": format_number(row.get("sd[2]")),
                }
            )
        if desc_rows:
            sections.append({"title": "Group Descriptives", "rows": desc_rows})
    return sections
