"""Tests for jamovi_runner.preprocess data preparation and template validation."""

from pathlib import Path

import pytest

from jamovi_runner.preprocess import PreprocessError, preprocess_data, safe_alias


class TestSafeAlias:
    def test_basic_cleaning(self):
        seen: set[str] = set()
        assert safe_alias("Score", 0, seen) == "Score"

    def test_special_chars_replaced(self):
        seen: set[str] = set()
        assert safe_alias("Test Score!", 0, seen) == "Test_Score"

    def test_duplicate_names_numbered(self):
        seen: set[str] = set()
        assert safe_alias("Score", 0, seen) == "Score"
        assert safe_alias("Score", 1, seen) == "Score_1"
        assert safe_alias("Score", 2, seen) == "Score_2"

    def test_leading_digit_prefixes_with_var(self):
        seen: set[str] = set()
        assert safe_alias("1st_attempt", 0, seen) == "var_1st_attempt"

    def test_empty_name_uses_index(self):
        seen: set[str] = set()
        assert safe_alias("", 5, seen) == "var_5"


class TestPreprocessDataBasic:
    def test_reads_csv_and_builds_manifest(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("group,score\nA,85\nB,90\n", encoding="utf-8")

        out_csv, manifest, updated_spec, sidecar = preprocess_data(
            csv_path, {"analyses": []}, tmp_path
        )

        assert out_csv.exists()
        assert manifest == {"group": "group", "score": "score"}
        assert sidecar["analysis_ready"] == out_csv

    def test_unsupported_file_type_raises(self, tmp_path: Path):
        bad_path = tmp_path / "data.pdf"
        bad_path.write_text("x")
        with pytest.raises(PreprocessError, match="Unsupported data file type"):
            preprocess_data(bad_path, {"analyses": []}, tmp_path)


class TestPreprocessTemplateValidation:
    def test_reliability_scale_accepts_valid_integers(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("q01,q02,q03\n1,2,3\n4,5,5\n", encoding="utf-8")

        spec = {
            "template_hint": "reliability_scale",
            "analyses": [],
            "min_scale": 1,
            "max_scale": 5,
        }
        out_csv, manifest, updated_spec, sidecar = preprocess_data(
            csv_path, spec, tmp_path
        )
        assert out_csv.exists()

    def test_reliability_scale_rejects_out_of_range(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("q01,q02,q03\n1,2,6\n4,5,5\n", encoding="utf-8")

        spec = {
            "template_hint": "reliability_scale",
            "analyses": [],
            "min_scale": 1,
            "max_scale": 5,
        }
        with pytest.raises(PreprocessError, match="out of range"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_reliability_scale_rejects_non_integers(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("q01,q02,q03\n1,2.5,3\n4,5,5\n", encoding="utf-8")

        spec = {
            "template_hint": "reliability_scale",
            "analyses": [],
            "min_scale": 1,
            "max_scale": 5,
        }
        with pytest.raises(PreprocessError, match="integer"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_ttest_two_group_requires_exactly_two_groups(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("group,score\nA,85\nB,90\nC,95\n", encoding="utf-8")

        spec = {
            "template_hint": "ttest_two_group",
            "analyses": [],
            "group_column": "group",
        }
        with pytest.raises(PreprocessError, match="exactly 2 groups"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_missing_group_column_raises(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("group,score\nA,85\nB,90\n", encoding="utf-8")

        spec = {
            "template_hint": "ttest_two_group",
            "analyses": [],
            "group_column": "condition",
        }
        with pytest.raises(PreprocessError, match="not found"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_template_hint_none_skips_validation(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("q01,q02,q03\n1,2,6\n4,5,5\n", encoding="utf-8")

        spec = {"analyses": []}
        out_csv, manifest, updated_spec, sidecar = preprocess_data(
            csv_path, spec, tmp_path
        )
        assert out_csv.exists()


class TestPreprocessPrepostScaleStudy:
    def test_requires_pre_and_post_columns(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,q01,q02\nS1,1,2\nS2,3,4\n", encoding="utf-8")

        spec = {
            "template_hint": "prepost_scale_study",
            "analyses": [],
        }
        with pytest.raises(PreprocessError, match="pre_"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_valid_prepost_scale_study_passes(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,pre_q01,post_q01\nS1,1,3\nS2,2,4\n", encoding="utf-8")

        spec = {
            "template_hint": "prepost_scale_study",
            "analyses": [],
            "id_column": "user_id",
        }
        out_csv, manifest, updated_spec, sidecar = preprocess_data(
            csv_path, spec, tmp_path
        )
        assert out_csv.exists()

    def test_duplicate_ids_raise(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,pre_q01,post_q01\nS1,1,3\nS1,2,4\n", encoding="utf-8")

        spec = {
            "template_hint": "prepost_scale_study",
            "analyses": [],
            "id_column": "user_id",
        }
        with pytest.raises(PreprocessError, match="Duplicate id"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_scale_items_must_be_integers(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,pre_q01,post_q01\nS1,1.5,3\nS2,2,4\n", encoding="utf-8")

        spec = {
            "template_hint": "prepost_scale_study",
            "analyses": [],
            "id_column": "user_id",
        }
        with pytest.raises(PreprocessError, match="integer"):
            preprocess_data(csv_path, spec, tmp_path)


class TestPreprocessCrossSectionalSurvey:
    def test_requires_at_least_one_question_column(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,gender\nS1,M\nS2,F\n", encoding="utf-8")

        spec = {
            "template_hint": "cross_sectional_survey",
            "analyses": [],
        }
        with pytest.raises(PreprocessError, match="q\\d+"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_valid_cross_sectional_survey_passes(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,q01,q02\nS1,1,2\nS2,3,4\n", encoding="utf-8")

        spec = {
            "template_hint": "cross_sectional_survey",
            "analyses": [],
        }
        out_csv, manifest, updated_spec, sidecar = preprocess_data(
            csv_path, spec, tmp_path
        )
        assert out_csv.exists()

    def test_duplicate_user_ids_raise(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,q01,q02\nS1,1,2\nS1,3,4\n", encoding="utf-8")

        spec = {
            "template_hint": "cross_sectional_survey",
            "analyses": [],
        }
        with pytest.raises(PreprocessError, match="Duplicate user_id"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_scale_items_must_be_integers(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("user_id,q01,q02\nS1,1,2.5\nS2,3,4\n", encoding="utf-8")

        spec = {
            "template_hint": "cross_sectional_survey",
            "analyses": [],
        }
        with pytest.raises(PreprocessError, match="integer"):
            preprocess_data(csv_path, spec, tmp_path)


class TestPreprocessRegressionStudy:
    def test_requires_dependent_and_predictor_columns(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("y\n1\n2\n", encoding="utf-8")

        spec = {
            "template_hint": "regression_study",
            "analyses": [],
        }
        with pytest.raises(PreprocessError, match="predictor"):
            preprocess_data(csv_path, spec, tmp_path)

    def test_valid_regression_study_passes(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("y,x1,x2\n1,2,3\n4,5,6\n", encoding="utf-8")

        spec = {
            "template_hint": "regression_study",
            "analyses": [],
        }
        out_csv, manifest, updated_spec, sidecar = preprocess_data(
            csv_path, spec, tmp_path
        )
        assert out_csv.exists()

    def test_dependent_variable_must_be_numeric(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("y,x1\na,1\nb,2\n", encoding="utf-8")

        spec = {
            "template_hint": "regression_study",
            "analyses": [],
            "dependent_var": "y",
        }
        with pytest.raises(PreprocessError, match="numeric"):
            preprocess_data(csv_path, spec, tmp_path)
