"""Extractor for paired-samples t-test results."""

from typing import Any

from jamovi_runner.formatting import format_number, format_p_value
from jamovi_runner.extract._utils import (
    find_first_named_element,
    first_present_label,
    first_present_value,
    format_pair_label,
    table_rows,
)


def build_ttestps_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "ttest")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    for row_dict in table_rows(element.table):
        for suffix in ("stud", "wilc"):
            if row_dict.get(f"stat[{suffix}]") is None and row_dict.get(f"p[{suffix}]") is None:
                continue

            row = {
                "Pair": format_pair_label(row_dict),
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
            label = first_present_label(row, "var", "name", ".name", "var1", "var2")
            mean_value = first_present_value(row, "mean", "mean[1]", "m")
            sd_value = first_present_value(row, "sd", "sd[1]")
            n_value = first_present_value(row, "num", "n", "num[1]")
            if not label and mean_value is None and sd_value is None and n_value is None:
                continue
            desc_rows.append(
                {
                    "Variable": label,
                    "N": format_number(n_value),
                    "Mean": format_number(mean_value),
                    "SD": format_number(sd_value),
                }
            )
        if desc_rows:
            sections.append({"title": "Group Descriptives", "rows": desc_rows})
    return sections
