"""Extractor for linear regression results."""

from typing import Any

from jamovi_runner.formatting import format_number, format_p_value
from jamovi_runner.extract._utils import find_all_named_elements, find_first_named_element, table_rows


def build_linreg_sections(root: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    model_fit = find_first_named_element(root, "modelFit")
    if model_fit is not None and model_fit.HasField("table"):
        fit_rows = []
        for row in table_rows(model_fit.table):
            fit_rows.append(
                {
                    "Model": format_number(row.get("model")),
                    "R": format_number(row.get("r")),
                    "R2": format_number(row.get("r2")),
                    "Adjusted R2": format_number(row.get("r2Adj")),
                    "F": format_number(row.get("f")),
                    "df1": format_number(row.get("df1")),
                    "df2": format_number(row.get("df2")),
                    "p": format_p_value(row.get("p")),
                }
            )
        if fit_rows:
            sections.append({"title": "Model Fit", "rows": fit_rows})

    coefficient_tables = find_all_named_elements(root, "coef")
    coefficient_rows: list[dict[str, Any]] = []
    for table_element in coefficient_tables:
        if not table_element.HasField("table"):
            continue
        for row in table_rows(table_element.table):
            coef_row: dict[str, Any] = {
                "Term": row.get("term") or "",
                "Estimate": format_number(row.get("est")),
                "SE": format_number(row.get("se")),
                "Lower": format_number(row.get("lower")),
                "Upper": format_number(row.get("upper")),
                "t": format_number(row.get("t")),
                "p": format_p_value(row.get("p")),
            }
            if row.get("beta") is not None:
                coef_row["beta"] = format_number(row.get("beta"))
            coefficient_rows.append(coef_row)
    if coefficient_rows:
        sections.append({"title": "Coefficients", "rows": coefficient_rows[:12]})
    return sections
