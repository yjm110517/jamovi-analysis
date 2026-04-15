"""Lightweight integration checks that the runner script references new packages."""

from pathlib import Path


RUNNER_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run-jamovi-project.py"


def test_runner_imports_new_formatting_module():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "from jamovi_runner.formatting import" in source
    assert "from jamovi_runner.report import" in source


def test_runner_adds_src_to_sys_path():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert 'SRC_ROOT = str(PROJECT_ROOT / "src")' in source
    assert "sys.path.insert(0, SRC_ROOT)" in source


def test_runner_no_longer_defines_local_format_number():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    # The old local definitions should have been removed
    assert "def format_number(value: Any, *, digits: int = 4)" not in source
    assert "def format_p_value(value: Any) -> str:" not in source or "from jamovi_runner.formatting import" in source


def test_runner_uses_package_markdown_builder_for_apa():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "_build_markdown_report_from_package" in source


def test_runner_imports_extract_package_and_has_no_local_builders():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "from jamovi_runner.extract import build_summary_sections" in source
    assert "def build_descriptives_sections(" not in source
    assert "def build_ttest_sections(" not in source
    assert "def build_anova_sections(" not in source
    assert "def build_corr_sections(" not in source
    assert "def build_linreg_sections(" not in source
    assert "def build_logreg_sections(" not in source
    assert "def build_cont_tables_sections(" not in source
    assert "def build_reliability_sections(" not in source
    assert "SUMMARY_BUILDERS = {" not in source


def test_runner_imports_preprocess_package_and_has_no_local_definitions():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "from jamovi_runner.preprocess import preprocess_data, PreprocessError" in source
    assert "def safe_alias(" not in source
    assert "def preprocess_data(" not in source


def test_runner_has_no_local_report_or_docx_functions():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "def build_markdown_report(" not in source
    assert "def build_docx_report(" not in source
    assert "def render_markdown_html(" not in source
    assert "def export_report_formats(" not in source
    assert "def write_latex_bundle(" not in source
    assert "def normalize_output_stem(" not in source
    assert "def format_variables_for_markdown(" not in source
    assert "def _docx_style_exists(" not in source
    assert "def _set_cell_border(" not in source
    assert "def apply_apa_header_border(" not in source
