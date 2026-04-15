"""Tests for jamovi result extractors (Phase 3/4)."""

from typing import Any

import pytest

from jamovi_runner.extract import build_summary_sections
from jamovi_runner.extract._utils import (
    clean_value,
    find_all_named_elements,
    find_first_named_element,
    format_pair_label,
    table_rows,
    walk_result_elements,
)


class MockCell:
    def __init__(self, value: Any):
        self._value = value

    def ListFields(self):
        if self._value is None:
            return []
        return [(type("D", (), {"name": "s"})(), self._value)]


class MockColumn:
    def __init__(self, name: str, cells: list[Any]):
        self.name = name
        self.cells = [MockCell(c) for c in cells]


class MockTable:
    def __init__(self, columns: list[MockColumn]):
        self.columns = columns


class MockElement:
    def __init__(self, name: str, table: MockTable | None = None, children: list["MockElement"] | None = None):
        self.name = name
        self._table = table
        self.group = type("G", (), {"elements": children or []})()
        self.array = type("A", (), {"elements": []})()

    def HasField(self, field: str) -> bool:
        if field == "table":
            return self._table is not None
        if field == "group":
            return bool(self.group.elements)
        if field == "array":
            return bool(self.array.elements)
        return False

    @property
    def table(self) -> MockTable:
        if self._table is None:
            raise AttributeError("No table")
        return self._table


class MockRoot:
    def __init__(self, children: list[MockElement]):
        self.name = ""
        self.group = type("G", (), {"elements": children})()
        self.array = type("A", (), {"elements": []})()
        self._table = None

    def HasField(self, field: str) -> bool:
        if field == "group":
            return True
        if field == "array":
            return False
        if field == "table":
            return False
        return False


# ---------------------------------------------------------------------------
# _utils tests
# ---------------------------------------------------------------------------

class TestCleanValue:
    def test_empty_string_returns_none(self):
        assert clean_value("") is None

    def test_dot_returns_none(self):
        assert clean_value(".") is None

    def test_emdash_returns_none(self):
        assert clean_value("—") is None

    def test_number_returns_number(self):
        assert clean_value(3.14) == 3.14


class TestTableRows:
    def test_basic_rows(self):
        table = MockTable([
            MockColumn("var", ["x", "y"]),
            MockColumn("mean", [1.5, 2.5]),
        ])
        rows = table_rows(table)
        assert rows == [{"var": "x", "mean": 1.5}, {"var": "y", "mean": 2.5}]

    def test_missing_cell_is_none(self):
        table = MockTable([
            MockColumn("var", ["x"]),
            MockColumn("mean", [1.5, 2.5]),
        ])
        rows = table_rows(table)
        assert rows[0]["var"] == "x"
        assert rows[0]["mean"] == 1.5
        assert rows[1]["var"] is None
        assert rows[1]["mean"] == 2.5


class TestWalkResultElements:
    def test_walks_nested_groups(self):
        child = MockElement("child")
        parent = MockElement("parent", children=[child])
        root = MockRoot([parent])
        names = [n.name for n in walk_result_elements(root)]
        assert names == ["", "parent", "child"]


class TestFindFirstNamedElement:
    def test_finds_by_name(self):
        target = MockElement("target")
        root = MockRoot([MockElement("other"), target])
        assert find_first_named_element(root, "target") is target

    def test_missing_returns_none(self):
        root = MockRoot([MockElement("other")])
        assert find_first_named_element(root, "target") is None


class TestFindAllNamedElements:
    def test_finds_all_matching(self):
        a = MockElement("coef")
        b = MockElement("coef")
        root = MockRoot([a, MockElement("other"), b])
        results = find_all_named_elements(root, "coef")
        assert results == [a, b]


class TestFormatPairLabel:
    def test_var1_var2(self):
        row = {"var1": "Pre", "var2": "Post"}
        assert format_pair_label(row) == "Pre - Post"

    def test_fallback_to_pair(self):
        row = {"pair": "A vs B"}
        assert format_pair_label(row) == "A vs B"

    def test_only_one_side(self):
        row = {"var1": "Pre"}
        assert format_pair_label(row) == "Pre"


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------

class TestBuildDescriptivesSections:
    def test_simple_descriptives(self):
        table = MockTable([
            MockColumn("var", ["Creativity"]),
            MockColumn("mean", [3.82]),
            MockColumn("sd", [0.71]),
            MockColumn("n", [120]),
        ])
        root = MockRoot([MockElement("descriptives", table=table)])
        sections = build_summary_sections("descriptives", root)
        assert len(sections) == 1
        assert sections[0]["title"] == "Key Results"
        row = sections[0]["rows"][0]
        assert row["Variable"] == "Creativity"
        assert row["Mean"] == "3.82"
        assert row["SD"] == "0.71"
        assert row["N"] == "120"

    def test_skips_placeholder_rows(self):
        table = MockTable([
            MockColumn("var", ["Overall", ""]),
            MockColumn("mean", [3.5, 2.0]),
            MockColumn("sd", [0.8, 0.5]),
        ])
        root = MockRoot([MockElement("descriptives", table=table)])
        sections = build_summary_sections("descriptives", root)
        assert sections == []


class TestBuildTtestSections:
    def test_student_ttest(self):
        table = MockTable([
            MockColumn("var", ["Score"]),
            MockColumn("stat[stud]", [2.17]),
            MockColumn("df[stud]", [49]),
            MockColumn("p[stud]", [0.021]),
            MockColumn("es[stud]", [0.53]),
            MockColumn("esType[stud]", ["Cohen's d"]),
        ])
        root = MockRoot([MockElement("ttest", table=table)])
        sections = build_summary_sections("ttestIS", root)
        assert sections[0]["title"] == "Key Results"
        row = sections[0]["rows"][0]
        assert row["Variable"] == "Score"
        assert row["Statistic"] == "2.17"
        assert row["p"] == ".021"
        assert row["Cohen's d"] == "0.53"


class TestBuildTtestPsSections:
    def test_paired_ttest(self):
        table = MockTable([
            MockColumn("var1", ["Post"]),
            MockColumn("var2", ["Pre"]),
            MockColumn("stat[stud]", [4.25]),
            MockColumn("df[stud]", [24]),
            MockColumn("p[stud]", [0.0005]),
        ])
        root = MockRoot([MockElement("ttest", table=table)])
        sections = build_summary_sections("ttestPS", root)
        row = sections[0]["rows"][0]
        assert row["Pair"] == "Post - Pre"
        assert row["p"] == "<.001"


class TestBuildAnovaSections:
    def test_anova_key_results(self):
        table = MockTable([
            MockColumn("dep", ["Creativity"]),
            MockColumn("F[fisher]", [5.94]),
            MockColumn("df1[fisher]", [2]),
            MockColumn("df2[fisher]", [87]),
            MockColumn("p[fisher]", [0.007]),
        ])
        root = MockRoot([MockElement("anova", table=table)])
        sections = build_summary_sections("anovaOneW", root)
        row = sections[0]["rows"][0]
        assert row["Dependent Variable"] == "Creativity"
        assert row["F"] == "5.94"
        assert row["p"] == ".007"
        assert row["etaSqP"] == "0.12"  # computed from F, df1, df2

    def test_anova_computes_eta_sq_p_from_f_and_dfs(self):
        table = MockTable([
            MockColumn("dep", ["Score"]),
            MockColumn("F[fisher]", [4.0]),
            MockColumn("df1[fisher]", [2]),
            MockColumn("df2[fisher]", [36]),
            MockColumn("p[fisher]", [0.03]),
        ])
        root = MockRoot([MockElement("anova", table=table)])
        sections = build_summary_sections("anovaOneW", root)
        row = sections[0]["rows"][0]
        # etaSqP = 4 * 2 / (4 * 2 + 36) = 8 / 44 = 0.1818...
        assert row["etaSqP"] == "0.18"

    def test_anova_descriptives(self):
        anova_table = MockTable([MockColumn("dep", [])])
        desc_table = MockTable([
            MockColumn("dep", ["Creativity"]),
            MockColumn("group", ["Exp"]),
            MockColumn("num", [30]),
            MockColumn("mean", [85.6]),
            MockColumn("sd", [6.4]),
        ])
        root = MockRoot([
            MockElement("anova", table=anova_table),
            MockElement("desc", table=desc_table),
        ])
        sections = build_summary_sections("anovaOneW", root)
        assert len(sections) == 1  # only descriptives because anova rows empty
        assert sections[0]["title"] == "Group Descriptives"


class TestBuildCorrSections:
    def test_correlation_pairs(self):
        table = MockTable([
            MockColumn(".name[r]", ["Algorithmic"]),
            MockColumn("Creativity[r]", [0.45]),
            MockColumn("Creativity[rdf]", [118]),
            MockColumn("Creativity[rp]", [0.001]),
            MockColumn("Creativity[n]", [120]),
        ])
        root = MockRoot([MockElement("matrix", table=table)])
        sections = build_summary_sections("corrMatrix", root)
        row = sections[0]["rows"][0]
        assert row["Variable 1"] == "Creativity"
        assert row["Variable 2"] == "Algorithmic"
        assert row["r"] == "0.45"
        assert row["p"] == ".001"


class TestBuildLinRegSections:
    def test_model_fit_and_coefficients(self):
        fit_table = MockTable([
            MockColumn("model", [1]),
            MockColumn("r2", [0.18]),
            MockColumn("r2Adj", [0.16]),
            MockColumn("f", [12.45]),
            MockColumn("df1", [2]),
            MockColumn("df2", [117]),
            MockColumn("p", [0.0001]),
        ])
        coef_table = MockTable([
            MockColumn("term", ["Age", "Gender"]),
            MockColumn("est", [0.15, -0.30]),
            MockColumn("se", [0.05, 0.12]),
            MockColumn("beta", [0.25, -0.18]),
            MockColumn("t", [3.0, -2.50]),
            MockColumn("p", [0.003, 0.014]),
        ])
        root = MockRoot([
            MockElement("modelFit", table=fit_table),
            MockElement("coef", table=coef_table),
        ])
        sections = build_summary_sections("linReg", root)
        assert sections[0]["title"] == "Model Fit"
        assert sections[1]["title"] == "Coefficients"
        assert sections[0]["rows"][0]["R2"] == "0.18"
        assert sections[1]["rows"][0]["beta"] == "0.25"
        assert sections[1]["rows"][1]["beta"] == "-0.18"

    def test_linreg_beta_omitted_when_not_present(self):
        fit_table = MockTable([
            MockColumn("model", [1]),
            MockColumn("r2", [0.10]),
            MockColumn("r2Adj", [0.08]),
            MockColumn("f", [5.0]),
            MockColumn("df1", [1]),
            MockColumn("df2", [48]),
            MockColumn("p", [0.03]),
        ])
        coef_table = MockTable([
            MockColumn("term", ["Age"]),
            MockColumn("est", [0.15]),
            MockColumn("se", [0.05]),
            MockColumn("t", [3.0]),
            MockColumn("p", [0.003]),
        ])
        root = MockRoot([
            MockElement("modelFit", table=fit_table),
            MockElement("coef", table=coef_table),
        ])
        sections = build_summary_sections("linReg", root)
        row = sections[1]["rows"][0]
        assert "beta" not in row


class TestBuildLogRegSections:
    def test_logistic_regression(self):
        fit_table = MockTable([
            MockColumn("model", [1]),
            MockColumn("r2mf", [0.14]),
            MockColumn("chi", [18.4]),
            MockColumn("df", [2]),
            MockColumn("p", [0.0001]),
        ])
        coef_table = MockTable([
            MockColumn("term", ["Age"]),
            MockColumn("est", [0.08]),
            MockColumn("se", [0.03]),
            MockColumn("z", [2.67]),
            MockColumn("p", [0.008]),
            MockColumn("odds", [1.08]),
        ])
        root = MockRoot([
            MockElement("modelFit", table=fit_table),
            MockElement("coef", table=coef_table),
        ])
        sections = build_summary_sections("logRegBin", root)
        assert sections[0]["rows"][0]["McFadden R2"] == "0.14"
        assert sections[1]["rows"][0]["OR"] == "1.08"


class TestBuildContTablesSections:
    def test_chi_square(self):
        chi_table = MockTable([
            MockColumn("test[chiSq]", ["Pearson"]),
            MockColumn("value[chiSq]", [14.14]),
            MockColumn("df[chiSq]", [2]),
            MockColumn("p[chiSq]", [0.001]),
            MockColumn("value[N]", [170]),
        ])
        root = MockRoot([MockElement("chiSq", table=chi_table)])
        sections = build_summary_sections("contTables", root)
        row = sections[0]["rows"][0]
        assert row["Test"] == "Pearson"
        assert row["N"] == "170"


class TestBuildReliabilitySections:
    def test_scale_reliability(self):
        table = MockTable([
            MockColumn("name", ["Creativity"]),
            MockColumn("mean", [3.82]),
            MockColumn("sd", [0.71]),
            MockColumn("alpha", [0.82]),
            MockColumn("omega", [0.84]),
        ])
        root = MockRoot([MockElement("scale", table=table)])
        sections = build_summary_sections("reliability", root)
        row = sections[0]["rows"][0]
        assert row["Scale"] == "Creativity"
        assert row["Cronbach Alpha"] == "0.82"
        assert row["McDonalds Omega"] == "0.84"
