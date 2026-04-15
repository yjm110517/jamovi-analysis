"""Extractor for binary logistic regression results."""

from typing import Any

from jamovi_runner.formatting import format_number, format_p_value
from jamovi_runner.extract._utils import find_all_named_elements, find_first_named_element, table_rows


def build_logreg_sections(root: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    model_fit = find_first_named_element(root, "modelFit")
    if model_fit is not None and model_fit.HasField("table"):
        fit_rows = []
        for row in table_rows(model_fit.table):
            fit_rows.append(
                {
                    "Model": format_number(row.get("model")),
                    "Deviance": format_number(row.get("dev")),
                    "AIC": format_number(row.get("aic")),
                    "McFadden R2": format_number(row.get("r2mf")),
                    "Chi Square": format_number(row.get("chi")),
                    "df": format_number(row.get("df")),
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
            coefficient_rows.append(
                {
                    "Term": row.get("term") or "",
                    "Estimate": format_number(row.get("est")),
                    "SE": format_number(row.get("se")),
                    "Lower": format_number(row.get("lower")),
                    "Upper": format_number(row.get("upper")),
                    "z": format_number(row.get("z")),
                    "p": format_p_value(row.get("p")),
                    "OR": format_number(row.get("odds")),
                    "OR Lower": format_number(row.get("oddsLower")),
                    "OR Upper": format_number(row.get("oddsUpper")),
                }
            )
    if coefficient_rows:
        sections.append({"title": "Coefficients", "rows": coefficient_rows[:12]})
    return sections
