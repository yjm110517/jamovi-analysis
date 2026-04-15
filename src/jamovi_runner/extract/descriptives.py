"""Extractor for descriptives analysis results."""

from typing import Any

from jamovi_runner.formatting import format_number
from jamovi_runner.extract._utils import (
    clean_value,
    cell_value,
    find_first_named_element,
    first_present_label,
    has_any_value,
    is_placeholder_label,
    table_rows,
)


def build_descriptives_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "descriptives")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    stat_keys = ("n", "missing", "mean", "median", "sd", "min", "max")
    for row_dict in table_rows(element.table):
        var_name = first_present_label(row_dict, "var", "name", ".name", "vars", ".name[r]")
        if not var_name or is_placeholder_label(var_name):
            continue
        if not has_any_value(row_dict, stat_keys):
            continue

        r = {"Variable": var_name}
        stat_names = {"n", "missing", "mean", "median", "sd", "se", "min", "max", "var", "name", ".name"}
        # Include any split variables
        for k, v in row_dict.items():
            if k not in stat_names and not k.startswith(".") and not k.endswith("[stat]"):
                cleaned = clean_value(v)
                if cleaned is not None:
                    r[k] = cleaned

        r["N"] = format_number(row_dict.get("n"))
        r["Missing"] = format_number(row_dict.get("missing"))
        r["Mean"] = format_number(row_dict.get("mean"))
        r["Median"] = format_number(row_dict.get("median"))
        r["SD"] = format_number(row_dict.get("sd"))
        r["Min"] = format_number(row_dict.get("min"))
        r["Max"] = format_number(row_dict.get("max"))
        rows.append(r)

    if not rows:
        import re

        metrics: dict[str, dict[str, Any]] = {}
        for column in element.table.columns:
            match = re.match(r"(.+)\[([^\]]+)\]$", column.name)
            if not match:
                continue
            variable_name, stat_name = match.groups()
            if variable_name == "stat":
                continue
            metrics.setdefault(variable_name, {})[stat_name] = clean_value(cell_value(column.cells[0])) if column.cells else None

        for variable_name, stats in metrics.items():
            rows.append(
                {
                    "Variable": variable_name,
                    "N": format_number(stats.get("n")),
                    "Missing": format_number(stats.get("missing")),
                    "Mean": format_number(stats.get("mean")),
                    "Median": format_number(stats.get("median")),
                    "SD": format_number(stats.get("sd")),
                    "Min": format_number(stats.get("min")),
                    "Max": format_number(stats.get("max")),
                }
            )
    return [{"title": "Key Results", "rows": rows}] if rows else []
