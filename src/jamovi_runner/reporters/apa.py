"""APA 7th edition table formatter with note support."""

from typing import Any, Sequence

from jamovi_runner.formatting import markdown_table


# Map common statistical labels to APA italicized symbols
APA_STAT_SYMBOLS = {
    "Mean": "*M*",
    "M": "*M*",
    "SD": "*SD*",
    "N": "*N*",
    "n": "*n*",
    "t": "*t*",
    "p": "*p*",
    "r": "*r*",
    "F": "*F*",
    "b": "*b*",
    "beta": "*β*",
    "β": "*β*",
    "eta": "*η*",
    "etasq": "*η*²",
    "eta2": "*η*²",
    "etaSqP": "*η*²p",
    "η": "*η*",
    "η²": "*η*²",
    "omega": "*ω*",
    "omega2": "*ω*²",
    "R2": "*R*²",
    "R2Adj": "Adjusted *R*²",
    "df": "*df*",
    "df1": "*df*1",
    "df2": "*df*2",
    "se": "*SE*",
    "SE": "*SE*",
    "ci": "95% CI",
    "OR": "OR",
    "Cronbach Alpha": "Cronbach's α",
    "McDonalds Omega": "McDonald's ω",
}


def format_apa_stat_header(label: str) -> str:
    """Replace statistical labels with APA-italicized Markdown equivalents."""
    return APA_STAT_SYMBOLS.get(label, label)


def _format_apa_cell_value(key: str, value: str) -> str:
    """Apply APA-specific formatting to cell values.

    Specifically, reliability coefficients (alpha, omega) and correlation
    coefficients should omit the leading zero when |value| < 1.
    """
    if not isinstance(value, str):
        value = str(value)

    # Coefficients bounded at +/- 1: omit leading zero in APA style
    if key in ("Cronbach Alpha", "McDonalds Omega", "r", "beta", "β", "eta", "η", "η²", "R2", "etaSqP", "eta2", "etasq"):
        try:
            num = float(value)
            if 0 <= num < 1:
                return value.replace("0.", ".", 1)
            if -1 < num < 0:
                return value.replace("-0.", "-.", 1)
        except ValueError:
            pass

    return value


class APATableFormatter:
    """Format tables according to APA 7th edition conventions.

    Features:
    - Automatic Table 1, Table 2... numbering
    - Italicized table titles
    - APA statistical symbol headers
    - Leading-zero omission for bounded coefficients
    - Optional note area appended below the table
    """

    def __init__(
        self,
        title: str,
        rows: Sequence[dict[str, Any]],
        table_index: int = 1,
    ):
        self.title = title
        self.rows = list(rows)
        self.table_index = table_index
        self.notes: list[str] = []

    def add_note(self, note: str) -> "APATableFormatter":
        """Append a note to be rendered below the table."""
        self.notes.append(note)
        return self

    def format(self) -> list[str]:
        """Render the table as a list of Markdown lines."""
        lines: list[str] = [
            f"Table {self.table_index}",
            f"*{self.title}*",
        ]

        # Apply APA header and cell formatting
        formatted_rows = []
        for row in self.rows:
            formatted_row: dict[str, Any] = {}
            for key, value in row.items():
                new_key = format_apa_stat_header(key)
                new_value = _format_apa_cell_value(key, value)
                formatted_row[new_key] = new_value
            formatted_rows.append(formatted_row)

        lines.extend(markdown_table(formatted_rows))
        if self.notes:
            lines.append("")
            lines.append(f"*Note.* {' '.join(self.notes)}")
        return lines
