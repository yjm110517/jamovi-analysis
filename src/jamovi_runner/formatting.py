"""APA 7th edition formatting utilities for jamovi-analysis reports."""

from typing import Any, Sequence


def format_number(value: Any, *, digits: int = 2, leading_zero: bool = True) -> str:
    """Format a numeric value for APA-style reporting.

    Args:
        value: The number to format.
        digits: Number of decimal places (default 2 for APA).
        leading_zero: If False, omit leading zero for values bounded at +/- 1
            (e.g., correlations, p-values). Negative values keep the minus sign.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        formatted = f"{value:.{digits}f}"
        if not leading_zero and abs(value) < 1:
            # Remove leading zero for correlations / p-values in APA style
            if value < 0:
                formatted = formatted.replace("-0.", "-.")
            else:
                formatted = formatted.replace("0.", ".")
        return formatted
    return str(value)


def format_p_value(value: Any) -> str:
    """Format a p-value according to APA 7th edition conventions.

    - p < .001 for values below 0.001
    - No leading zero otherwise (e.g., .021, .26)
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if value < 0.001:
        return "<.001"
    return format_number(value, digits=3, leading_zero=False)


def markdown_table(rows: Sequence[dict[str, Any]]) -> list[str]:
    """Render a list of row dictionaries as a GitHub-flavored Markdown table."""
    if not rows:
        return ["No extractable rows were available."]

    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [str(row.get(column, "") or "") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_markdown_table_block(
    rows: Sequence[dict[str, Any]],
    title: str,
    table_style: str,
    table_index: int,
) -> tuple[list[str], int]:
    """Render a table block with optional APA-style numbering and italic title."""
    if not rows:
        return ["No extractable rows were available."], table_index

    lines: list[str] = []
    if table_style == "apa":
        lines.append(f"Table {table_index}")
        lines.append(f"*{title}*")
        table_index += 1
    lines.extend(markdown_table(rows))
    return lines, table_index
