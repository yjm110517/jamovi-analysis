"""Tests for APA 7th edition formatting utilities (Phase 2)."""

import pytest

from jamovi_runner.formatting import (
    format_number,
    format_p_value,
    markdown_table,
    render_markdown_table_block,
)


class TestFormatNumber:
    """APA requires 2 decimal places for most statistics."""

    def test_default_is_two_decimals(self):
        assert format_number(3.14159) == "3.14"

    def test_integer_no_decimal(self):
        assert format_number(42) == "42"

    def test_correlation_no_leading_zero(self):
        """Correlations and p-values omit the leading zero in APA style."""
        assert format_number(0.45, leading_zero=False) == ".45"
        assert format_number(-0.32, leading_zero=False) == "-.32"
        assert format_number(0.05, leading_zero=False) == ".05"

    def test_non_correlation_keeps_leading_zero(self):
        """Means, SDs, t, F, b, beta keep leading zero."""
        assert format_number(0.45) == "0.45"
        assert format_number(-0.32) == "-0.32"

    def test_none_returns_empty(self):
        assert format_number(None) == ""

    def test_bool_returns_uppercase(self):
        assert format_number(True) == "TRUE"
        assert format_number(False) == "FALSE"


class TestFormatPValue:
    """APA p-value formatting: <.001 for tiny, no leading zero otherwise."""

    def test_less_than_point_zero_zero_one(self):
        assert format_p_value(0.0005) == "<.001"
        assert format_p_value(0.0001) == "<.001"

    def test_regular_p_values_no_leading_zero(self):
        assert format_p_value(0.021) == ".021"
        assert format_p_value(0.256) == ".256"
        assert format_p_value(0.05) == ".050"

    def test_none_returns_empty(self):
        assert format_p_value(None) == ""

    def test_string_passthrough(self):
        assert format_p_value(".04") == ".04"


class TestMarkdownTable:
    def test_basic_table(self):
        rows = [{"Variable": "Creativity", "M": "3.82", "SD": "0.71"}]
        lines = markdown_table(rows)
        assert lines[0] == "| Variable | M | SD |"
        assert lines[1] == "| --- | --- | --- |"
        assert lines[2] == "| Creativity | 3.82 | 0.71 |"

    def test_empty_rows_message(self):
        lines = markdown_table([])
        assert lines == ["No extractable rows were available."]


class TestRenderMarkdownTableBlock:
    def test_apa_table_numbering_and_title_italic(self):
        rows = [{"Variable": "Creativity", "M": "3.82"}]
        lines, idx = render_markdown_table_block(
            rows, "Descriptive Statistics", "apa", 1
        )
        assert lines[0] == "Table 1"
        assert lines[1] == "*Descriptive Statistics*"
        assert idx == 2

    def test_gfm_no_numbering(self):
        rows = [{"Variable": "Creativity", "M": "3.82"}]
        lines, idx = render_markdown_table_block(
            rows, "Descriptive Statistics", "gfm", 1
        )
        assert lines[0] == "| Variable | M |"
        assert idx == 1  # index unchanged for gfm

    def test_apa_multiple_tables_increment_index(self):
        lines1, idx1 = render_markdown_table_block(
            [{"A": "1"}], "Title 1", "apa", 1
        )
        lines2, idx2 = render_markdown_table_block(
            [{"B": "2"}], "Title 2", "apa", idx1
        )
        assert lines1[0] == "Table 1"
        assert lines2[0] == "Table 2"
        assert idx2 == 3
