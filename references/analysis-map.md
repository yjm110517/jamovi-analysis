# Analysis Map

Use this map to translate a user request into the correct `jmv` analysis. For exact option names and defaults, open the matching `Resources\modules\jmv\analyses\*.a.yaml` file from the jamovi install.

## Project-Mode v1 Coverage

These are implemented in `.omv` project mode:

- Exploratory summaries, histograms, boxplots, QQ plots: `descriptives`
  - YAML: `descriptives.a.yaml`
- Independent groups t-test: `ttestIS`
  - YAML: `ttestis.a.yaml`
- One-way ANOVA: `anovaOneW`
  - YAML: `anovaonew.a.yaml`
- Correlation matrix: `corrMatrix`
  - YAML: `corrmatrix.a.yaml`
- Linear regression: `linReg`
  - YAML: `linreg.a.yaml`
- Binary logistic regression: `logRegBin`
  - YAML: `logregbin.a.yaml`
- Contingency tables and chi-square: `contTables`
  - YAML: `conttables.a.yaml`
- Reliability and Cronbach alpha: `reliability`
  - YAML: `reliability.a.yaml`

## Batch-Mode Only For Now

These remain batch-mode references in v1 and are not implemented in project mode:

- Paired samples t-test: `ttestPS`
  - YAML: `ttestps.a.yaml`
- One-sample t-test: `ttestOneS`
  - YAML: `ttestones.a.yaml`
- Factorial ANOVA: `ANOVA`
  - YAML: `anova.a.yaml`
- Repeated-measures ANOVA: `anovaRM`
  - YAML: `anovarm.a.yaml`
- ANCOVA: `ancova`
  - YAML: `ancova.a.yaml`
- Multinomial logistic regression: `logRegMulti`
  - YAML: `logregmulti.a.yaml`
- Ordinal logistic regression: `logRegOrd`
  - YAML: `logregord.a.yaml`
- Paired contingency tables: `contTablesPaired`
  - YAML: `conttablespaired.a.yaml`
- Partial correlations: `corrPart`
  - YAML: `corrpart.a.yaml`
- Principal components analysis: `pca`
  - YAML: `pca.a.yaml`
- Exploratory factor analysis: `efa`
  - YAML: `efa.a.yaml`
- Confirmatory factor analysis: `cfa`
  - YAML: `cfa.a.yaml`

## Measurement Rules Worth Checking First

- `ttestIS`
  - dependent variable must be continuous
  - grouping variable must be nominal or ordinal with 2 levels
- `anovaOneW`
  - dependent variable must be continuous
  - grouping variable must be nominal or ordinal
- `corrMatrix`
  - variables should be continuous in project mode v1
- `linReg`
  - dependent variable must be continuous
  - covariates must be continuous
  - factors must be nominal or ordinal
- `logRegBin`
  - dependent variable must be nominal or ordinal with 2 levels
- `contTables`
  - rows and columns must be categorical
- `reliability`
  - items must be continuous or ordinal

## Reliable Calling Patterns

- Prefer formula-style interpretation when the analysis has a clear dependent and grouping structure.
- In project mode, pass variables as a structured JSON object keyed by jamovi option name.
- Let the runner inject a small set of stable defaults for key-result extraction, then add only the extra options you need.

## Minimal Structured Examples

### Descriptives

```json
{
  "analysis_type": "descriptives",
  "variables": {
    "vars": ["score", "age"]
  }
}
```

### Independent Samples T-Test

```json
{
  "analysis_type": "ttestIS",
  "variables": {
    "vars": ["score"],
    "group": "group"
  }
}
```

### Linear Regression

```json
{
  "analysis_type": "linReg",
  "variables": {
    "dep": "outcome",
    "covs": ["x1", "x2"],
    "factors": ["condition"]
  }
}
```
