# Reporting Templates & APA Specification

> This document defines the input data templates and APA 7th edition output reporting standards for `jamovi-analysis`. It serves as the canonical reference for both users preparing data and developers writing extractors/reporters.

---

## 1. Input Data Templates

All input data must be in **wide format**: one row per participant, one column per variable.

### 1.1 General Rules

| Rule | Requirement |
|------|-------------|
| **Format** | `.csv` (UTF-8), `.tsv`, or `.xlsx` |
| **Shape** | Wide format only. No repeated-measures "long" format. |
| **Headers** | First row must be column headers. Chinese headers are allowed and will be aliased automatically. |
| **Missing values** | Leave cell empty, or use `NA`, `N/A`, `null`, `.` |
| **ID column** | Optional but recommended. Name it `user_id`, `id`, or `participant_id`. |
| **Group column** | For group comparisons, use `group`, `gender`, `class`, `condition`, etc. Must be categorical (2+ levels). |

### 1.2 Template: Pre/Post Scale Study (`prepost_scale_study`)

**Use case**: Educational psychology experiments with pre-test and post-test Likert scales.

**Required columns**:
- `user_id` — unique participant identifier
- `group` — experimental condition (optional)
- `pre_q01` ~ `pre_qNN` — pre-test items
- `post_q01` ~ `post_qNN` — post-test items

**Optional columns**:
- `cluster` — additional grouping for descriptive splits

**Constraints**:
- All scale items must be **integers** (e.g., 1–5 or 1–7).
- No decimal points in scale columns.
- Item names must match the `subscales` mapping in the JobFile.

**Example (first 3 rows)**:

| user_id | group | pre_q01 | pre_q02 | pre_q03 | post_q01 | post_q02 | post_q03 |
|---------|-------|---------|---------|---------|----------|----------|----------|
| S001    | Exp   | 4       | 3       | 5       | 5        | 4        | 5        |
| S002    | Ctrl  | 2       | 3       | 2       | 3        | 3        | 4        |
| S003    | Exp   | 3       | 4       | 4       | 4        | 5        | 5        |

### 1.3 Template: Cross-Sectional Survey (`cross_sectional_survey`)

**Use case**: Single-timepoint questionnaire studies.

**Required columns**:
- `user_id` — unique identifier
- Demographics: `gender`, `age`, `grade` (optional)
- `q01` ~ `qNN` — scale items

**Constraints**:
- Scale items are integers.
- Demographic columns can be text or numeric codes.

### 1.4 Template: Two-Group Comparison (`ttest_two_group`)

**Use case**: Simple independent-samples t-test.

**Required columns**:
- `group` — exactly 2 levels (e.g., `Exp`, `Ctrl` or `1`, `2`)
- `score` — continuous dependent variable

**Example**:

| group | score |
|-------|-------|
| Exp   | 85    |
| Ctrl  | 78    |
| Exp   | 88    |

### 1.5 Template: Reliability Analysis (`reliability_scale`)

**Use case**: Cronbach's α and McDonald's ω for a scale or subscales.

**Required columns**:
- `q01` ~ `qNN` — all items of the scale

**Constraints**:
- Items should use the same response scale (e.g., all 1–5).
- No grouping variable required.

### 1.6 Template: Regression Study (`regression_study`)

**Use case**: Linear or logistic regression.

**Required columns**:
- `y` / `dep` — dependent variable (continuous for linear, binary for logistic)
- `x1`, `x2`, `x3` — continuous predictors (covariates)
- `gender`, `condition` — categorical predictors (factors)

**Constraints**:
- Binary dependent variables must have exactly 2 unique values (e.g., `0`/`1` or `Yes`/`No`).

---

## 2. Output Reporting Standards (APA 7th Edition)

All reports support two `table_style` modes:

- `gfm` — General GitHub-flavored Markdown. Flexible, machine-readable.
- `apa` — Strict APA 7th edition formatting for education/psychology manuscripts.

This section defines the **APA mode** requirements.

### 2.1 General APA Formatting Rules

| Element | Rule |
|---------|------|
| **Decimals** | Two decimal places for means, SDs, t, F, b, β. Correlations and p-values may use 2 or 3. |
| **Statistical symbols** | Italicize in Markdown: `*M*`, `*SD*`, `*t*`, `*p*`, `*r*`, `*F*`, `*β*`, `*b*`, `*d*`, `*η*`, `*ω*`. |
| **Leading zeros** | Omit for correlations and p-values (e.g., `r = .45`, `p = .021`). Keep for all other statistics (e.g., `M = 3.45`). |
| **Tables** | Horizontal lines only (Markdown tables naturally satisfy this). No vertical borders. |
| **Table numbering** | Consecutive: Table 1, Table 2, Table 3... |
| **Table title** | Italicized, title case, placed on the line below the table number. |
| **Table notes** | Start with `Note.` (or `*p < .05. **p < .01.` for significance). |

### 2.2 Descriptive Statistics

#### Simple Descriptives (no grouping)

**Table template**:

```markdown
**Table 1**  
*Descriptive Statistics for Study Variables (N = 120)*

| Variable | *M* | *SD* | Min | Max |
|----------|-----|------|-----|-----|
| Creativity | 3.82 | 0.71 | 1.00 | 5.00 |
| Algorithmic Thinking | 3.45 | 0.89 | 1.00 | 5.00 |

Note. Scores range from 1 to 5.
```

**Extractor contract** (`build_descriptives_sections`):
- Section title: `"Descriptive Statistics"`
- Row keys: `Variable`, `N`, `Missing`, `Mean`, `Median`, `SD`, `Min`, `Max`
- APA reporter maps `Mean` → `*M*`, `SD` → `*SD*` in table headers.

#### Grouped Descriptives (splitBy)

**Table template**:

```markdown
**Table 2**  
*Descriptive Statistics for Creativity by Teaching Method*

| Variable | Traditional (*n* = 25) | Experimental (*n* = 25) |
|----------|------------------------|--------------------------|
| | *M* | *SD* | *M* | *SD* |
| Pretest | 72.40 | 8.60 | 71.80 | 9.20 |
| Posttest | 78.20 | 7.90 | 85.60 | 6.40 |
```

### 2.3 Independent Samples t-Test (`ttestIS`)

**Narrative format** (must appear in Markdown report as a summary sentence):

> The experimental group (*M* = 85.00, *SD* = 10.00) scored significantly higher than the control group (*M* = 80.00, *SD* = 15.00), *t*(49) = 2.17, *p* = .021, *d* = 0.53.

**Table template**:

```markdown
**Table 3**  
*Independent Samples t-Test for Test Scores by Group*

| Variable | Group 1 | Group 2 | *t* | *df* | *p* | Cohen's *d* | 95% CI |
|----------|---------|---------|-----|------|-----|-------------|--------|
| | *M* (*SD*) | *M* (*SD*) | | | | | |
| Test Score | 80.00 (15.00) | 85.00 (10.00) | 2.17 | 49 | .021 | 0.53 | [0.10, 1.05] |
```

**Extractor contract** (`build_ttest_sections`):
- Key Results rows must include: `Variable`, `Test`, `Statistic`, `df`, `p`, `Cohen's d` (if available from `es[stud]`)
- Descriptive sub-section must include: `Variable`, `Group 1`, `N 1`, `Mean 1`, `SD 1`, `Group 2`, `N 2`, `Mean 2`, `SD 2`
- APA reporter must merge descriptives into the main table and produce the narrative sentence.

### 2.4 Paired Samples t-Test (`ttestPS`)

**Narrative format**:

> Posttest scores (*M* = 85.60, *SD* = 6.40) were significantly higher than pretest scores (*M* = 71.80, *SD* = 9.20), *t*(24) = 4.25, *p* < .001, *d* = 1.05.

**Table template**:

```markdown
**Table 4**  
*Paired Samples t-Test for Pre-test and Post-test Scores*

| Pair | *M*<sub>diff</sub> | *SD*<sub>diff</sub> | *t* | *df* | *p* | Cohen's *d* |
|------|--------------------|---------------------|-----|------|-----|-------------|
| Posttest – Pretest | 13.80 | 4.20 | 4.25 | 24 | <.001 | 1.05 |
```

**Extractor contract** (`build_ttestps_sections`):
- Key Results rows: `Pair`, `Test`, `Statistic`, `df`, `p`, `Cohen's d`
- Descriptive sub-section: `Variable`, `N`, `Mean`, `SD`

### 2.5 One-Way ANOVA (`anovaOneW`)

**Narrative format**:

> The effect of teaching method on creativity was significant, *F*(2, 87) = 5.94, *p* = .007, *η*²p = .12.

**Table template**:

```markdown
**Table 5**  
*One-Way ANOVA for Creativity by Teaching Method*

| Source | *F* | *df*1 | *df*2 | *p* | *η*²p |
|--------|-----|-------|-------|-----|--------|
| Teaching Method | 5.94 | 2 | 87 | .007 | .12 |
```

**Group Descriptives**:

```markdown
**Table 6**  
*Group Descriptives for Creativity*

| Group | *n* | *M* | *SD* | *SE* |
|-------|-----|-----|------|------|
| Traditional | 30 | 72.40 | 8.60 | 1.57 |
| Experimental | 30 | 85.60 | 6.40 | 1.17 |
| Blended | 30 | 80.15 | 9.87 | 1.80 |
```

**Extractor contract** (`build_anova_sections`):
- Key Results rows: `Dependent Variable`, `Test`, `F`, `df1`, `df2`, `p`
- Descriptive rows: `Dependent Variable`, `Group`, `N`, `Mean`, `SD`, `SE`
- **Enhancement needed**: compute `η²p` (partial eta-squared) from F and dfs if jamovi does not provide it directly.

### 2.6 Correlation Matrix (`corrMatrix`)

**Table template**:

```markdown
**Table 7**  
*Correlation Matrix for Study Variables*

| Variable | 1 | 2 | 3 |
|----------|---|---|---|
| 1. Creativity | — | | |
| 2. Algorithmic Thinking | .45** | — | |
| 3. Critical Thinking | .32* | .28 | — |

Note. *p < .05. **p < .01.
```

**Alternative (compact long-form)** for Markdown reports with many variables:

```markdown
**Table 7**  
*Correlation Matrix for Study Variables*

| Variable 1 | Variable 2 | *r* | *df* | *p* |
|------------|------------|-----|------|-----|
| Creativity | Algorithmic Thinking | .45 | 118 | <.001 |
| Creativity | Critical Thinking | .32 | 118 | .002 |
```

**Extractor contract** (`build_corr_sections`):
- Row keys: `Variable 1`, `Variable 2`, `r`, `df`, `p`, `N`
- APA reporter must format the lower-triangular matrix with `—` on the diagonal and significance stars.

### 2.7 Linear Regression (`linReg`)

**Table template — Model Fit**:

```markdown
**Table 8**  
*Summary of Linear Regression Analysis*

| Variable | *b* | *SE* | *β* | *t* | *p* | 95% CI |
|----------|-----|------|-----|-----|------|--------|
| Intercept | 2.10 | 0.45 | — | 4.67 | <.001 | [1.21, 2.99] |
| Age | 0.15 | 0.05 | .25 | 3.00 | .003 | [0.05, 0.25] |
| Gender | -0.30 | 0.12 | -.18 | -2.50 | .014 | [-0.54, -0.06] |

Note. *R*² = .18, Adjusted *R*² = .16, *F*(2, 117) = 12.45, *p* < .001.
```

**Extractor contract** (`build_linreg_sections`):
- Model Fit section rows: `Model`, `R`, `R2`, `Adjusted R2`, `F`, `df1`, `df2`, `p`
- Coefficients section rows: `Term`, `Estimate`, `SE`, `Lower`, `Upper`, `t`, `p`
- APA reporter must compute `β` (standardized beta) if not directly provided by the extractor.

### 2.8 Binary Logistic Regression (`logRegBin`)

**Table template**:

```markdown
**Table 9**  
*Summary of Binary Logistic Regression Analysis*

| Variable | *b* | *SE* | *z* | *p* | OR | 95% CI OR |
|----------|-----|------|-----|------|-----|-----------|
| Intercept | -1.20 | 0.35 | -3.43 | .001 | 0.30 | [0.15, 0.60] |
| Age | 0.08 | 0.03 | 2.67 | .008 | 1.08 | [1.02, 1.15] |

Note. McFadden *R*² = .14, χ²(2) = 18.40, *p* < .001.
```

**Extractor contract** (`build_logreg_sections`):
- Model Fit rows: `Model`, `Deviance`, `AIC`, `McFadden R2`, `Chi Square`, `df`, `p`
- Coefficients rows: `Term`, `Estimate`, `SE`, `Lower`, `Upper`, `z`, `p`, `OR`, `OR Lower`, `OR Upper`

### 2.9 Contingency Tables (`contTables`)

**Table template — Chi-Square**:

```markdown
**Table 10**  
*Chi-Square Test of Independence for Gender and Preference*

| Test | χ² | *df* | *p* | *N* |
|------|-----|------|-----|-----|
| Pearson Chi-Square | 14.14 | 2 | <.001 | 170 |
```

**Nominal measures** (optional):

```markdown
| Measure | Value |
|---------|-------|
| Cramers *V* | .29 |
| Phi | .20 |
```

**Extractor contract** (`build_cont_tables_sections`):
- Chi Square rows: `Test`, `Value` (χ²), `df`, `p`, `N`
- Nominal rows: `Contingency Coefficient`, `Phi`, `Cramers V`

### 2.10 Reliability Analysis (`reliability`)

**Table template**:

```markdown
**Table 11**  
*Reliability Analysis (Cronbach's α and McDonald's ω)*

| Scale | Items | *M* | *SD* | Cronbach's α | McDonald's ω |
|-------|-------|-----|------|--------------|--------------|
| Creativity | 5 | 3.82 | 0.71 | .82 | .84 |
| Algorithmic Thinking | 4 | 3.45 | 0.89 | .76 | .78 |
| Total Scale | 15 | 3.60 | 0.55 | .85 | .87 |
```

**Extractor contract** (`build_reliability_sections`):
- Row keys: `Scale`, `Mean`, `SD`, `Cronbach Alpha`, `McDonalds Omega`
- APA reporter maps `Cronbach Alpha` → `Cronbach's α`, `McDonalds Omega` → `McDonald's ω`.

---

## 3. Extractor Development Contract

All extractor functions must conform to the following interface:

```python
def build_<analysis>_sections(root: Any) -> list[dict[str, Any]]:
    ...
```

### 3.1 Return Structure

Each element in the returned list is a **section**:

```python
{
    "title": "Key Results",      # or "Model Fit", "Coefficients", etc.
    "rows": [
        {"Variable": "score", "t": "2.17", "df": "49", "p": ".021"},
        ...
    ]
}
```

### 3.2 Field Naming Rules

- Use **Title Case** keys (e.g., `Variable`, `Mean`, `SD`, `Cohen's d`).
- Do not include raw Markdown formatting in keys; formatters in `report.py` handle APA italics.
- If a statistic is missing, use `None` and let the formatter skip or mark it as `—`.

### 3.3 Defensive Extraction Rules

1. **Never crash on missing elements**. Use `find_first_named_element` and check `HasField("table")`.
2. **Always fall back**. If the expected table name is missing, use `walk_result_elements` to log discoverable top-level names.
3. **Log misses**. Emit `extraction_warnings` when expected columns are absent:

```python
{
    "analysis_type": "ttestIS",
    "expected": ["ttest", "desc"],
    "found": ["ttest"],
    "reason": "Missing descriptive statistics sub-table"
}
```

### 3.4 Number Formatting Rules (for `format_number` / `format_p_value`)

| Statistic | Formatter Rule |
|-----------|----------------|
| Means, SDs, t, F, b, β, SE, OR | 2 decimal places |
| Correlations (*r*) | 2 decimal places, no leading zero |
| p-values | 2 decimal places if ≥ .001; `<.001` if smaller |
| *η*², *R*², Adjusted *R*², *ω*² | 2 decimal places |
| Sample sizes (*N*, *n*, *df*) | Integer, no decimals |

### 3.5 Adding a New Analysis Type

To add a new analysis to the extraction pipeline:

1. Add an entry to `SUPPORTED_ANALYSES` in `constants.py`.
2. Implement `build_<analysis>_sections(root)` in `extract/analyses.py`.
3. Register it in `SUMMARY_BUILDERS` in `extract/__init__.py`.
4. Add an APA table template to this document (Section 2).
5. Add a unit test in `tests/test_extract.py` with a mock result tree.
6. Create an example dataset + JobFile in `examples/` and run the smoke test.

---

## 4. JobFile Examples

### 4.1 Pre/Post Scale Study (Preset)

```json
{
  "data_path": "examples/datasets/prepost_scale_study.csv",
  "mode": "project",
  "locale": "zh",
  "request_kind": "preset",
  "preset": {
    "name": "prepost_scale_study",
    "id_column": "user_id",
    "group_column": "group",
    "max_scale": 5,
    "reverse_items": ["q03"],
    "subscales": {
      "creativity": ["q01", "q02", "q03"]
    }
  },
  "output": {
    "dir": "jamovi_outputs",
    "basename": "prepost-example",
    "table_style": "apa"
  }
}
```

### 4.2 Independent Samples t-Test (Structured)

```json
{
  "data_path": "examples/datasets/ttest_two_group.csv",
  "mode": "project",
  "request_kind": "structured",
  "analyses": [
    {
      "analysis_type": "ttestIS",
      "variables": {
        "vars": ["score"],
        "group": "group"
      },
      "options": {
        "students": true,
        "welchs": true,
        "effectSize": true,
        "ci": true,
        "desc": true
      }
    }
  ],
  "output": {
    "basename": "ttest-example",
    "table_style": "apa"
  }
}
```

### 4.3 Reliability Analysis (Structured)

```json
{
  "data_path": "examples/datasets/reliability_scale.csv",
  "mode": "project",
  "request_kind": "structured",
  "analyses": [
    {
      "analysis_type": "reliability",
      "variables": {
        "vars": ["q01", "q02", "q03", "q04", "q05"]
      }
    }
  ],
  "output": {
    "basename": "reliability-example",
    "table_style": "apa"
  }
}
```

---

## 5. Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `.omv` opens but tables are empty | `table_style` omitted or wrong | Set `"table_style": "apa"` in JobFile |
| `Effect Size` column missing in t-test | `effectSize: false` in options | Add `"effectSize": true` |
| Scale items have decimal values | Data input violation | Check `templates/input/*.csv` constraints |
| `group` variable has 3 levels but t-test requested | Measurement type mismatch | Use `anovaOneW` instead of `ttestIS` |
| Chinese headers become `var_1`, `var_2` | Normal aliasing | Refer to `column_manifest.json` for mapping |
| PDF export fails | `weasyprint` unavailable | Run `preflight-jamovi-project.ps1` first |

---

## Related Documents

- [`references/project-mode.md`](project-mode.md) — JobFile schema, lifecycle, timeout handling
- [`references/analysis-map.md`](analysis-map.md) — `jmv` function mappings
- [`references/install-layout.md`](install-layout.md) — Verified local jamovi paths
