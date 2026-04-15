# Jamovi Analysis Examples

This directory contains ready-to-run example datasets and JobFiles for common educational psychology research designs.

## Directory Structure

Each subdirectory contains:
- `data.csv` — Sample input dataset
- `jobfile.json` — JobFile configuration for the runner
- `expected-output.md` — Expected APA 7th edition output format

## Available Examples

| Example | Design | Analysis Types |
|---------|--------|----------------|
| `prepost_scale_study/` | Pre-test / Post-test scale study | Descriptives, Paired t-test |
| `cross_sectional_survey/` | Cross-sectional questionnaire | Descriptives, Correlation Matrix |
| `ttest_study/` | Two-group comparison | Independent Samples t-test |
| `reliability_study/` | Scale reliability | Cronbach's α, McDonald's ω |
| `regression_study/` | Predictive modeling | Linear Regression |

## Running an Example

```powershell
& 'scripts/invoke-jamovi-project.ps1' -JobFile 'examples/ttest_study/jobfile.json'
```

## Data Preparation Guide

When preparing your own data, follow these rules:

1. **Wide Format**: One row per participant, one column per variable.
2. **Headers**: First row must be column names. Chinese headers are supported.
3. **Missing Values**: Leave cells empty, or use `NA`, `N/A`, `null`, `.`.
4. **Scale Items**: Must be integers (e.g., 1–5 or 1–7). No decimals.
5. **Grouping Variables**: For t-tests, exactly 2 levels; for ANOVA, 2+ levels.

For detailed template specifications, see `templates/input/README.md`.
For APA output specifications, see `references/reporting-templates.md`.
