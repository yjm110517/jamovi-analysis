"""Tests for APA report generation (Phase 2)."""

import pytest

from jamovi_runner.report import build_markdown_report
from jamovi_runner.reporters.apa import format_apa_stat_header


class TestFormatApaStatHeader:
    def test_mean_and_sd_get_italicized(self):
        assert format_apa_stat_header("Mean") == "*M*"
        assert format_apa_stat_header("SD") == "*SD*"

    def test_t_p_r_beta_get_italicized(self):
        assert format_apa_stat_header("t") == "*t*"
        assert format_apa_stat_header("p") == "*p*"
        assert format_apa_stat_header("r") == "*r*"
        assert format_apa_stat_header("beta") == "*β*"

    def test_regular_header_unchanged(self):
        assert format_apa_stat_header("Variable") == "Variable"
        assert format_apa_stat_header("Group") == "Group"


class TestBuildMarkdownReport:
    def test_apa_table_numbering_increments(self):
        sections = [
            {"title": "Descriptive Statistics", "rows": [{"Variable": "x", "Mean": "3.14"}]},
            {"title": "Independent Samples t-Test", "rows": [{"Variable": "x", "t": "2.17"}]},
        ]
        lines, idx = build_markdown_report(sections, table_style="apa")
        assert "Table 1" in lines
        assert "*Descriptive Statistics*" in lines
        assert "Table 2" in lines
        assert "*Independent Samples t-Test*" in lines
        assert idx == 3

    def test_gfm_does_not_number_tables(self):
        sections = [
            {"title": "Key Results", "rows": [{"Variable": "x", "Mean": "3.14"}]},
        ]
        lines, idx = build_markdown_report(sections, table_style="gfm")
        assert "Table 1" not in lines
        assert "*Key Results*" not in lines
        assert idx == 1

    def test_apa_stat_headers_are_italicized(self):
        sections = [
            {
                "title": "Key Results",
                "rows": [{"Variable": "Score", "Mean": "3.82", "SD": "0.71", "t": "2.17", "p": ".021"}],
            }
        ]
        lines, idx = build_markdown_report(sections, table_style="apa")
        header_line = [ln for ln in lines if "| Variable |" in ln][0]
        assert "*M*" in header_line
        assert "*SD*" in header_line
        assert "*t*" in header_line
        assert "*p*" in header_line

    def test_reliability_alpha_omega_omit_leading_zero(self):
        sections = [
            {
                "title": "Scale Reliability",
                "rows": [{"Scale": "Creativity", "Cronbach Alpha": "0.82", "McDonalds Omega": "0.84"}],
            }
        ]
        lines, idx = build_markdown_report(sections, table_style="apa")
        data_line = [ln for ln in lines if "Creativity" in ln][0]
        assert ".82" in data_line
        assert ".84" in data_line
        assert "0.82" not in data_line
        assert "0.84" not in data_line

    def test_empty_sections_are_skipped(self):
        sections = [
            {"title": "Key Results", "rows": []},
            {"title": "Model Fit", "rows": [{"R2": ".18"}]},
        ]
        lines, idx = build_markdown_report(sections, table_style="apa")
        assert "Table 1" in lines
        assert "*Model Fit*" in lines
        assert "*Key Results*" not in lines  # empty section skipped, numbering continues
        assert idx == 2
