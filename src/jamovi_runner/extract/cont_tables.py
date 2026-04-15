"""Extractor for contingency tables results."""

from typing import Any

from jamovi_runner.formatting import format_number, format_p_value
from jamovi_runner.extract._utils import find_first_named_element, table_rows


def build_cont_tables_sections(root: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    chi_sq = find_first_named_element(root, "chiSq")
    if chi_sq is not None and chi_sq.HasField("table"):
        rows = []
        for row in table_rows(chi_sq.table):
            rows.append(
                {
                    "Test": row.get("test[chiSq]") or "Chi Square",
                    "Value": format_number(row.get("value[chiSq]")),
                    "df": format_number(row.get("df[chiSq]")),
                    "p": format_p_value(row.get("p[chiSq]")),
                    "N": format_number(row.get("value[N]")),
                }
            )
        if rows:
            sections.append({"title": "Chi Square Tests", "rows": rows})

    nominal = find_first_named_element(root, "nom")
    if nominal is not None and nominal.HasField("table"):
        rows = []
        for row in table_rows(nominal.table):
            rows.append(
                {
                    "Contingency Coefficient": format_number(row.get("v[cont]")),
                    "Phi": format_number(row.get("v[phi]")),
                    "Cramers V": format_number(row.get("v[cra]")),
                }
            )
        if rows:
            sections.append({"title": "Nominal Measures", "rows": rows})
    return sections
