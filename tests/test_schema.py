"""Tests for jamovi_runner.schema configuration validation."""

import pytest

from jamovi_runner.schema import OutputConfig, TemplateHint, validate_spec


class TestTemplateHint:
    def test_valid_hints(self):
        for hint in (
            "prepost_scale_study",
            "cross_sectional_survey",
            "ttest_two_group",
            "reliability_scale",
            "regression_study",
        ):
            assert TemplateHint.is_valid(hint) is True

    def test_invalid_hint(self):
        assert TemplateHint.is_valid("unknown_template") is False

    def test_from_spec_extracts_hint(self):
        spec = {"template_hint": "prepost_scale_study"}
        assert TemplateHint.from_spec(spec) == "prepost_scale_study"

    def test_from_spec_returns_none_when_missing(self):
        assert TemplateHint.from_spec({}) is None


class TestOutputConfig:
    def test_default_table_style_is_gfm(self):
        config = OutputConfig.from_spec({})
        assert config.table_style == "gfm"

    def test_apa_table_style_is_accepted(self):
        config = OutputConfig.from_spec({"output": {"table_style": "apa"}})
        assert config.table_style == "apa"

    def test_invalid_table_style_raises(self):
        with pytest.raises(ValueError, match="table_style"):
            OutputConfig.from_spec({"output": {"table_style": "invalid"}})

    def test_table_style_is_case_insensitive(self):
        config = OutputConfig.from_spec({"output": {"table_style": "APA"}})
        assert config.table_style == "apa"


class TestValidateSpec:
    def test_valid_spec_with_template_hint(self):
        spec = {
            "template_hint": "ttest_two_group",
            "output": {"table_style": "apa"},
        }
        validated = validate_spec(spec)
        assert validated["template_hint"] == "ttest_two_group"
        assert validated["output"]["table_style"] == "apa"

    def test_invalid_template_hint_raises(self):
        with pytest.raises(ValueError, match="template_hint"):
            validate_spec({"template_hint": "bad_hint"})

    def test_spec_without_output_gets_defaults(self):
        spec = {"analyses": []}
        validated = validate_spec(spec)
        assert validated["output"]["table_style"] == "gfm"

    def test_analyses_must_be_list(self):
        with pytest.raises(ValueError, match="analyses"):
            validate_spec({"analyses": "not_a_list"})

    def test_unknown_keys_are_allowed_but_logged(self):
        spec = {"unknown_key": 123}
        validated = validate_spec(spec)
        assert validated["unknown_key"] == 123
