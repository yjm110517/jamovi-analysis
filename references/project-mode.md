# Project Mode

Project mode creates a real jamovi project by driving jamovi internals through:

- `Session.start()`
- `Session.create()`
- `Instance.open()`
- `instance._data.analyses.create(...)`
- `Instance.save(...)`

The PowerShell entrypoint is [scripts/invoke-jamovi-project.ps1](../scripts/invoke-jamovi-project.ps1).

## Runtime Isolation

- Project mode must run with jamovi's bundled interpreter:
  - `C:\Program Files\jamovi 2.6.19.0\Frameworks\python\python.exe`
- Do not run the Python runner with system Python.
- The wrapper removes:
  - `PYTHONHOME`
  - `PYTHONPATH`
  - `VIRTUAL_ENV`
  - all inherited `CONDA_*`

## Outputs

Each run writes:

- `*.omv`
- same-stem `*.md`
- same-stem `*.docx` (APA template + python-docx)
- same-stem `*.html` (Markdown export when enabled)
- same-stem `*.pdf` (Markdown export when enabled and weasyprint is available)
- same-stem `*.zip` (LaTeX bundle export when enabled)

File names are timestamped and do not overwrite previous runs.

## Unified JobFile Schema (Canonical)

The modern entry point is to construct a single JSON configuration file (a `JobFile`) and pass it to `-JobFile`. The `JobFile` handles data source, preprocessing, and analysis configurations via a unified contract.

```json
{
  "data_path": "C:/data/raw_survey.xlsx",
  "mode": "project",
  "sheet": "Sheet1",
  "request_kind": "structured",
  "analyses": [
    {
      "analysis_type": "ttestIS",
      "variables": {
        "vars": ["score"],
        "group": "group"
      }
    }
  ],
  "output": {
    "dir": "C:/data/jamovi_outputs",
    "basename": "study-report",
    "table_style": "gfm",
    "export": {
      "enabled": true,
      "formats": ["pdf", "html", "latex"]
    }
  }
}
```

Output options:
- `output.table_style`: `gfm` (default) or `apa`.
- `output.export`: `{ enabled: true, formats: ["pdf", "html", "latex"] }`.
  If omitted, project mode enables only the default formats supported by the current environment. For example, `pdf` is removed when `weasyprint` is unavailable.

## Preflight

Use [scripts/preflight-jamovi-project.ps1](../scripts/preflight-jamovi-project.ps1) to check optional report dependencies before running a full analysis.

The preflight reports:
- `python-docx` availability for DOCX output
- `markdown` availability for rich HTML/LaTeX rendering
- `weasyprint` availability for PDF output
- the effective default export formats after capability filtering

Project mode does not perform runtime `pip install`. Optional dependencies should come from jamovi's bundled environment or the repo-scoped vendor directory at `vendor/jamovi-python`.

### High-level Preset

For standard educational/psychology surveys, use `request_kind: "preset"`. The system will automatically compute reverse items, domain totals, and expand into the preset's implemented analyses.

```json
{
  "data_path": "C:/data/raw_survey.xlsx",
  "mode": "project",
  "request_kind": "preset",
  "preset": {
    "name": "prepost_scale_study",
    "id_column": "user_id",
    "group_column": "class_group",
    "cluster_column": "cluster",
    "pre_prefix": "pre_",
    "post_prefix": "post_",
    "max_scale": 5,
    "reverse_items": ["q24", "q25"],
    "subscales": {
      "creativity": ["q01", "q02"]
    }
  },
  "output": {
    "dir": "C:/data/jamovi_outputs",
    "basename": "ct-core-analysis"
  }
}
```

The runner automatically generates an `analysis_ready.csv` file, normalizing column names into pure ASCII aliases to ensure Jamovi runs without Mojibake errors. If `output.dir` is provided, the sidecar files are written there; otherwise a temporary directory is used and reported in the Markdown summary.

## Legacy Structured Spec

The legacy interface passing `-DataPath` directly and using `-SpecJson` allows either a single analysis object:

```json
{
  "analysis_type": "ttestIS",
  "variables": {
    "vars": ["score"],
    "group": "group"
  },
  "options": {
    "welchs": true,
    "effectSize": true
  }
}
```

Or a top-level batch object:

```json
{
  "output_basename": "study-report",
  "measure_overrides": {
    "group": "nominal",
    "score": "continuous"
  },
  "analyses": [
    {
      "analysis_type": "descriptives",
      "variables": {
        "vars": ["score", "age"]
      }
    },
    {
      "analysis_type": "ttestIS",
      "variables": {
        "vars": ["score"],
        "group": "group"
      }
    }
  ]
}
```

## NL Contract

NL mode uses a strict parser contract:

```json
{
  "is_executable": true,
  "missing_info": "",
  "analysis_spec": {
    "analysis_type": "corrMatrix",
    "variables": {
      "vars": ["score", "age"]
    }
  }
}
```

If the request is ambiguous or underspecified:

```json
{
  "is_executable": false,
  "missing_info": "Mention at least two exact column names for a correlation analysis.",
  "analysis_spec": null
}
```

The runner strips Markdown fences before parsing JSON so inputs like ````json ... ```` do not fail spuriously.

## Supported Analyses

v1 supports:

- `descriptives`
- `ttestIS`
- `ttestPS`
- `anovaOneW`
- `corrMatrix`
- `linReg`
- `logRegBin`
- `contTables`
- `reliability`

v1 does not cover PCA, EFA, or CFA.

## Measurement Rules

- `ttestIS`
  - `vars`: continuous
  - `group`: nominal or ordinal, exactly 2 levels
- `ttestPS`
  - `pairs`: list of dictionaries `{"i1": continuous, "i2": continuous}`
- `anovaOneW`
  - `deps`: continuous
  - `group`: nominal or ordinal
- `corrMatrix`
  - `vars`: continuous
- `linReg`
  - `dep`: continuous
  - `covs`: continuous
  - `factors`: nominal or ordinal
- `logRegBin`
  - `dep`: nominal or ordinal, exactly 2 levels
  - `covs`: continuous
  - `factors`: nominal or ordinal
- `contTables`
  - `rows`, `cols`, `layers`: nominal or ordinal
  - `counts`: continuous when provided
- `reliability`
  - `vars`: continuous or ordinal

When safe, the runner corrects `measure_type` before analysis creation. If the conversion is unsafe, the analysis fails before `analyses.create(...)`.

## Lifecycle

Project mode uses a single event loop:

1. `asyncio.run(main())`
2. `await session.start()`
3. `instance = await session.create(...)`
4. `await instance.open(...)`
5. create and poll analyses serially
6. `await instance.save(...)`
7. teardown:
   - `await session._runner.stop()`
   - `instance.close()`
   - `session.stop()`
   - `await session.wait_ended()`

The explicit `session._runner.stop()` call is important in practice to reduce engine-thread shutdown noise on Windows.

## Timeout Handling

- Analyses are polled serially.
- Each analysis has its own timeout.
- On timeout, the runner:
  - marks the analysis failed
  - records the timeout in Markdown
  - attempts `session.restart_engines()`
  - continues to the next analysis

## Markdown Summary

The Markdown output is meant to be a dehydrated report, not only a pass/fail log.

Current extraction covers:

- descriptives
- independent samples t-test
- paired samples t-test
- one-way ANOVA
- correlation matrix
- linear regression
- binomial logistic regression
- contingency tables
- reliability

If key statistics cannot be extracted automatically, the Markdown explicitly says to inspect the `.omv` file.

## Validation

Use `zipfile` to validate `.omv` output without jamovi GUI:

```python
from zipfile import ZipFile

with ZipFile("report.omv") as archive:
    names = archive.namelist()
    assert "metadata.json" in names
    assert any(name.endswith("/analysis") for name in names)
```
