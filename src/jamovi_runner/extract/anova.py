"""Extractor for one-way ANOVA results."""

from typing import Any

from jamovi_runner.formatting import format_number, format_p_value
from jamovi_runner.extract._utils import find_first_named_element, table_rows


def build_anova_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "anova")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    for row in table_rows(element.table):
        for suffix, label in (("welch", "Welch"), ("fisher", "Fisher")):
            if row.get(f"p[{suffix}]") is None and row.get(f"F[{suffix}]") is None:
                continue
            f_val = row.get(f"F[{suffix}]")
            df1 = row.get(f"df1[{suffix}]")
            df2 = row.get(f"df2[{suffix}]")
            eta_sq_p = None
            if f_val is not None and df1 is not None and df2 is not None:
                try:
                    f_num = float(f_val)
                    df1_num = float(df1)
                    df2_num = float(df2)
                    denom = f_num * df1_num + df2_num
                    if denom != 0:
                        eta_sq_p = f_num * df1_num / denom
                except (ValueError, TypeError):
                    pass
            result_row: dict[str, Any] = {
                "Dependent Variable": row.get("dep") or "",
                "Test": label,
                "F": format_number(f_val),
                "df1": format_number(df1),
                "df2": format_number(df2),
                "p": format_p_value(row.get(f"p[{suffix}]")),
            }
            if eta_sq_p is not None:
                result_row["etaSqP"] = format_number(eta_sq_p)
            rows.append(result_row)
    sections = [{"title": "Key Results", "rows": rows}] if rows else []

    descriptives = find_first_named_element(root, "desc")
    if descriptives is not None and descriptives.HasField("table"):
        desc_rows = []
        for row in table_rows(descriptives.table):
            desc_rows.append(
                {
                    "Dependent Variable": row.get("dep") or "",
                    "Group": row.get("group") or "",
                    "N": format_number(row.get("num")),
                    "Mean": format_number(row.get("mean")),
                    "SD": format_number(row.get("sd")),
                    "SE": format_number(row.get("se")),
                }
            )
        if desc_rows:
            sections.append({"title": "Group Descriptives", "rows": desc_rows})
    return sections
