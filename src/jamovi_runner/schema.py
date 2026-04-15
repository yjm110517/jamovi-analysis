"""Configuration schema and validation for jamovi-analysis runs."""

from dataclasses import dataclass
from typing import Any


VALID_TEMPLATE_HINTS = frozenset(
    {
        "prepost_scale_study",
        "cross_sectional_survey",
        "ttest_two_group",
        "reliability_scale",
        "regression_study",
    }
)

VALID_TABLE_STYLES = frozenset({"gfm", "apa"})


class TemplateHint:
    """Template hint validation utilities."""

    @staticmethod
    def is_valid(hint: str | None) -> bool:
        return hint in VALID_TEMPLATE_HINTS

    @staticmethod
    def from_spec(spec: dict[str, Any]) -> str | None:
        return spec.get("template_hint")


@dataclass
class OutputConfig:
    """Validated output configuration."""

    table_style: str

    @classmethod
    def from_spec(cls, spec: dict[str, Any]) -> "OutputConfig":
        output = spec.get("output", {})
        raw_style = output.get("table_style", "gfm")
        style = str(raw_style).lower()
        if style not in VALID_TABLE_STYLES:
            raise ValueError(f"Invalid table_style '{raw_style}'. Must be one of: {', '.join(sorted(VALID_TABLE_STYLES))}.")
        return cls(table_style=style)


def validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a run specification dictionary.

    Raises:
        ValueError: If required fields are malformed.
    """
    validated: dict[str, Any] = dict(spec)

    template_hint = TemplateHint.from_spec(validated)
    if template_hint is not None and not TemplateHint.is_valid(template_hint):
        raise ValueError(
            f"Invalid template_hint '{template_hint}'. Must be one of: {', '.join(sorted(VALID_TEMPLATE_HINTS))}."
        )

    if "output" not in validated:
        validated["output"] = {}
    validated["output"] = dict(validated["output"])
    config = OutputConfig.from_spec(validated)
    validated["output"]["table_style"] = config.table_style

    if "analyses" in validated and not isinstance(validated["analyses"], list):
        raise ValueError("'analyses' must be a list.")

    return validated
