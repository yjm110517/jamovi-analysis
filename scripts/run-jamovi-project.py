from __future__ import annotations

import argparse
import asyncio
import csv
import html
import importlib
import json
import os
import re
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_JAMOVI_HOME = Path(os.environ.get("JAMOVI_HOME", r"C:\Program Files\jamovi 2.6.19.0"))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVER_ROOT = DEFAULT_JAMOVI_HOME / "Resources" / "server"
DEFAULT_VENDOR_ROOT = PROJECT_ROOT / "vendor" / "jamovi-python"

if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


def configure_vendor_paths() -> list[str]:
    raw_value = os.environ.get("JAMOVI_PROJECT_VENDOR_PATH")
    candidates: list[str] = []
    if raw_value:
        candidates.extend(entry.strip() for entry in raw_value.split(os.pathsep) if entry.strip())
    elif DEFAULT_VENDOR_ROOT.exists():
        candidates.append(str(DEFAULT_VENDOR_ROOT))

    configured: list[str] = []
    for entry in candidates:
        resolved = str(Path(entry).resolve())
        if not Path(resolved).exists():
            continue
        if resolved not in sys.path:
            sys.path.insert(0, resolved)
        configured.append(resolved)
    return configured


VENDOR_PATHS = configure_vendor_paths()

# Allow importing the refactored jamovi_runner package
SRC_ROOT = str(PROJECT_ROOT / "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

if os.environ.get("JAMOVI_PROJECT_RUNNER") != "1":
    raise SystemExit("run-jamovi-project.py must be launched via invoke-jamovi-project.ps1")

from jamovi.core import DataType, MeasureType  # noqa: E402
from jamovi.server.analyses.analysis import Analysis  # noqa: E402
from jamovi.server.options import Options  # noqa: E402
from jamovi.server.session import Session  # noqa: E402

from jamovi_runner.extract import build_summary_sections  # noqa: E402
from jamovi_runner.formatting import format_number, format_p_value, markdown_table, render_markdown_table_block  # noqa: E402
from jamovi_runner.preprocess import preprocess_data, PreprocessError  # noqa: E402
from jamovi_runner.report import build_markdown_report as _build_markdown_report_from_package  # noqa: E402
from jamovi_runner.reporters import (
    build_docx_report,
    build_runner_markdown_report,
    export_report_formats,
    render_markdown_html,
    resolve_output_paths,
)  # noqa: E402


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
    "ttestPS": {
        "title": "Paired Samples T-Test",
        "namespace": "jmv",
        "roles": {
            "pairs": RoleSpec("variables", measure="continuous", required=True, min_items=2),
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
    "ttestPS": {"students": True, "effectSize": True, "ci": True, "desc": True},
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
DEFAULT_TABLE_STYLE = "gfm"
DEFAULT_EXPORT_FORMATS = ("pdf", "html", "latex")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run jamovi project-mode analyses and save .omv output.")
    parser.add_argument("--data-path")
    parser.add_argument("--job-file")
    parser.add_argument("--spec-json")
    parser.add_argument("--spec-file")
    parser.add_argument("--request")
    parser.add_argument("--request-file")
    parser.add_argument("--output-dir")
    parser.add_argument("--output-basename")
    parser.add_argument("--analysis-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--poll-interval-ms", type=int, default=250)
    parser.add_argument("--preflight", action="store_true")
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


def normalize_table_style(raw_value: Any) -> str:
    if raw_value is None:
        return DEFAULT_TABLE_STYLE
    if not isinstance(raw_value, str):
        raise SpecError("output.table_style must be a string")
    normalized = raw_value.strip().casefold()
    if normalized not in {"gfm", "apa"}:
        raise SpecError("output.table_style must be 'gfm' or 'apa'")
    return normalized


def normalize_export_config(raw_value: Any) -> tuple[bool, list[str]]:
    if raw_value is None:
        return True, list(DEFAULT_EXPORT_FORMATS)
    if not isinstance(raw_value, dict):
        raise SpecError("output.export must be an object")
    enabled = bool(raw_value.get("enabled", True))
    raw_formats = raw_value.get("formats", list(DEFAULT_EXPORT_FORMATS))
    if isinstance(raw_formats, str):
        formats = [raw_formats]
    elif isinstance(raw_formats, list):
        formats = raw_formats
    else:
        raise SpecError("output.export.formats must be a string or array of strings")
    normalized: list[str] = []
    for entry in formats:
        if not isinstance(entry, str):
            raise SpecError("output.export.formats must contain only strings")
        value = entry.strip().casefold()
        if value == "htm":
            value = "html"
        if value not in {"pdf", "html", "latex"}:
            raise SpecError("output.export.formats entries must be pdf, html, or latex")
        if value not in normalized:
            normalized.append(value)
    return enabled, normalized


def probe_optional_dependency(import_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(import_name)
    except Exception as exc:
        return {
            "available": False,
            "import_name": import_name,
            "source": None,
            "detail": str(exc),
        }

    module_path = getattr(module, "__file__", None)
    source = "bundled"
    if module_path:
        resolved = str(Path(module_path).resolve())
        if any(resolved.startswith(path) for path in VENDOR_PATHS):
            source = "vendor"
    return {
        "available": True,
        "import_name": import_name,
        "source": source,
        "detail": None,
    }


def detect_optional_dependencies() -> dict[str, dict[str, Any]]:
    return {
        "python_docx": probe_optional_dependency("docx"),
        "markdown": probe_optional_dependency("markdown"),
        "weasyprint": probe_optional_dependency("weasyprint"),
    }


def compute_output_capabilities(dependencies: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    template_path = PROJECT_ROOT / "assets" / "apa-template.docx"
    markdown_available = dependencies["markdown"]["available"]
    docx_available = dependencies["python_docx"]["available"] and template_path.exists()
    pdf_available = dependencies["weasyprint"]["available"]
    return {
        "omv": {"available": True},
        "markdown": {"available": True},
        "docx": {
            "available": docx_available,
            "renderer": "python-docx" if docx_available else None,
            "detail": None if docx_available else (
                f"Template missing: {template_path}" if not template_path.exists() else dependencies["python_docx"]["detail"]
            ),
        },
        "html": {
            "available": True,
            "renderer": "markdown" if markdown_available else "preformatted-fallback",
            "detail": None if markdown_available else dependencies["markdown"]["detail"],
        },
        "latex": {
            "available": True,
            "renderer": "markdown" if markdown_available else "preformatted-fallback",
            "detail": None if markdown_available else dependencies["markdown"]["detail"],
        },
        "pdf": {
            "available": pdf_available,
            "renderer": "weasyprint" if pdf_available else None,
            "detail": None if pdf_available else dependencies["weasyprint"]["detail"],
        },
    }


def resolve_default_export_formats(
    export_formats: Sequence[str],
    raw_export_config: Any,
    output_capabilities: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    if raw_export_config is not None:
        return list(export_formats), []

    effective: list[str] = []
    warnings: list[str] = []
    for fmt in export_formats:
        capability = output_capabilities.get(fmt, {"available": True})
        if capability.get("available", True):
            effective.append(fmt)
            continue
        warnings.append(
            f"Default export format '{fmt}' disabled by preflight: {capability.get('detail') or 'dependency unavailable'}"
        )
    return effective, warnings


def build_preflight_report() -> dict[str, Any]:
    dependencies = detect_optional_dependencies()
    output_capabilities = compute_output_capabilities(dependencies)
    default_export_formats, warnings = resolve_default_export_formats(
        DEFAULT_EXPORT_FORMATS,
        None,
        output_capabilities,
    )
    if not output_capabilities["docx"]["available"]:
        warnings.append(f"DOCX output unavailable: {output_capabilities['docx']['detail']}")
    if output_capabilities["html"]["renderer"] == "preformatted-fallback":
        warnings.append("HTML and LaTeX exports will use the plain preformatted fallback because markdown is unavailable.")
    return {
        "status": "ok",
        "jamovi_home": str(DEFAULT_JAMOVI_HOME),
        "project_root": str(PROJECT_ROOT),
        "vendor_paths": VENDOR_PATHS,
        "dependencies": dependencies,
        "outputs": output_capabilities,
        "default_export_formats": default_export_formats,
        "warnings": warnings,
    }


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

    if raw_spec.get("request_kind") == "preset" and "analyses" not in raw_spec:
        return raw_spec

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
    supported_text = {".csv", ".txt", ".tsv"}
    supported_excel = {".xlsx", ".xlsm"}
    if suffix in supported_text:
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

    if suffix in supported_excel:
        try:
            import openpyxl  # type: ignore
        except Exception:
            return []
        workbook = openpyxl.load_workbook(data_path, read_only=True, data_only=True)
        worksheet = workbook.active
        first_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        workbook.close()
        return [str(cell).strip() for cell in first_row if cell is not None and str(cell).strip()]
    raise RunnerError(
        f"Unsupported data file type '{suffix}'. Supported formats: {', '.join(sorted(supported_text | supported_excel))}."
    )


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


def normalize_variable_binding(value: Any, role: RoleSpec, role_name: str) -> str | list[str] | list[dict[str, str]] | None:
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

    if role_name == "pairs" and isinstance(value, list) and all(isinstance(item, dict) for item in value):
        normalized_pairs: list[dict[str, str]] = []
        for item in value:
            i1 = item.get("i1")
            i2 = item.get("i2")
            if not isinstance(i1, str) or not i1.strip() or not isinstance(i2, str) or not i2.strip():
                raise SpecError("variables.pairs entries must contain non-empty 'i1' and 'i2' column names")
            normalized_pairs.append({"i1": i1.strip(), "i2": i2.strip()})
        if role.required and not normalized_pairs:
            raise SpecError("variables.pairs requires at least one pair")
        return normalized_pairs

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
        if role_name == "pairs" and isinstance(normalized_value, list) and normalized_value and isinstance(normalized_value[0], dict):
            normalized_pairs: list[dict[str, str]] = []
            for pair in normalized_value:
                i1 = pair.get("i1")
                i2 = pair.get("i2")
                if i1 is None or i2 is None:
                    raise ValidationError("variables.pairs entries must contain i1 and i2.")
                if i1 not in column_map or i2 not in column_map:
                    missing = [name for name in (i1, i2) if name not in column_map]
                    raise ValidationError(f"Unknown column(s) for role 'pairs': {', '.join(missing)}")
                for name in (i1, i2):
                    column = column_map[name]
                    ensure_measure_requirements(column, role.measure)
                    ensure_level_count(column, role_name, role)
                normalized_pairs.append({"i1": i1, "i2": i2})
            if role.required and not normalized_pairs:
                raise ValidationError("variables.pairs requires at least one pair.")
            normalized_variables[role_name] = normalized_pairs
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
    import time
    start_time = time.time()
    phase_timings: dict[str, float] = {}

    job_spec = None
    output_config: dict[str, Any] = {}
    if args.job_file:
        job_file_path = Path(args.job_file).expanduser().resolve()
        job_spec = load_json_text(job_file_path.read_text(encoding="utf-8"), "--job-file")
        data_path = Path(job_spec["data_path"]).expanduser().resolve()

        # --- Wire JobFile.output -------------------------------------------------
        job_output = job_spec.get("output") or {}
        output_config = job_output
        if job_output.get("dir") and not args.output_dir:
            args.output_dir = job_output["dir"]
        if job_output.get("basename") and not args.output_basename:
            args.output_basename = job_output["basename"]

        # --- Locale for Chinese .omv labels -------------------------------------
        locale = job_spec.get("locale", "zh")
        os.environ["LANGUAGE"] = locale

        args.spec_json = json.dumps(job_spec)
    else:
        if not args.data_path:
            raise RunnerError("Data path is required if job-file is not provided.")
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
    if not output_config:
        output_config = spec.get("output") or {}
    table_style = normalize_table_style(output_config.get("table_style"))
    raw_export_config = output_config.get("export")
    export_enabled, export_formats = normalize_export_config(raw_export_config)
    dependency_status = detect_optional_dependencies()
    output_capabilities = compute_output_capabilities(dependency_status)
    export_formats, preflight_warnings = resolve_default_export_formats(
        export_formats,
        raw_export_config,
        output_capabilities,
    )

    # --- Preprocess phase ---------------------------------------------------
    column_manifest = None
    sidecar_info: dict[str, Any] | None = None
    t_pre = time.time()
    if job_spec or spec.get("request_kind") == "preset" or spec.get("request_kind") == "structured":
        try:
            data_path, column_manifest, spec_raw, sidecar_info = preprocess_data(
                data_path,
                job_spec or spec,
                args.output_dir,
            )
            spec = normalize_top_level_spec(spec_raw)
        except Exception as exc:
            raise RunnerError(f"Preprocess error: {exc}")
    phase_timings["preprocess_seconds"] = time.time() - t_pre

    omv_path, markdown_path, docx_path, output_base = resolve_output_paths(
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

        # --- Open phase -----------------------------------------------------
        t_open = time.time()
        await drain_progress_stream(instance.open(str(data_path)))
        phase_timings["open_seconds"] = time.time() - t_open

        # --- Run phase ------------------------------------------------------
        t_run = time.time()
        records = await execute_analyses(
            session,
            instance,
            spec,
            analysis_timeout_seconds=args.analysis_timeout_seconds,
            poll_interval_seconds=max(args.poll_interval_ms / 1000.0, 0.05),
        )
        phase_timings["run_seconds"] = time.time() - t_run

        # --- Save phase -----------------------------------------------------
        t_save = time.time()
        try:
            await drain_progress_stream(instance.save({"path": str(omv_path), "overwrite": True}))
        except Exception as exc:
            save_error = str(exc)
        phase_timings["save_seconds"] = time.time() - t_save
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

    phase_timings["total_seconds"] = time.time() - start_time
    markdown_text = build_runner_markdown_report(
        data_path=data_path,
        omv_path=omv_path if omv_path.exists() else None,
        parse_contract=parse_contract,
        records=records,
        teardown_errors=teardown_errors,
        mode=mode,
        column_manifest=column_manifest,
        timings=phase_timings,
        table_style=table_style,
        sidecar_info=sidecar_info,
    )
    try:
        markdown_path.write_text(markdown_text, encoding="utf-8")
    except Exception as exc:
        teardown_errors.append(f"Failed to write markdown: {exc}")

    output_warnings: list[str] = list(preflight_warnings)
    template_path = PROJECT_ROOT / "assets" / "apa-template.docx"
    docx_output, docx_warning = build_docx_report(
        template_path=template_path,
        output_path=docx_path,
        data_path=data_path,
        omv_path=omv_path if omv_path.exists() else None,
        records=records,
        mode=mode,
        table_style=table_style,
        column_manifest=column_manifest,
        timings=phase_timings,
    )
    if docx_warning:
        output_warnings.append(docx_warning)

    export_paths: dict[str, str | None] = {}
    export_warnings: list[str] = []
    if export_enabled:
        export_paths, export_warnings = await export_report_formats(
            markdown_text,
            output_base,
            export_formats,
        )
        output_warnings.extend(export_warnings)

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
        "timings": phase_timings,
        "mode": mode,
        "parse": parse_contract,
        "omv_path": str(omv_path) if omv_path.exists() else None,
        "markdown_path": str(markdown_path),
        "docx_path": str(docx_output) if docx_output else None,
        "success_count": success_count,
        "failure_count": failure_count,
        "output": {
            "table_style": table_style,
            "export": {
                "enabled": export_enabled,
                "formats": export_formats,
                "paths": export_paths,
                "warnings": export_warnings,
            },
        },
        "analyses": [
            {
                "analysis_type": record.analysis_type,
                "title": record.title,
                "status": record.status,
                "status_detail": record.status_detail,
                "options": record.options,
            }
            for record in records
        ],
        "output_warnings": output_warnings,
        "teardown_errors": teardown_errors,
    }
    return result, exit_code


async def async_main(args: argparse.Namespace) -> int:
    if args.preflight:
        print(json.dumps(build_preflight_report(), indent=2, ensure_ascii=False))
        return 0
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
