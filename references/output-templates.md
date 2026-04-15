# Extractor Output Templates (Developer Contract)

> This document defines the **canonical output contract** for every jamovi result extractor in `src/jamovi_runner/extract/`. It is the reference developers should consult when modifying extractors or writing new ones. End-user APA formatting rules live in [`reporting-templates.md`](reporting-templates.md).

---

## General Rules

1. **Return type**: Every extractor must return `list[dict[str, Any]]` where each dict is a *section*:
   ```python
   {
       "title": str,          # e.g. "Key Results", "Model Fit"
       "rows": list[dict],    # one dict per table row
   }
   ```
2. **Keys**: Use Title Case English labels (e.g. `Variable`, `Mean`, `SD`). The APA reporter (`APATableFormatter`) maps these to italicized symbols automatically.
3. **Missing values**: Use `None` or omit the key. Never use `""` to mean a computed statistic is missing.
4. **Formatting**: Extractors should call `format_number()` and `format_p_value()` from `jamovi_runner.formatting` so that raw numbers are already formatted when they reach the reporter.
5. **Effect sizes**: Whenever jamovi provides an effect size (or it can be derived from available statistics), the extractor **must** include it. Do not leave this to the reporter.

---

## Analysis Type Contracts

### 1. Descriptives (`descriptives`)

**Extractor**: `build_descriptives_sections` in `descriptives.py`

**Sections**:
- `title`: `"Descriptive Statistics"`
- `rows`: list of dicts with these keys

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `Variable` | str | Yes | Variable name |
| `N` | str | Yes | Sample size |
| `Missing` | str | No | Count of missing values |
| `Mean` | str | Yes | Formatted mean |
| `Median` | str | No | Formatted median |
| `SD` | str | Yes | Standard deviation |
| `Min` | str | No | Minimum value |
| `Max` | str | No | Maximum value |

**Validation**: Rows with placeholder labels (`var\d*`, `overall`, `total`) are skipped.

---

### 2. Independent Samples t-Test (`ttestIS`)

**Extractor**: `build_ttest_sections` in `ttest_is.py`

**Sections**:

1. **Key Results**
   - `title`: `"Key Results"`
   - Row keys:

   | Key | Type | Required | Notes |
   |-----|------|----------|-------|
   | `Variable` | str | Yes | Dependent variable name |
   | `Test` | str | Yes | Test type (Student's, Welch's, Mann-Whitney) |
   | `Statistic` | str | Yes | Test statistic |
   | `df` | str | Yes | Degrees of freedom |
   | `p` | str | Yes | Formatted p-value |
   | `Cohen's d` | str | **Yes** | Effect size from `es[stud]` / `es[welc]` / `es[mann]` |

2. **Group Descriptives** (optional)
   - `title`: `"Group Descriptives"`
   - Row keys: `Variable`, `Group 1`, `N 1`, `Mean 1`, `SD 1`, `Group 2`, `N 2`, `Mean 2`, `SD 2`

---

### 3. Paired Samples t-Test (`ttestPS`)

**Extractor**: `build_ttestps_sections` in `ttest_ps.py`

**Sections**:

1. **Key Results**
   - `title`: `"Key Results"`
   - Row keys:

   | Key | Type | Required | Notes |
   |-----|------|----------|-------|
   | `Pair` | str | Yes | e.g. `"Post - Pre"` |
   | `Test` | str | Yes | Test type |
   | `Statistic` | str | Yes | t or W |
   | `df` | str | Yes | df |
   | `p` | str | Yes | p-value |
   | `Cohen's d` | str | **Yes** | Effect size when available |

2. **Group Descriptives** (optional)
   - `title`: `"Group Descriptives"`
   - Row keys: `Variable`, `N`, `Mean`, `SD`

---

### 4. One-Way ANOVA (`anovaOneW`)

**Extractor**: `build_anova_sections` in `anova.py`

**Sections**:

1. **Key Results**
   - `title`: `"Key Results"`
   - Row keys:

   | Key | Type | Required | Notes |
   |-----|------|----------|-------|
   | `Dependent Variable` | str | Yes | Outcome variable |
   | `Test` | str | Yes | `"Fisher"` or `"Welch"` |
   | `F` | str | Yes | F statistic |
   | `df1` | str | Yes | Between-groups df |
   | `df2` | str | Yes | Within-groups df |
   | `p` | str | Yes | p-value |
   | `etaSqP` | str | **Yes** | **Partial eta-squared computed by extractor**: `F * df1 / (F * df1 + df2)` |

2. **Group Descriptives** (optional)
   - `title`: `"Group Descriptives"`
   - Row keys: `Dependent Variable`, `Group`, `N`, `Mean`, `SD`, `SE`

---

### 5. Correlation Matrix (`corrMatrix`)

**Extractor**: `build_corr_sections` in `corr_matrix.py`

**Sections**:
- `title`: `"Correlation Matrix"` (or similar)
- Row keys:

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `Variable 1` | str | Yes | First variable name |
| `Variable 2` | str | Yes | Second variable name |
| `r` | str | Yes | Correlation coefficient |
| `df` | str | No | df for the correlation |
| `p` | str | Yes | p-value |
| `N` | str | No | Sample size |

**Note**: The APA reporter may reshape these long-form rows into a lower-triangular matrix.

---

### 6. Linear Regression (`linReg`)

**Extractor**: `build_linreg_sections` in `lin_reg.py`

**Sections**:

1. **Model Fit**
   - `title`: `"Model Fit"`
   - Row keys:

   | Key | Type | Required | Notes |
   |-----|------|----------|-------|
   | `Model` | str | Yes | Model number or step |
   | `R` | str | No | Multiple R |
   | `R2` | str | Yes | R-squared |
   | `Adjusted R2` | str | Yes | Adjusted R-squared |
   | `F` | str | Yes | Model F statistic |
   | `df1` | str | Yes | Model df |
   | `df2` | str | Yes | Residual df |
   | `p` | str | Yes | Model p-value |

2. **Coefficients**
   - `title`: `"Coefficients"`
   - Row keys:

   | Key | Type | Required | Notes |
   |-----|------|----------|-------|
   | `Term` | str | Yes | Predictor / Intercept |
   | `Estimate` | str | Yes | Unstandardized *b* |
   | `SE` | str | Yes | Standard error |
   | `Lower` | str | No | CI lower bound |
   | `Upper` | str | No | CI upper bound |
   | `t` | str | Yes | t statistic |
   | `p` | str | Yes | p-value |
   | `beta` | str | **Yes** | **Standardized β extracted from jamovi when available** |

---

### 7. Binary Logistic Regression (`logRegBin`)

**Extractor**: `build_logreg_sections` in `log_reg_bin.py`

**Sections**:

1. **Model Fit**
   - `title`: `"Model Fit"`
   - Row keys: `Model`, `McFadden R2`, `Chi Square`, `df`, `p`

2. **Coefficients**
   - `title`: `"Coefficients"`
   - Row keys: `Term`, `Estimate`, `SE`, `Lower`, `Upper`, `z`, `p`, `OR`, `OR Lower`, `OR Upper`

---

### 8. Contingency Tables (`contTables`)

**Extractor**: `build_cont_tables_sections` in `cont_tables.py`

**Sections**:

1. **Chi-Square Test**
   - `title`: `"Chi-Square Test"`
   - Row keys: `Test`, `Value`, `df`, `p`, `N`

2. **Nominal Measures** (optional)
   - `title`: `"Nominal Measures"`
   - Row keys: `Contingency Coefficient`, `Phi`, `Cramers V`

---

### 9. Reliability Analysis (`reliability`)

**Extractor**: `build_reliability_sections` in `reliability.py`

**Sections**:
- `title`: `"Scale Reliability"`
- Row keys:

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `Scale` | str | Yes | Scale / subscale name |
| `Mean` | str | No | Mean of scale scores |
| `SD` | str | No | SD of scale scores |
| `Cronbach Alpha` | str | Yes | Internal consistency |
| `McDonalds Omega` | str | No | Alternative reliability index |

---

## Effect-Size Derivation Rules

When jamovi does **not** return an effect size directly, the extractor must compute it if the required inputs are present:

| Analysis | Effect Size | Formula | Status |
|----------|-------------|---------|--------|
| ANOVA | η²p (partial eta-squared) | `F * df1 / (F * df1 + df2)` | **Implemented** in `anova.py` |
| Linear Regression | β (standardized beta) | Requires variable SDs; currently extracted from jamovi `beta` column when available | **Extracted** in `lin_reg.py` |
| t-test | Cohen's d | Read from `es[stud]` / `es[welc]` / `es[mann]` | **Implemented** in `ttest_is.py` and `ttest_ps.py` |

---

## Header Mapping to APA Symbols

The `APATableFormatter` in `reporters/apa.py` automatically converts these extractor keys into APA-italicized Markdown headers:

| Extractor Key | APA Header |
|---------------|------------|
| `Mean` / `M` | `*M*` |
| `SD` | `*SD*` |
| `N` / `n` | `*N*` / `*n*` |
| `t` | `*t*` |
| `p` | `*p*` |
| `r` | `*r*` |
| `F` | `*F*` |
| `b` | `*b*` |
| `beta` / `β` | `*β*` |
| `eta` / `η` | `*η*` |
| `etasq` / `eta2` / `η²` | `*η*²` |
| `etaSqP` | `*η*²p` |
| `df` | `*df*` |
| `se` / `SE` | `*SE*` |
| `R2` | `*R*²` |
| `R2Adj` | `Adjusted *R*²` |
| `Cronbach Alpha` | `Cronbach's α` |
| `McDonalds Omega` | `McDonald's ω` |

Keys not in this mapping are passed through unchanged.

---

## Modification Policy

> **If you change an extractor's output keys, you must update this file.**

This document is the source of truth for:
- Unit tests in `tests/test_extract.py`
- APA reporter header mapping in `reporters/apa.py`
- End-user templates in `references/reporting-templates.md`
