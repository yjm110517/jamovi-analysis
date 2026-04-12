from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_JAMOVI_HOME = Path(os.environ.get("JAMOVI_HOME", r"C:\Program Files\jamovi 2.6.19.0"))
SERVER_ROOT = DEFAULT_JAMOVI_HOME / "Resources" / "server"

if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

if os.environ.get("JAMOVI_PROJECT_RUNNER") != "1":
    raise SystemExit("run-jamovi-project.py must be launched via invoke-jamovi-project.ps1")

from jamovi.core import DataType, MeasureType  # noqa: E402
from jamovi.server.analyses.analysis import Analysis  # noqa: E402
from jamovi.server.options import Options  # noqa: E402
from jamovi.server.session import Session  # noqa: E402


class RunnerError(Exception):
    pass


class ParseContractError(RunnerError):
    pass


class SpecError(RunnerError):
    pass


class ValidationError(RunnerError):
    pass


@dataclass
class RoleSpec:
    mode: str
    measure: str = "any"
    required: bool = True
    min_items: int = 1
    max_items: int | None = None
    min_levels: int | None = None
    max_levels: int | None = None


@dataclass
class AnalysisResultRecord:
    analysis_type: str
    title: str
    variables: dict[str, Any]
    options: dict[str, Any]
    status: str
    status_detail: str
    summary_sections: list[dict[str, Any]] = field(default_factory=list)
    note: str | None = None


ANALYSIS_ALIASES = {
    "anova": "anovaOneW",
    "anovaonew": "anovaOneW",
    "chi-square": "contTables",
    "chisquare": "contTables",
    "conttables": "contTables",
    "corrmatrix": "corrMatrix",
    "correlation": "corrMatrix",
    "descriptive": "descriptives",
    "descriptives": "descriptives",
    "linear-regression": "linReg",
    "linear_regression": "linReg",
    "linreg": "linReg",
    "logistic-regression": "logRegBin",
    "logistic_regression": "logRegBin",
    "logregbin": "logRegBin",
    "reliability": "reliability",
    "ttest": "ttestIS",
    "ttestis": "ttestIS",
}

SUPPORTED_ANALYSES: dict[str, dict[str, Any]] = {
    "descriptives": {
        "title": "Descriptives",
        "namespace": "jmv",
        "roles": {
            "vars": RoleSpec("variables", measure="any", required=True, min_items=1),
            "splitBy": RoleSpec("variables", measure="categorical", required=False, min_items=1),
        },
    },
    "ttestIS": {
        "title": "Independent Samples T-Test",
        "namespace": "jmv",
        "roles": {
            "vars": RoleSpec("variables", measure="continuous", required=True, min_items=1),
            "group": RoleSpec("variable", measure="categorical", required=True, min_levels=2, max_levels=2),
        },
    },
    "anovaOneW": {
        "title": "One-Way ANOVA",
        "namespace": "jmv",
        "roles": {
            "deps": RoleSpec("variables", measure="continuous", required=True, min_items=1),
            "group": RoleSpec("variable", measure="categorical", required=True, min_levels=2),
        },
    },
    "corrMatrix": {
        "title": "Correlation Matrix",
        "namespace": "jmv",
        "roles": {
            "vars": RoleSpec("variables", measure="continuous", required=True, min_items=2),
        },
    },
    "linReg": {
        "title": "Linear Regression",
        "namespace": "jmv",
        "roles": {
            "dep": RoleSpec("variable", measure="continuous", required=True),
            "covs": RoleSpec("variables", measure="continuous", required=False, min_items=1),
            "factors": RoleSpec("variables", measure="categorical", required=False, min_items=1),
            "weights": RoleSpec("variable", measure="continuous", required=False),
        },
    },
    "logRegBin": {
        "title": "Binomial Logistic Regression",
        "namespace": "jmv",
        "roles": {
            "dep": RoleSpec("variable", measure="categorical", required=True, min_levels=2, max_levels=2),
            "covs": RoleSpec("variables", measure="continuous", required=False, min_items=1),
            "factors": RoleSpec("variables", measure="categorical", required=False, min_items=1),
        },
    },
    "contTables": {
        "title": "Contingency Tables",
        "namespace": "jmv",
        "roles": {
            "rows": RoleSpec("variable", measure="categorical", required=True, min_levels=2),
            "cols": RoleSpec("variable", measure="categorical", required=True, min_levels=2),
            "layers": RoleSpec("variables", measure="categorical", required=False, min_items=1),
            "counts": RoleSpec("variable", measure="continuous", required=False),
        },
    },
    "reliability": {
        "title": "Reliability Analysis",
        "namespace": "jmv",
        "roles": {
            "vars": RoleSpec("variables", measure="continuous_or_ordinal", required=True, min_items=2),
            "revItems": RoleSpec("variables", measure="continuous_or_ordinal", required=False, min_items=1),
        },
    },
}

DEFAULT_OPTION_OVERRIDES = {
    "descriptives": {"n": True, "missing": True, "mean": True, "median": True, "sd": True, "min": True, "max": True},
    "ttestIS": {"students": True, "welchs": True, "effectSize": True, "ci": True, "desc": True},
    "anovaOneW": {"welchs": True, "fishers": True, "desc": True},
    "corrMatrix": {"pearson": True, "sig": True, "n": True},
    "linReg": {"r": True, "r2": True, "r2Adj": True, "modelTest": True, "ci": True},
    "logRegBin": {"dev": True, "aic": True, "modelTest": True, "ci": True, "OR": True, "ciOR": True},
    "contTables": {"chiSq": True, "phiCra": True, "obs": True},
    "reliability": {"alphaScale": True, "meanScale": True, "sdScale": True},
}

MEASURE_ALIASES = {
    "categorical": MeasureType.NOMINAL,
    "continuous": MeasureType.CONTINUOUS,
    "nominal": MeasureType.NOMINAL,
    "ordinal": MeasureType.ORDINAL,
    "scale": MeasureType.CONTINUOUS,
}

NUMERIC_DATA_TYPES = {DataType.INTEGER, DataType.DECIMAL}
BOUNDARY = r"(?<![0-9A-Za-z_]){pattern}(?![0-9A-Za-z_])"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run jamovi project-mode analyses and save .omv output.")
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--spec-json")
    parser.add_argument("--spec-file")
    parser.add_argument("--request")
    parser.add_argument("--request-file")
    parser.add_argument("--output-dir")
    parser.add_argument("--output-basename")
    parser.add_argument("--analysis-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--poll-interval-ms", type=int, default=250)
    return parser.parse_args()


def strip_json_wrappers(text: str) -> str:
    candidate = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    if candidate.startswith("{") or candidate.startswith("["):
        return candidate

    first_obj = candidate.find("{")
    last_obj = candidate.rfind("}")
    if first_obj != -1 and last_obj != -1 and first_obj < last_obj:
        return candidate[first_obj:last_obj + 1].strip()

    first_arr = candidate.find("[")
    last_arr = candidate.rfind("]")
    if first_arr != -1 and last_arr != -1 and first_arr < last_arr:
        return candidate[first_arr:last_arr + 1].strip()

    return candidate


def load_json_text(raw_text: str, source_label: str) -> Any:
    cleaned = strip_json_wrappers(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ParseContractError(f"Could not parse JSON from {source_label}: {exc}") from exc


def normalize_analysis_type(value: str) -> str:
    key = value.strip()
    if not key:
        raise SpecError("analysis_type cannot be blank")
    lowered = key.casefold()
    normalized = ANALYSIS_ALIASES.get(lowered, key)
    if normalized not in SUPPORTED_ANALYSES:
        raise SpecError(
            f"Unsupported analysis_type '{value}'. Supported values: {', '.join(sorted(SUPPORTED_ANALYSES))}"
        )
    return normalized


def ensure_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SpecError(f"{field_name} must be an object")
    return dict(value)


def normalize_analysis_spec(raw_spec: dict[str, Any]) -> dict[str, Any]:
    analysis_type = normalize_analysis_type(str(raw_spec.get("analysis_type", "")))
    variables = ensure_mapping(raw_spec.get("variables"), "variables")
    options = ensure_mapping(raw_spec.get("options"), "options")
    measure_overrides = ensure_mapping(raw_spec.get("measure_overrides"), "measure_overrides")
    namespace = raw_spec.get("namespace") or raw_spec.get("ns") or SUPPORTED_ANALYSES[analysis_type]["namespace"]
    if namespace != "jmv":
        raise SpecError("Only namespace 'jmv' is supported in project mode v1")
    return {
        "analysis_type": analysis_type,
        "namespace": namespace,
        "variables": variables,
        "options": options,
        "measure_overrides": measure_overrides,
        "output_basename": raw_spec.get("output_basename"),
    }


def normalize_top_level_spec(raw_spec: Any) -> dict[str, Any]:
    if not isinstance(raw_spec, dict):
        raise SpecError("Top-level spec must be a JSON object")

    if "analysis_spec" in raw_spec and "is_executable" in raw_spec:
        contract = normalize_parse_contract(raw_spec)
        if not contract["is_executable"]:
            raise ParseContractError(contract["missing_info"] or "Request is not executable")
        return contract["analysis_spec"]

    top_measure_overrides = ensure_mapping(raw_spec.get("measure_overrides"), "measure_overrides")
    output_basename = raw_spec.get("output_basename")

    if "analyses" in raw_spec:
        analyses_value = raw_spec["analyses"]
        if not isinstance(analyses_value, list) or not analyses_value:
            raise SpecError("analyses must be a non-empty array")
        analyses = [normalize_analysis_spec(item) for item in analyses_value]
    elif "analysis_type" in raw_spec:
        analyses = [normalize_analysis_spec(raw_spec)]
    else:
        raise SpecError("Spec must contain analysis_type or analyses")

    return {
        "output_basename": output_basename,
        "measure_overrides": top_measure_overrides,
        "analyses": analyses,
    }


def parse_inline_or_file_spec(args: argparse.Namespace) -> dict[str, Any]:
    if bool(args.spec_json) == bool(args.spec_file):
        raise SpecError("Provide exactly one of --spec-json or --spec-file for structured mode")

    if args.spec_json:
        raw_spec = load_json_text(args.spec_json, "--spec-json")
    else:
        raw_spec = load_json_text(Path(args.spec_file).read_text(encoding="utf-8"), "--spec-file")

    return normalize_top_level_spec(raw_spec)


def make_parse_contract(is_executable: bool, missing_info: str, analysis_spec: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "is_executable": is_executable,
        "missing_info": missing_info,
        "analysis_spec": analysis_spec,
    }


def normalize_parse_contract(raw_contract: Any) -> dict[str, Any]:
    if not isinstance(raw_contract, dict):
        raise ParseContractError("NL parser output must be a JSON object")

    is_executable = bool(raw_contract.get("is_executable"))
    missing_info = str(raw_contract.get("missing_info", "") or "")
    raw_analysis_spec = raw_contract.get("analysis_spec")

    if is_executable and raw_analysis_spec is None:
        raise ParseContractError("analysis_spec is required when is_executable is true")
    if not is_executable and missing_info == "":
        missing_info = "The request could not be executed because required information is missing or ambiguous."

    analysis_spec = None
    if raw_analysis_spec is not None:
        analysis_spec = normalize_top_level_spec(raw_analysis_spec)

    return make_parse_contract(is_executable, missing_info, analysis_spec)


def read_dataset_headers(data_path: Path) -> list[str]:
    suffix = data_path.suffix.lower()
    if suffix in {".csv", ".txt", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else None
        with data_path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            if delimiter is None:
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ","
            reader = csv.reader(handle, delimiter=delimiter)
            for row in reader:
                if row:
                    return [cell.strip() for cell in row if cell.strip()]
        return []

    if suffix in {".xlsx", ".xlsm"}:
        try:
            import openpyxl  # type: ignore
        except Exception:
            return []
        workbook = openpyxl.load_workbook(data_path, read_only=True, data_only=True)
        worksheet = workbook.active
        first_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        workbook.close()
        return [str(cell).strip() for cell in first_row if cell is not None and str(cell).strip()]

    return []


def extract_column_mentions(text: str, columns: Sequence[str]) -> list[str]:
    matches: list[tuple[int, str]] = []
    for column in columns:
        pattern = re.compile(BOUNDARY.format(pattern=re.escape(column)), flags=re.IGNORECASE)
        match = pattern.search(text)
        if match:
            matches.append((match.start(), column))
    matches.sort(key=lambda item: item[0])

    ordered: list[str] = []
    seen: set[str] = set()
    for _, column in matches:
        if column not in seen:
            seen.add(column)
            ordered.append(column)
    return ordered


def parse_by_expression(request: str, mentions: Sequence[str]) -> tuple[str, str] | None:
    if len(mentions) < 2:
        return None

    ordered_mentions = sorted(mentions, key=lambda column: request.casefold().find(column.casefold()))
    first = ordered_mentions[0]
    second = ordered_mentions[1]
    first_pos = request.casefold().find(first.casefold())
    second_pos = request.casefold().find(second.casefold())
    if first_pos == -1 or second_pos == -1 or first_pos >= second_pos:
        return None

    between = request[first_pos + len(first):second_pos].casefold()
    if any(token in between for token in (" by ", "~", " 按", " 根据", " grouped ", " group ", " 分组")):
        return first, second

    return None


def parse_regression_expression(request: str, mentions: Sequence[str]) -> tuple[str, list[str]] | None:
    if len(mentions) < 2:
        return None

    lowered = request.casefold()
    connector_index = -1
    connector = ""
    for token in (" from ", " on ", " using ", " with ", " 由", " 使用"):
        connector_index = lowered.find(token)
        if connector_index != -1:
            connector = token
            break
    if connector_index == -1:
        return None

    before = request[:connector_index]
    after = request[connector_index + len(connector):]

    dep_mentions = extract_column_mentions(before, mentions)
    pred_mentions = extract_column_mentions(after, mentions)
    if len(dep_mentions) != 1 or not pred_mentions:
        return None
    return dep_mentions[0], pred_mentions


def parse_nl_request(request: str, columns: Sequence[str]) -> dict[str, Any]:
    stripped = request.strip()
    if not stripped:
        return make_parse_contract(False, "The natural-language request is empty.", None)

    json_candidate = strip_json_wrappers(stripped)
    if json_candidate.startswith("{"):
        try:
            return normalize_parse_contract(load_json_text(stripped, "NL request"))
        except Exception as exc:
            return make_parse_contract(False, f"Could not parse NL parser JSON: {exc}", None)

    mentions = extract_column_mentions(stripped, columns)
    lowered = stripped.casefold()

    if any(token in lowered for token in ("descriptive", "descriptives", "summary", "summarize", "描述统计", "描述性统计")):
        if not mentions:
            return make_parse_contract(False, "Mention at least one exact column name for descriptives.", None)
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "descriptives", "variables": {"vars": mentions}}),
        )

    if any(token in lowered for token in ("correlation", "correlate", "相关", "相关性")):
        if len(mentions) < 2:
            return make_parse_contract(False, "Mention at least two exact column names for a correlation analysis.", None)
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "corrMatrix", "variables": {"vars": mentions}}),
        )

    if any(token in lowered for token in ("cronbach", "reliability", "alpha", "信度")):
        if len(mentions) < 2:
            return make_parse_contract(False, "Mention at least two exact column names for reliability analysis.", None)
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "reliability", "variables": {"vars": mentions}}),
        )

    if any(token in lowered for token in ("chi-square", "chi square", "contingency", "列联", "卡方")):
        if len(mentions) != 2:
            return make_parse_contract(
                False,
                "Mention exactly two exact column names for contingency-table analysis so rows and columns are unambiguous.",
                None,
            )
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "contTables", "variables": {"rows": mentions[0], "cols": mentions[1]}}),
        )

    if any(token in lowered for token in ("independent samples t-test", "independent t-test", "ttest", "t-test", "独立样本t", "独立样本 t")):
        parsed = parse_by_expression(stripped, mentions)
        if parsed is None:
            return make_parse_contract(
                False,
                "Use an explicit pattern like 'score by group' with exact column names for an independent-samples t-test.",
                None,
            )
        dep, group = parsed
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "ttestIS", "variables": {"vars": [dep], "group": group}}),
        )

    if any(token in lowered for token in ("anova", "one-way", "单因素方差", "单因素 anova")):
        parsed = parse_by_expression(stripped, mentions)
        if parsed is None:
            return make_parse_contract(
                False,
                "Use an explicit pattern like 'score by group' with exact column names for one-way ANOVA.",
                None,
            )
        dep, group = parsed
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "anovaOneW", "variables": {"deps": [dep], "group": group}}),
        )

    if any(token in lowered for token in ("logistic regression", "logistic", "logit", "逻辑回归", "二元logistic")):
        parsed = parse_regression_expression(stripped, mentions)
        if parsed is None:
            return make_parse_contract(
                False,
                "Use an explicit pattern like 'predict outcome from x1 and x2' with exact column names for logistic regression.",
                None,
            )
        dep, predictors = parsed
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "logRegBin", "variables": {"dep": dep, "predictors": predictors}}),
        )

    if any(token in lowered for token in ("linear regression", "regress", "回归", "线性回归", "predict ")):
        parsed = parse_regression_expression(stripped, mentions)
        if parsed is None:
            return make_parse_contract(
                False,
                "Use an explicit pattern like 'predict outcome from x1 and x2' with exact column names for linear regression.",
                None,
            )
        dep, predictors = parsed
        return make_parse_contract(
            True,
            "",
            normalize_top_level_spec({"analysis_type": "linReg", "variables": {"dep": dep, "predictors": predictors}}),
        )

    supported = "descriptives, ttestIS, anovaOneW, corrMatrix, linReg, logRegBin, contTables, reliability"
    return make_parse_contract(
        False,
        f"Could not deterministically map the request to a supported analysis. Supported NL intents: {supported}.",
        None,
    )


def current_measure_name(column: Any) -> str:
    return getattr(getattr(column, "measure_type", None), "name", str(column.measure_type)).lower()


def current_data_type_name(column: Any) -> str:
    return getattr(getattr(column, "data_type", None), "name", str(column.data_type)).lower()


def build_column_map(data: Any) -> dict[str, Any]:
    columns: dict[str, Any] = {}
    for column in data:
        name = getattr(column, "name", "")
        if not name or getattr(column, "is_virtual", False):
            continue
        columns[name] = column
    return columns


def normalize_variable_binding(value: Any, role: RoleSpec, role_name: str) -> str | list[str] | None:
    if value is None:
        return None

    if role.mode == "variable":
        if isinstance(value, list):
            if len(value) != 1:
                raise SpecError(f"variables.{role_name} must be a single column name")
            value = value[0]
        if not isinstance(value, str) or not value.strip():
            raise SpecError(f"variables.{role_name} must be a column name")
        return value.strip()

    if isinstance(value, str):
        values = [value.strip()] if value.strip() else []
    elif isinstance(value, list):
        values = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise SpecError(f"variables.{role_name} must contain only non-empty column names")
            values.append(item.strip())
    else:
        raise SpecError(f"variables.{role_name} must be a column name or an array of column names")

    if role.required and len(values) < role.min_items:
        raise SpecError(f"variables.{role_name} requires at least {role.min_items} column name(s)")
    if role.max_items is not None and len(values) > role.max_items:
        raise SpecError(f"variables.{role_name} accepts at most {role.max_items} column name(s)")
    return values


def set_measure(column: Any, measure: MeasureType) -> None:
    if column.measure_type == measure:
        return
    column.change(measure_type=measure)


def apply_explicit_measure_override(column: Any, override_name: str) -> None:
    normalized = override_name.strip().casefold()
    if normalized not in MEASURE_ALIASES:
        raise ValidationError(
            f"Unsupported measure override '{override_name}' for column '{column.name}'. Use nominal, ordinal, or continuous."
        )

    target = MEASURE_ALIASES[normalized]
    if target == MeasureType.CONTINUOUS and column.data_type not in NUMERIC_DATA_TYPES:
        raise ValidationError(
            f"Column '{column.name}' cannot be forced to continuous because its data_type is {current_data_type_name(column)}."
        )
    set_measure(column, target)


def ensure_measure_requirements(column: Any, requirement: str) -> None:
    if requirement == "any":
        return

    if requirement == "continuous":
        if column.data_type not in NUMERIC_DATA_TYPES:
            raise ValidationError(
                f"Column '{column.name}' must be numeric for a continuous role, but data_type is {current_data_type_name(column)}."
            )
        set_measure(column, MeasureType.CONTINUOUS)
        return

    if requirement == "categorical":
        if column.measure_type not in {MeasureType.NOMINAL, MeasureType.ORDINAL}:
            set_measure(column, MeasureType.NOMINAL)
        return

    if requirement == "continuous_or_ordinal":
        if column.data_type not in NUMERIC_DATA_TYPES:
            raise ValidationError(
                f"Column '{column.name}' must be numeric for this analysis, but data_type is {current_data_type_name(column)}."
            )
        if column.measure_type not in {MeasureType.CONTINUOUS, MeasureType.ORDINAL}:
            set_measure(column, MeasureType.CONTINUOUS)
        return

    raise ValidationError(f"Unhandled measure requirement '{requirement}'")


def ensure_level_count(column: Any, role_name: str, role: RoleSpec) -> None:
    if role.min_levels is None and role.max_levels is None:
        return

    level_count = getattr(column, "level_count", None)
    if level_count is None:
        return
    if role.min_levels is not None and level_count < role.min_levels:
        raise ValidationError(
            f"Column '{column.name}' must have at least {role.min_levels} levels for role '{role_name}', but has {level_count}."
        )
    if role.max_levels is not None and level_count > role.max_levels:
        raise ValidationError(
            f"Column '{column.name}' must have at most {role.max_levels} levels for role '{role_name}', but has {level_count}."
        )


def split_predictors_by_measure(predictors: Sequence[str], column_map: dict[str, Any]) -> tuple[list[str], list[str]]:
    covs: list[str] = []
    factors: list[str] = []
    for predictor in predictors:
        column = column_map[predictor]
        if column.measure_type in {MeasureType.NOMINAL, MeasureType.ORDINAL}:
            factors.append(predictor)
        elif column.data_type in NUMERIC_DATA_TYPES:
            covs.append(predictor)
        else:
            factors.append(predictor)
    return covs, factors


def apply_measure_overrides(column_map: dict[str, Any], overrides: dict[str, Any]) -> None:
    for column_name, measure_name in overrides.items():
        if column_name not in column_map:
            raise ValidationError(f"measure_overrides references unknown column '{column_name}'.")
        if not isinstance(measure_name, str):
            raise ValidationError(f"measure_overrides['{column_name}'] must be a string.")
        apply_explicit_measure_override(column_map[column_name], measure_name)


def prepare_analysis_payload(
    spec: dict[str, Any],
    column_map: dict[str, Any],
    global_measure_overrides: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    analysis_type = spec["analysis_type"]
    analysis_config = SUPPORTED_ANALYSES[analysis_type]
    roles: dict[str, RoleSpec] = analysis_config["roles"]
    variables = dict(spec.get("variables", {}))

    if analysis_type in {"linReg", "logRegBin"} and "predictors" in variables:
        raw_predictors = variables.pop("predictors")
        predictor_role = RoleSpec("variables", measure="any", required=True, min_items=1)
        normalized_predictors = normalize_variable_binding(raw_predictors, predictor_role, "predictors")
        assert isinstance(normalized_predictors, list)
        missing = [name for name in normalized_predictors if name not in column_map]
        if missing:
            raise ValidationError(f"Unknown predictor column(s): {', '.join(missing)}")
        covs, factors = split_predictors_by_measure(normalized_predictors, column_map)
        if covs:
            variables.setdefault("covs", covs)
        if factors:
            variables.setdefault("factors", factors)

    combined_measure_overrides = dict(global_measure_overrides)
    combined_measure_overrides.update(spec.get("measure_overrides", {}))
    apply_measure_overrides(column_map, combined_measure_overrides)

    normalized_variables: dict[str, Any] = {}
    for role_name, role in roles.items():
        raw_value = variables.get(role_name)
        normalized_value = normalize_variable_binding(raw_value, role, role_name)
        if normalized_value is None:
            if role.required:
                raise ValidationError(f"variables.{role_name} is required for {analysis_type}.")
            continue
        names = [normalized_value] if isinstance(normalized_value, str) else normalized_value
        missing = [name for name in names if name not in column_map]
        if missing:
            raise ValidationError(f"Unknown column(s) for role '{role_name}': {', '.join(missing)}")
        for name in names:
            column = column_map[name]
            ensure_measure_requirements(column, role.measure)
            ensure_level_count(column, role_name, role)
        normalized_variables[role_name] = normalized_value

    options = dict(DEFAULT_OPTION_OVERRIDES.get(analysis_type, {}))
    options.update(spec.get("options", {}))

    if analysis_type in {"linReg", "logRegBin"} and "blocks" not in options:
        predictors: list[str] = []
        predictors.extend(normalized_variables.get("covs", []))
        predictors.extend(normalized_variables.get("factors", []))
        if predictors:
            options["blocks"] = [predictors]

    payload = dict(normalized_variables)
    payload.update(options)
    return normalized_variables, payload


async def drain_progress_stream(stream: Any) -> Any:
    async for _ in stream:
        pass
    return stream.result()


def result_error_message(analysis: Any) -> str:
    analysis_response = getattr(analysis, "results", None)
    if analysis_response is None:
        return ""
    try:
        return analysis_response.results.error.message or ""
    except Exception:
        return ""


async def poll_analysis(analysis: Any, session: Session, timeout_seconds: float, poll_interval_seconds: float) -> tuple[str, str]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while True:
        message = result_error_message(analysis)
        if message:
            return "error", message

        status_name = getattr(getattr(analysis, "status", None), "name", str(getattr(analysis, "status", "")))
        if status_name == "COMPLETE":
            return "complete", ""
        if status_name == "ERROR":
            return "error", message or "Analysis returned ANALYSIS_ERROR."

        if loop.time() >= deadline:
            timeout_message = f"Timed out after {timeout_seconds:.1f}s while waiting for {analysis.name}."
            try:
                analysis.set_error(timeout_message)
                analysis.set_status(Analysis.Status.ERROR)
            except Exception:
                pass
            try:
                await session.restart_engines()
            except Exception as exc:
                timeout_message = f"{timeout_message} Engine restart failed: {exc}"
            return "timeout", timeout_message

        await asyncio.sleep(poll_interval_seconds)


def cell_value(cell: Any) -> Any:
    fields = cell.ListFields()
    if not fields:
        return None
    descriptor, value = fields[0]
    if descriptor.name == "o":
        return None
    return value


def clean_value(value: Any) -> Any:
    if value in ("", ".", "—"):
        return None
    return value


def table_rows(table: Any) -> list[dict[str, Any]]:
    columns = list(table.columns)
    row_count = max((len(column.cells) for column in columns), default=0)
    rows: list[dict[str, Any]] = []
    for row_index in range(row_count):
        row: dict[str, Any] = {}
        for column in columns:
            row[column.name] = clean_value(cell_value(column.cells[row_index])) if row_index < len(column.cells) else None
        rows.append(row)
    return rows


def walk_result_elements(node: Any) -> Iterable[Any]:
    yield node
    if node.HasField("group"):
        for child in node.group.elements:
            yield from walk_result_elements(child)
    if node.HasField("array"):
        for child in node.array.elements:
            yield from walk_result_elements(child)


def find_first_named_element(root: Any, name: str) -> Any | None:
    for node in walk_result_elements(root):
        if getattr(node, "name", "") == name:
            return node
    return None


def find_all_named_elements(root: Any, name: str) -> list[Any]:
    return [node for node in walk_result_elements(root) if getattr(node, "name", "") == name]


def format_number(value: Any, *, digits: int = 4) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:.2f}"
        if value.is_integer():
            return str(int(value))
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def format_p_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if value < 0.001:
        return "< 0.001"
    return format_number(value, digits=4)


def markdown_table(rows: Sequence[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No extractable rows were available."]

    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [str(row.get(column, "") or "") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def format_variables_for_markdown(variables: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key, value in variables.items():
        if isinstance(value, list):
            chunks.append(f"{key}={', '.join(f'`{item}`' for item in value)}")
        else:
            chunks.append(f"{key}=`{value}`")
    return "; ".join(chunks)


def build_descriptives_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "descriptives")
    if element is None or not element.HasField("table"):
        return []

    metrics: dict[str, dict[str, Any]] = {}
    for column in element.table.columns:
        match = re.match(r"(.+)\[([^\]]+)\]$", column.name)
        if not match:
            continue
        variable_name, stat_name = match.groups()
        if variable_name == "stat":
            continue
        metrics.setdefault(variable_name, {})[stat_name] = clean_value(cell_value(column.cells[0])) if column.cells else None

    rows = []
    for variable_name, stats in metrics.items():
        rows.append(
            {
                "Variable": variable_name,
                "N": format_number(stats.get("n")),
                "Missing": format_number(stats.get("missing")),
                "Mean": format_number(stats.get("mean")),
                "Median": format_number(stats.get("median")),
                "SD": format_number(stats.get("sd")),
                "Min": format_number(stats.get("min")),
                "Max": format_number(stats.get("max")),
            }
        )
    return [{"title": "Key Results", "rows": rows}]


def build_ttest_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "ttest")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    for suffix in ("stud", "welc", "mann"):
        values = {}
        for key in ("var", "name", "stat", "df", "p", "es", "esType"):
            column_name = f"{key}[{suffix}]"
            for column in element.table.columns:
                if column.name == column_name and column.cells:
                    values[key] = clean_value(cell_value(column.cells[0]))
                    break
        if not values.get("name"):
            continue
        if values.get("stat") is None and values.get("p") is None:
            continue
        row = {
            "Variable": values.get("var") or "",
            "Test": values.get("name") or "",
            "Statistic": format_number(values.get("stat")),
            "df": format_number(values.get("df")),
            "p": format_p_value(values.get("p")),
        }
        if values.get("es") is not None:
            label = values.get("esType") or "Effect Size"
            row[str(label)] = format_number(values.get("es"))
        rows.append(row)

    sections = [{"title": "Key Results", "rows": rows}] if rows else []
    descriptives = find_first_named_element(root, "desc")
    if descriptives is not None and descriptives.HasField("table"):
        desc_rows = []
        for row in table_rows(descriptives.table):
            desc_rows.append(
                {
                    "Variable": row.get("dep") or "",
                    "Group 1": row.get("group[1]") or "",
                    "N 1": format_number(row.get("num[1]")),
                    "Mean 1": format_number(row.get("mean[1]")),
                    "SD 1": format_number(row.get("sd[1]")),
                    "Group 2": row.get("group[2]") or "",
                    "N 2": format_number(row.get("num[2]")),
                    "Mean 2": format_number(row.get("mean[2]")),
                    "SD 2": format_number(row.get("sd[2]")),
                }
            )
        if desc_rows:
            sections.append({"title": "Group Descriptives", "rows": desc_rows})
    return sections


def build_anova_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "anova")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    for row in table_rows(element.table):
        for suffix, label in (("welch", "Welch"), ("fisher", "Fisher")):
            if row.get(f"p[{suffix}]") is None and row.get(f"F[{suffix}]") is None:
                continue
            rows.append(
                {
                    "Dependent Variable": row.get("dep") or "",
                    "Test": label,
                    "F": format_number(row.get(f"F[{suffix}]")),
                    "df1": format_number(row.get(f"df1[{suffix}]")),
                    "df2": format_number(row.get(f"df2[{suffix}]")),
                    "p": format_p_value(row.get(f"p[{suffix}]")),
                }
            )
    sections = [{"title": "Key Results", "rows": rows}] if rows else []

    descriptives = find_first_named_element(root, "desc")
    if descriptives is not None and descriptives.HasField("table"):
        desc_rows = []
        for row in table_rows(descriptives.table):
            desc_rows.append(
                {
                    "Dependent Variable": row.get("dep") or "",
                    "Group": row.get("group") or "",
                    "N": format_number(row.get("num")),
                    "Mean": format_number(row.get("mean")),
                    "SD": format_number(row.get("sd")),
                    "SE": format_number(row.get("se")),
                }
            )
        if desc_rows:
            sections.append({"title": "Group Descriptives", "rows": desc_rows})
    return sections


def build_corr_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "matrix")
    if element is None or not element.HasField("table"):
        return []

    rows = table_rows(element.table)
    pair_rows: list[dict[str, Any]] = []
    for row in rows:
        target = row.get(".name[r]")
        if not target:
            continue
        for key, value in row.items():
            match = re.match(r"(.+)\[r\]$", key)
            if not match:
                continue
            other = match.group(1)
            if other.startswith(".") or value is None:
                continue
            pair_rows.append(
                {
                    "Variable 1": other,
                    "Variable 2": target,
                    "r": format_number(value),
                    "df": format_number(row.get(f"{other}[rdf]")),
                    "p": format_p_value(row.get(f"{other}[rp]")),
                    "N": format_number(row.get(f"{other}[n]")),
                }
            )
    return [{"title": "Key Results", "rows": pair_rows[:12]}] if pair_rows else []


def build_linreg_sections(root: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    model_fit = find_first_named_element(root, "modelFit")
    if model_fit is not None and model_fit.HasField("table"):
        fit_rows = []
        for row in table_rows(model_fit.table):
            fit_rows.append(
                {
                    "Model": format_number(row.get("model")),
                    "R": format_number(row.get("r")),
                    "R2": format_number(row.get("r2")),
                    "Adjusted R2": format_number(row.get("r2Adj")),
                    "F": format_number(row.get("f")),
                    "df1": format_number(row.get("df1")),
                    "df2": format_number(row.get("df2")),
                    "p": format_p_value(row.get("p")),
                }
            )
        if fit_rows:
            sections.append({"title": "Model Fit", "rows": fit_rows})

    coefficient_tables = find_all_named_elements(root, "coef")
    coefficient_rows: list[dict[str, Any]] = []
    for table_element in coefficient_tables:
        if not table_element.HasField("table"):
            continue
        for row in table_rows(table_element.table):
            coefficient_rows.append(
                {
                    "Term": row.get("term") or "",
                    "Estimate": format_number(row.get("est")),
                    "SE": format_number(row.get("se")),
                    "Lower": format_number(row.get("lower")),
                    "Upper": format_number(row.get("upper")),
                    "t": format_number(row.get("t")),
                    "p": format_p_value(row.get("p")),
                }
            )
    if coefficient_rows:
        sections.append({"title": "Coefficients", "rows": coefficient_rows[:12]})
    return sections


def build_logreg_sections(root: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    model_fit = find_first_named_element(root, "modelFit")
    if model_fit is not None and model_fit.HasField("table"):
        fit_rows = []
        for row in table_rows(model_fit.table):
            fit_rows.append(
                {
                    "Model": format_number(row.get("model")),
                    "Deviance": format_number(row.get("dev")),
                    "AIC": format_number(row.get("aic")),
                    "McFadden R2": format_number(row.get("r2mf")),
                    "Chi Square": format_number(row.get("chi")),
                    "df": format_number(row.get("df")),
                    "p": format_p_value(row.get("p")),
                }
            )
        if fit_rows:
            sections.append({"title": "Model Fit", "rows": fit_rows})

    coefficient_tables = find_all_named_elements(root, "coef")
    coefficient_rows: list[dict[str, Any]] = []
    for table_element in coefficient_tables:
        if not table_element.HasField("table"):
            continue
        for row in table_rows(table_element.table):
            coefficient_rows.append(
                {
                    "Term": row.get("term") or "",
                    "Estimate": format_number(row.get("est")),
                    "SE": format_number(row.get("se")),
                    "Lower": format_number(row.get("lower")),
                    "Upper": format_number(row.get("upper")),
                    "z": format_number(row.get("z")),
                    "p": format_p_value(row.get("p")),
                    "OR": format_number(row.get("odds")),
                    "OR Lower": format_number(row.get("oddsLower")),
                    "OR Upper": format_number(row.get("oddsUpper")),
                }
            )
    if coefficient_rows:
        sections.append({"title": "Coefficients", "rows": coefficient_rows[:12]})
    return sections


def build_cont_tables_sections(root: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    chi_sq = find_first_named_element(root, "chiSq")
    if chi_sq is not None and chi_sq.HasField("table"):
        rows = []
        for row in table_rows(chi_sq.table):
            rows.append(
                {
                    "Test": row.get("test[chiSq]") or "Chi Square",
                    "Value": format_number(row.get("value[chiSq]")),
                    "df": format_number(row.get("df[chiSq]")),
                    "p": format_p_value(row.get("p[chiSq]")),
                    "N": format_number(row.get("value[N]")),
                }
            )
        if rows:
            sections.append({"title": "Chi Square Tests", "rows": rows})

    nominal = find_first_named_element(root, "nom")
    if nominal is not None and nominal.HasField("table"):
        rows = []
        for row in table_rows(nominal.table):
            rows.append(
                {
                    "Contingency Coefficient": format_number(row.get("v[cont]")),
                    "Phi": format_number(row.get("v[phi]")),
                    "Cramers V": format_number(row.get("v[cra]")),
                }
            )
        if rows:
            sections.append({"title": "Nominal Measures", "rows": rows})
    return sections


def build_reliability_sections(root: Any) -> list[dict[str, Any]]:
    element = find_first_named_element(root, "scale")
    if element is None or not element.HasField("table"):
        return []

    rows = []
    for row in table_rows(element.table):
        rows.append(
            {
                "Scale": row.get("name") or "",
                "Mean": format_number(row.get("mean")),
                "SD": format_number(row.get("sd")),
                "Cronbach Alpha": format_number(row.get("alpha")),
                "McDonalds Omega": format_number(row.get("omega")),
            }
        )
    return [{"title": "Scale Reliability", "rows": rows}]


SUMMARY_BUILDERS = {
    "anovaOneW": build_anova_sections,
    "contTables": build_cont_tables_sections,
    "corrMatrix": build_corr_sections,
    "descriptives": build_descriptives_sections,
    "linReg": build_linreg_sections,
    "logRegBin": build_logreg_sections,
    "reliability": build_reliability_sections,
    "ttestIS": build_ttest_sections,
}


def build_summary_sections(analysis_type: str, root: Any) -> list[dict[str, Any]]:
    builder = SUMMARY_BUILDERS.get(analysis_type)
    if builder is None:
        return []
    return builder(root)


def normalize_output_stem(raw_value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_value.strip())
    cleaned = cleaned.strip("-.")
    return cleaned or "jamovi-project"


def resolve_output_paths(
    data_path: Path,
    output_dir: str | None,
    output_basename: str | None,
    spec_output_basename: str | None,
) -> tuple[Path, Path]:
    destination = Path(output_dir) if output_dir else data_path.parent
    destination.mkdir(parents=True, exist_ok=True)
    stem_source = output_basename or spec_output_basename or f"{data_path.stem}-jamovi-project"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = normalize_output_stem(stem_source)
    return destination / f"{stem}-{timestamp}.omv", destination / f"{stem}-{timestamp}.md"


def build_markdown_report(
    data_path: Path,
    omv_path: Path | None,
    parse_contract: dict[str, Any] | None,
    records: Sequence[AnalysisResultRecord],
    teardown_errors: Sequence[str],
    mode: str,
) -> str:
    lines = [
        "# Jamovi Project Summary",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Mode: {mode}",
        f"- Data file: `{data_path}`",
        f"- OMV path: `{omv_path}`" if omv_path else "- OMV path: not saved",
        "",
    ]

    if parse_contract is not None:
        lines.extend(
            [
                "## Parse Contract",
                "",
                f"- is_executable: `{parse_contract['is_executable']}`",
                f"- missing_info: {parse_contract['missing_info'] or 'n/a'}",
                "",
            ]
        )

    successful = [record for record in records if record.status == "success"]
    failed = [record for record in records if record.status != "success"]

    lines.extend(["## Successful Analyses", ""])
    if not successful:
        lines.append("No analyses completed successfully.")
        lines.append("")
    else:
        for index, record in enumerate(successful, start=1):
            lines.append(f"### {index}. {record.title} (`{record.analysis_type}`)")
            lines.append("")
            lines.append(f"- Variables: {format_variables_for_markdown(record.variables)}")
            lines.append(f"- Status: {record.status_detail}")
            if record.note:
                lines.append(f"- Note: {record.note}")
            lines.append("")
            if record.summary_sections:
                for section in record.summary_sections:
                    lines.append(f"#### {section['title']}")
                    lines.extend(markdown_table(section["rows"]))
                    lines.append("")
            else:
                lines.append("Key results could not be extracted automatically. Open the `.omv` file for the full result tree.")
                lines.append("")

    lines.extend(["## Failed Analyses", ""])
    if not failed:
        lines.append("No analysis failures were recorded.")
        lines.append("")
    else:
        failure_rows = [
            {"Analysis": record.analysis_type, "Failure Type": record.status, "Reason": record.status_detail}
            for record in failed
        ]
        lines.extend(markdown_table(failure_rows))
        lines.append("")

    lines.extend(["## Teardown", ""])
    if teardown_errors:
        for issue in teardown_errors:
            lines.append(f"- {issue}")
    else:
        lines.append("- No teardown issues recorded.")
    lines.append("")
    return "\n".join(lines)


async def execute_analyses(
    session: Session,
    instance: Any,
    spec: dict[str, Any],
    analysis_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[AnalysisResultRecord]:
    records: list[AnalysisResultRecord] = []
    global_measure_overrides = spec.get("measure_overrides", {})

    for analysis_spec in spec["analyses"]:
        analysis_type = analysis_spec["analysis_type"]
        title = SUPPORTED_ANALYSES[analysis_type]["title"]
        column_map = build_column_map(instance._data)

        try:
            normalized_variables, payload = prepare_analysis_payload(analysis_spec, column_map, global_measure_overrides)
            module = instance._data.analyses._modules[analysis_spec["namespace"]]
            meta = module.get(analysis_type)
            valid_option_names = {option["name"] for option in meta.defn["options"]}
            unknown_keys = sorted(set(payload) - valid_option_names)
            if unknown_keys:
                raise ValidationError(f"Unknown option(s) for {analysis_type}: {', '.join(unknown_keys)}")

            options = Options.create(meta.defn["options"])
            for key, value in payload.items():
                options.set_value(key, value)

            analysis = instance._data.analyses.create(0, analysis_type, analysis_spec["namespace"], options.as_pb())
            analysis.run()
            state, detail = await poll_analysis(
                analysis,
                session,
                timeout_seconds=analysis_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )

            if state == "complete":
                root = analysis.results.results
                summary_sections = build_summary_sections(analysis_type, root)
                note = None
                if not summary_sections:
                    note = "Key results were not extracted automatically; inspect the .omv file for the full output."
                records.append(
                    AnalysisResultRecord(
                        analysis_type=analysis_type,
                        title=getattr(root, "title", title) or title,
                        variables=normalized_variables,
                        options={key: value for key, value in payload.items() if key not in normalized_variables},
                        status="success",
                        status_detail="Completed",
                        summary_sections=summary_sections,
                        note=note,
                    )
                )
            else:
                records.append(
                    AnalysisResultRecord(
                        analysis_type=analysis_type,
                        title=title,
                        variables=normalized_variables,
                        options={key: value for key, value in payload.items() if key not in normalized_variables},
                        status=state,
                        status_detail=detail,
                    )
                )
        except Exception as exc:
            records.append(
                AnalysisResultRecord(
                    analysis_type=analysis_type,
                    title=title,
                    variables=ensure_mapping(analysis_spec.get("variables"), "variables"),
                    options=ensure_mapping(analysis_spec.get("options"), "options"),
                    status="preflight_error",
                    status_detail=str(exc),
                )
            )

    return records


async def run_project_mode(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    data_path = Path(args.data_path).expanduser().resolve()
    if not data_path.exists():
        raise RunnerError(f"Data file not found: {data_path}")

    if bool(args.request) and bool(args.request_file):
        raise RunnerError("Provide either --request or --request-file, not both.")

    mode = "structured"
    parse_contract = None
    request_text = None
    if args.request_file:
        request_text = Path(args.request_file).read_text(encoding="utf-8-sig")
    elif args.request:
        request_text = args.request

    if request_text is not None:
        mode = "natural-language"
        header_columns = read_dataset_headers(data_path)
        parse_contract = parse_nl_request(request_text, header_columns)
        if not parse_contract["is_executable"]:
            return (
                {
                    "status": "parse_error",
                    "mode": mode,
                    "parse": parse_contract,
                    "omv_path": None,
                    "markdown_path": None,
                },
                2,
            )
        spec = parse_contract["analysis_spec"]
    else:
        spec = parse_inline_or_file_spec(args)

    assert spec is not None

    omv_path, markdown_path = resolve_output_paths(
        data_path=data_path,
        output_dir=args.output_dir,
        output_basename=args.output_basename,
        spec_output_basename=spec.get("output_basename"),
    )

    session = Session(data_path=str(omv_path.parent), id="codex-project-mode")
    session._settings._backend._flush_rate = 0
    instance = None
    records: list[AnalysisResultRecord] = []
    teardown_errors: list[str] = []
    save_error: str | None = None

    try:
        await session.start()
        instance = await session.create("codex-project-instance")
        await drain_progress_stream(instance.open(str(data_path)))
        records = await execute_analyses(
            session,
            instance,
            spec,
            analysis_timeout_seconds=args.analysis_timeout_seconds,
            poll_interval_seconds=max(args.poll_interval_ms / 1000.0, 0.05),
        )
        try:
            await drain_progress_stream(instance.save({"path": str(omv_path), "overwrite": True}))
        except Exception as exc:
            save_error = str(exc)
    finally:
        try:
            await session._runner.stop()
        except Exception as exc:
            teardown_errors.append(f"runner.stop failed: {exc}")
        if instance is not None:
            try:
                instance.close()
            except Exception as exc:
                teardown_errors.append(f"instance.close failed: {exc}")
        try:
            session.stop()
        except Exception as exc:
            teardown_errors.append(f"session.stop failed: {exc}")
        try:
            await session.wait_ended()
        except Exception as exc:
            teardown_errors.append(f"session.wait_ended failed: {exc}")

    if save_error:
        records.append(
            AnalysisResultRecord(
                analysis_type="save",
                title="Project Save",
                variables={},
                options={},
                status="save_error",
                status_detail=save_error,
            )
        )

    markdown_text = build_markdown_report(
        data_path=data_path,
        omv_path=omv_path if omv_path.exists() else None,
        parse_contract=parse_contract,
        records=records,
        teardown_errors=teardown_errors,
        mode=mode,
    )
    markdown_path.write_text(markdown_text, encoding="utf-8")

    success_count = sum(1 for record in records if record.status == "success")
    failure_count = sum(1 for record in records if record.status != "success")
    overall_status = "success"
    exit_code = 0
    if success_count and failure_count:
        overall_status = "partial"
    elif not success_count and failure_count:
        overall_status = "failed"
        exit_code = 1

    result = {
        "status": overall_status,
        "mode": mode,
        "parse": parse_contract,
        "omv_path": str(omv_path) if omv_path.exists() else None,
        "markdown_path": str(markdown_path),
        "success_count": success_count,
        "failure_count": failure_count,
        "analyses": [
            {
                "analysis_type": record.analysis_type,
                "title": record.title,
                "status": record.status,
                "status_detail": record.status_detail,
            }
            for record in records
        ],
        "teardown_errors": teardown_errors,
    }
    return result, exit_code


async def async_main(args: argparse.Namespace) -> int:
    result, exit_code = await run_project_mode(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return exit_code


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(async_main(args))
    except Exception as exc:
        failure = {
            "status": "failed",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(failure, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
