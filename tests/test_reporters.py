"""Tests for jamovi_runner.reporters APA table formatting."""

import pytest

from jamovi_runner.reporters import APATableFormatter


class TestAPATableFormatter:
    def test_basic_apa_table_formatting(self):
        rows = [{"Variable": "Creativity", "M": "3.82", "SD": "0.71"}]
        formatter = APATableFormatter("Descriptive Statistics", rows, table_index=1)
        lines = formatter.format()
        assert lines[0] == "Table 1"
        assert lines[1] == "*Descriptive Statistics*"
        assert "| Variable | *M* | *SD* |" in lines

    def test_table_index_increments(self):
        formatter1 = APATableFormatter("Title 1", [{"A": "1"}], table_index=1)
        formatter2 = APATableFormatter("Title 2", [{"B": "2"}], table_index=2)
        lines1 = formatter1.format()
        lines2 = formatter2.format()
        assert lines1[0] == "Table 1"
        assert lines2[0] == "Table 2"

    def test_note_appended_to_table(self):
        rows = [{"Variable": "Creativity", "M": "3.82"}]
        formatter = (
            APATableFormatter("Descriptive Statistics", rows, table_index=1)
            .add_note("Values are mean scores.")
        )
        lines = formatter.format()
        assert "*Note.* Values are mean scores." in lines

    def test_multiple_notes_joined(self):
        rows = [{"Variable": "Creativity", "M": "3.82"}]
        formatter = (
            APATableFormatter("Descriptive Statistics", rows, table_index=1)
            .add_note("Values are mean scores.")
            .add_note("SD = standard deviation.")
        )
        lines = formatter.format()
        assert "*Note.* Values are mean scores. SD = standard deviation." in lines

    def test_empty_rows_returns_message(self):
        formatter = APATableFormatter("Empty Table", [], table_index=1)
        lines = formatter.format()
        assert lines == ["Table 1", "*Empty Table*", "No extractable rows were available."]

    def test_chaining_add_note_returns_formatter(self):
        formatter = APATableFormatter("Test", [{"A": "1"}], table_index=1)
        result = formatter.add_note("A note")
        assert result is formatter
