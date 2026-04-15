---
name: jamovi-analysis
description: Run jamovi-native statistical analyses with the local jamovi installation. Use when the user asks to analyze data with jamovi or jmv, wants jamovi-compatible descriptives, t-tests, ANOVA, regression, correlation, contingency tables, reliability workflows, or needs a real `.omv` project saved through jamovi internals.
version: 1.0
---

# Jamovi Analysis

**Primary Rule:** By default, always use **Project Mode** with a **JobFile** (JSON configuration). This ensures data preprocessing, stable execution, and generates a real `.omv` project file and Markdown summary.

Only use R batch mode if the user explicitly asks for "quick terminal statistics without saving". Only use server mode if the user explicitly asks for "a live session".

## When to Use

Use this skill when the user requests any of the following:

- **Statistical analyses via jamovi**: t-tests, ANOVA, regression, correlation, contingency tables, reliability (Cronbach's α), or descriptive statistics.
- **Generating a `.omv` project file** programmatically from a dataset.
- **APA 7th edition formatted reports** (Markdown or DOCX) from jamovi output.
- **Preprocessing survey/scale data**: reverse scoring, subscale aggregation, column aliasing for non-English headers.

Do **not** use this skill when the user:

- Asks for a generic R script without mentioning jamovi (use plain R instead).
- Wants interactive GUI instructions for the jamovi desktop app (this skill is automation/programmatic only).

## Usage

The canonical workflow is a two-step "call":

1. **Generate a JobFile** (JSON config) based on the user's data and analysis needs.
2. **Execute the PowerShell wrapper** with the `-JobFile` parameter.

```powershell
& '.\scripts\invoke-jamovi-project.ps1' -JobFile '.\temp\job.json'
```

Claude should perform both steps automatically: write the JSON file to a sensible location, then invoke the script.

## Quick Start

1. The wrapper `scripts/invoke-jamovi-project.ps1` will automatically discover the jamovi install root.
2. The recommended interface is to write a single JSON configuration (`JobFile`) and pass it via `-JobFile`.
3. If the input data is a raw survey/instructional dataset (with Chinese headers, empty columns, duplicate names, or reverse scoring needs), **you MUST use the preprocess stage**. Do NOT manually clean the CSV via python scripts yourself—the runner does this for you automatically when invoked properly.

## Data Preparation & Templates

Before running any analysis, ensure the input data follows these rules:

1. **Wide Format**: One row per participant, one column per variable.
2. **Headers**: First row must be column names. Chinese headers are supported and will be aliased automatically.
3. **Missing Values**: Leave cells empty, or use `NA`, `N/A`, `null`, `.`.
4. **Scale Items**: Must be integers (e.g., 1–5 or 1–7). No decimal points.
5. **Grouping Variables**: For independent-samples t-tests, exactly 2 levels; for ANOVA, 2 or more levels.

### Ready-Made Templates

Use the CSV templates in `templates/input/` as a starting point:

| Template | Use Case |
|----------|----------|
| `prepost_scale_study.csv` | Educational experiments with pre-test and post-test Likert scales |
| `cross_sectional_survey.csv` | Single-timepoint questionnaire studies |
| `ttest_two_group.csv` | Simple independent-samples t-test |
| `reliability_scale.csv` | Cronbach's α and McDonald's ω analysis |
| `regression_study.csv` | Linear or binary logistic regression |

See `templates/input/README.md` for column naming conventions and constraints.

### Working Examples

The `examples/` directory contains runnable sample datasets and expected APA outputs:

```powershell
& 'scripts/invoke-jamovi-project.ps1' -JobFile 'examples/ttest_study/jobfile.json'
```

Each example includes:
- `data.csv` — sample dataset
- `jobfile.json` — ready-to-run JobFile
- `expected-output.md` — expected APA 7th edition report format

## The Canonical Request (JobFile)

You should create a JSON file (e.g., `request.json` in a temp dir) and pass its path to `invoke-jamovi-project.ps1 -JobFile temp\request.json`.

### Preset Mode (Highly Recommended for Surveys/Assessments)

For educational data, pre/post tests, and rating scales, use the `preset` mode. The runner will automatically:
1. Clean headers and create stable ASCII aliases (`column_manifest.json`).
2. Deduplicate empty columns.
3. Compute reverse-scored items (using `max_scale`).
4. Calculate subscale mean scores.
5. Automatically run a preset suite of analyses:
   - `descriptives` (pre/post/delta subscales, split by group/cluster when provided)
   - `ttestPS` (paired pre vs post for each subscale)
   - `ttestIS` (delta by group, if group column is provided)

```json
{
  "data_path": "C:/data/raw_study.xlsx",
  "mode": "project",
  "sheet": "Sheet1",
  "locale": "zh",
  "request_kind": "preset",
  "preset": {
    "name": "prepost_scale_study",
    "id_column": "user_id",
    "group_column": "class_group",
    "cluster_column": "cluster_type",
    "pre_prefix": "pre_",
    "post_prefix": "post_",
    "max_scale": 5,
    "reverse_items": ["q24", "q25", "q26"],
    "subscales": {
      "creativity": ["q01", "q02", "q03"],
      "algorithmic": ["q09", "q10", "q11"]
    }
  },
  "output": {
    "dir": "C:/data/jamovi_outputs",
    "basename": "ct-core-analysis",
    "table_style": "apa"
  }
}
```

> **Note**: `locale` defaults to `"zh"` (Chinese). Set to `"en"` for English .omv labels. The `reverse_items` and `subscales` items can use either alias keys (e.g. `q24`) or original header text.

### Structured Mode

If you need a specific set of tests rather than a full survey preset, use `request_kind: "structured"`. The runner will still perform standard data cleaning (ASCII aliasing) before running your specified analyses.

```json
{
  "data_path": "C:/data/study.csv",
  "mode": "project",
  "request_kind": "structured",
  "analyses": [
    {
      "analysis_type": "descriptives",
      "variables": {
        "vars": ["score", "age"],
        "splitBy": ["group"]
      }
    },
    {
      "analysis_type": "ttestIS",
      "variables": {
        "vars": ["score", "time"],
        "group": "group"
      },
      "options": {
        "students": true,
        "effectSize": true,
        "ci": true,
        "desc": true
      }
    }
  ],
  "output": {
    "dir": "C:/data/jamovi_outputs",
    "basename": "study-report",
    "table_style": "apa"
  }
}
```

### Script Execution

```powershell
& '.\scripts\invoke-jamovi-project.ps1' -JobFile '.\temp\job.json'
```

## Supported Analyses

- `descriptives`
- `ttestIS` (Independent groups t-test)
- `ttestPS` (Paired samples t-test)
- `anovaOneW`
- `corrMatrix`
- `linReg`
- `logRegBin`
- `contTables`
- `reliability`

## Report Formats

The output Markdown report supports two `table_style` modes:

- `gfm` — General GitHub-flavored Markdown. Flexible, machine-readable.
- `apa` — Strict APA 7th edition formatting for education/psychology manuscripts.

### APA 7th Edition Output Examples

When `table_style` is set to `"apa"`, the report follows these conventions:
- **Decimals**: Two decimal places for means, SDs, t, F, b, β.
- **Statistical symbols**: Italicized: *M*, *SD*, *t*, *p*, *r*, *F*, *β*, *b*, *η*, *ω*.
- **Leading zeros**: Omitted for correlations and p-values (e.g., `r = .45`, `p = .021`). Kept for other statistics (e.g., `M = 3.45`).
- **Tables**: Numbered consecutively (Table 1, Table 2...), titles italicized.

#### Descriptive Statistics Example

```markdown
Table 1
*Descriptive Statistics for Study Variables (N = 120)*

| Variable | *M* | *SD* | Min | Max |
|----------|-----|------|-----|-----|
| Creativity | 3.82 | 0.71 | 1.00 | 5.00 |
| Algorithmic Thinking | 3.45 | 0.89 | 1.00 | 5.00 |

Note. Scores range from 1 to 5.
```

#### Independent Samples t-Test Example

```markdown
Table 2
*Independent Samples t-Test for Test Scores by Group*

| Variable | Group 1 | Group 2 | *t* | *df* | *p* | Cohen's *d* | 95% CI |
|----------|---------|---------|-----|------|-----|-------------|--------|
| | *M* (*SD*) | *M* (*SD*) | | | | | |
| Test Score | 80.00 (15.00) | 85.00 (10.00) | 2.17 | 49 | .021 | 0.53 | [0.10, 1.05] |
```

> The experimental group (*M* = 85.00, *SD* = 10.00) scored significantly higher than the control group (*M* = 80.00, *SD* = 15.00), *t*(49) = 2.17, *p* = .021, *d* = 0.53.

For the complete APA specification, see `references/reporting-templates.md`.

## Legacy Wrapper Scripts & Modes

- `scripts/invoke-jamovi-project.ps1`: Accepts legacy flags (`-DataPath`, `-SpecJson`, `-Request`). These bypass the new JobFile canonical flow but are maintained for backward compatibility.
- `scripts/invoke-jamovi-r.ps1`: Run bundled R batch scripts.
- `scripts/start-jamovi-server.ps1`: Start an interactive browser jamovi backend.

## References

- Read [references/project-mode.md](references/project-mode.md) for the structured spec schema, measurement rules, lifecycle, and validation expectations.
- Read [references/analysis-map.md](references/analysis-map.md) for common `jmv` function mappings and project-mode scope.
- Read [references/reporting-templates.md](references/reporting-templates.md) for the full APA 7th edition table templates and extractor contracts.
