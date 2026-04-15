"""Jamovi result extractors — convert protobuf result trees into section dictionaries."""

from typing import Any

from jamovi_runner.extract.anova import build_anova_sections
from jamovi_runner.extract.cont_tables import build_cont_tables_sections
from jamovi_runner.extract.corr_matrix import build_corr_sections
from jamovi_runner.extract.descriptives import build_descriptives_sections
from jamovi_runner.extract.lin_reg import build_linreg_sections
from jamovi_runner.extract.log_reg_bin import build_logreg_sections
from jamovi_runner.extract.reliability import build_reliability_sections
from jamovi_runner.extract.ttest_is import build_ttest_sections
from jamovi_runner.extract.ttest_ps import build_ttestps_sections

SUMMARY_BUILDERS: dict[str, Any] = {
    "anovaOneW": build_anova_sections,
    "contTables": build_cont_tables_sections,
    "corrMatrix": build_corr_sections,
    "descriptives": build_descriptives_sections,
    "linReg": build_linreg_sections,
    "logRegBin": build_logreg_sections,
    "reliability": build_reliability_sections,
    "ttestIS": build_ttest_sections,
    "ttestPS": build_ttestps_sections,
}


def build_summary_sections(analysis_type: str, root: Any) -> list[dict[str, Any]]:
    builder = SUMMARY_BUILDERS.get(analysis_type)
    if builder is None:
        return []
    return builder(root)


__all__ = [
    "SUMMARY_BUILDERS",
    "build_summary_sections",
    "build_anova_sections",
    "build_cont_tables_sections",
    "build_corr_sections",
    "build_descriptives_sections",
    "build_linreg_sections",
    "build_logreg_sections",
    "build_reliability_sections",
    "build_ttest_sections",
    "build_ttestps_sections",
]
