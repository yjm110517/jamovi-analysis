---
name: jamovi-analysis
description: Run jamovi-native statistical analyses with the local jamovi installation. Use when the user asks to analyze data with jamovi or jmv, wants jamovi-compatible descriptives, t-tests, ANOVA, regression, correlation, contingency tables, reliability workflows, or needs a real `.omv` project saved through jamovi internals.
---

# Jamovi Analysis

Use the mode that matches the requested output:

- Use project mode when the user wants a real jamovi project file, wants to preserve analyses in `.omv`, or wants a reusable Markdown summary with key statistics.
- Use bundled R + `jmv` when the task only needs quick batch output in the terminal.
- Use `jamovi.server` only when a live jamovi session or browser-backed behavior is explicitly needed.

## Quick Start

1. Confirm the jamovi install root. In this environment, default to `C:\Program Files\jamovi 2.6.19.0`.
2. For `.omv` output, use [scripts/invoke-jamovi-project.ps1](scripts/invoke-jamovi-project.ps1).
3. For quick batch statistics, use [scripts/invoke-jamovi-r.ps1](scripts/invoke-jamovi-r.ps1).
4. For interactive jamovi behavior, use [scripts/start-jamovi-server.ps1](scripts/start-jamovi-server.ps1).
5. For project-mode schema, supported analyses, and measurement rules, read [references/project-mode.md](references/project-mode.md).

## Preferred Workflow

### Project mode

- This is the default path when the user asks for a jamovi project or `.omv` file.
- The wrapper hard-pins jamovi's bundled interpreter: `C:\Program Files\jamovi 2.6.19.0\Frameworks\python\python.exe`.
- It explicitly clears `PYTHONHOME`, `PYTHONPATH`, `VIRTUAL_ENV`, and inherited `CONDA_*` variables before launching the Python runner.
- The runner uses jamovi internals (`Session -> Instance -> Analyses -> save()`) and writes:
  - a timestamped `.omv`
  - a same-stem `.md` summary
- v1 is intentionally conservative:
  - single event loop via `asyncio.run()`
  - strictly serial analysis execution
  - per-analysis polling with timeout
  - explicit teardown
  - fail-fast NL parsing
  - no parallel analysis dispatch

### Bundled R batch mode

- Use jamovi's bundled `Frameworks\R\bin\x64\Rscript.exe`.
- Let the wrapper add `.libPaths()` for `Resources\modules\jmv\R` and `Resources\modules\base\R`.
- Load `library(jmv)` and call exported functions such as `descriptives()`, `ttestIS()`, `anovaOneW()`, `linReg()`, or `corrMatrix()`.
- Use this mode when the user only needs immediate results, not a persisted jamovi project.

### Interactive jamovi session

- Use the server wrapper only when the user needs a real jamovi session, browser-backed behavior, or GUI-like interaction.
- Keep the server in the foreground unless there is a clear reason to background it.
- Record the `ports:` line and the `access_key` value when the server starts.

## Wrapper Scripts

### `scripts/invoke-jamovi-project.ps1`

- This is the only supported entrypoint for project mode.
- It must launch the runner with jamovi's bundled Python, never with system Python.
- It accepts:
  - structured mode: `-DataPath` plus `-SpecJson` or `-SpecFile`
  - NL mode: `-DataPath` plus `-Request`
  - optional: `-OutputDir`, `-OutputBasename`, `-AnalysisTimeoutSeconds`, `-PollIntervalMs`

Structured example:

```powershell
& 'C:\Users\WINDOWS\.codex\skills\jamovi-analysis\scripts\invoke-jamovi-project.ps1' `
  -DataPath 'C:\data\study.csv' `
  -SpecJson '{"analyses":[{"analysis_type":"ttestIS","variables":{"vars":["score"],"group":"group"}}]}'
```

Natural-language example:

```powershell
& 'C:\Users\WINDOWS\.codex\skills\jamovi-analysis\scripts\invoke-jamovi-project.ps1' `
  -DataPath 'C:\data\study.csv' `
  -Request 'Run descriptives for score and age'
```

### `scripts/invoke-jamovi-r.ps1`

- Use `-Code` for short inline R.
- Use `-File` when the R code is long or reusable.
- Pass `-JamoviHome` only when the install is not `C:\Program Files\jamovi 2.6.19.0`.

### `scripts/start-jamovi-server.ps1`

- Use to start `python -m jamovi.server` with the environment variables jamovi expects.
- Default to port `0` so jamovi chooses a free port.
- Add `-ExposeAllInterfaces` only when a remote connection is explicitly required.

## Project Mode Rules

- The runner must be launched only through the PowerShell wrapper.
- The runner uses a single event loop and explicit teardown to reduce zombie R processes and engine cleanup issues on Windows.
- If an analysis times out, it is marked failed, recorded in Markdown, and the runner attempts engine restart before continuing.
- If a column's measure type is wrong for the requested analysis, the runner corrects it before creating the analysis when that correction is safe.
- If a safe correction is not possible, the analysis fails fast before `analyses.create(...)`.

## Supported Project-Mode Analyses

v1 project mode currently implements these high-frequency analyses:

- `descriptives`
- `ttestIS`
- `anovaOneW`
- `corrMatrix`
- `linReg`
- `logRegBin`
- `contTables`
- `reliability`

Project mode v1 does not implement PCA, EFA, or CFA.

## Natural-Language Mode

- NL mode is deterministic and fail-fast.
- The parser returns a strict JSON contract:
  - `is_executable`
  - `missing_info`
  - `analysis_spec`
- If the request is missing roles or remains ambiguous, the runner returns a parse error instead of guessing.
- The runner strips Markdown fences such as ````json ... ````
  before attempting `json.loads()`.
- NL mode is deliberately narrow. Use exact column names and explicit phrasing such as:
  - `Run descriptives for score and age`
  - `Run a correlation for score and age`
  - `Run an independent samples t-test for score by group`
  - `Run one-way ANOVA for score by condition`
  - `Predict outcome from age and score`

## Reporting Rules

- State the analysis name and variables used.
- State non-default options that materially affect interpretation.
- For project mode, prefer the Markdown summary when the user wants a dehydrated report.
- The Markdown summary should include key statistics when extractable:
  - t-tests: statistic, df, p, effect size
  - one-way ANOVA: F, df1, df2, p
  - correlations: r, p, N
  - linear regression: R2 and coefficient table
  - logistic regression: model fit and coefficient table with odds ratios
  - contingency tables: chi-square, df, p, nominal measures
  - reliability: Cronbach alpha and omega
  - descriptives: N, mean, median, SD, min, max

## References

- Read [references/install-layout.md](references/install-layout.md) for verified local jamovi paths.
- Read [references/analysis-map.md](references/analysis-map.md) for common `jmv` function mappings and project-mode scope.
- Read [references/project-mode.md](references/project-mode.md) for the structured spec schema, measurement rules, lifecycle, and validation expectations.

## Validation

- After editing project mode, run a real smoke test through `invoke-jamovi-project.ps1`.
- Validate the generated `.omv` with `zipfile` instead of jamovi GUI:
  - confirm `metadata.json` exists
  - confirm at least one analysis archive entry exists
- Treat jamovi YAML files as authoritative when your memory and the YAML disagree.
