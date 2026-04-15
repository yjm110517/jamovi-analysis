"""Report generation for jamovi-analysis, supporting GFM and APA 7th edition styles."""

from typing import Any, Sequence

from jamovi_runner.formatting import markdown_table, render_markdown_table_block
from jamovi_runner.reporters.apa import APATableFormatter


def build_markdown_report(
    sections: Sequence[dict[str, Any]],
    table_style: str,
    start_table_index: int = 1,
) -> tuple[list[str], int]:
    """Build a Markdown report from extracted sections.

    Args:
        sections: List of {"title": str, "rows": list[dict]} dictionaries.
        table_style: "gfm" or "apa".
        start_table_index: Starting number for APA table numbering.

    Returns:
        Tuple of (lines of Markdown text, next table index).
    """
    lines: list[str] = []
    table_index = start_table_index

    for section in sections:
        rows = section.get("rows", [])
        if not rows:
            continue

        title = section.get("title", "Results")

        if table_style == "apa":
            formatter = APATableFormatter(title, rows, table_index)
            block_lines = formatter.format()
            table_index += 1
        else:
            block_lines, table_index = render_markdown_table_block(
                rows, title, table_style, table_index
            )

        if lines:
            lines.append("")
        lines.extend(block_lines)

    return lines, table_index
