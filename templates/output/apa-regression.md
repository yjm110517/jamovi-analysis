# APA Output Template: Linear Regression

## Model Fit & Coefficients Table

```markdown
Table 8
*Summary of Linear Regression Analysis*

| Variable | *b* | *SE* | *β* | *t* | *p* | 95% CI |
| --- | --- | --- | --- | --- | --- | --- |
| Intercept | 2.10 | 0.45 | — | 4.67 | <.001 | [1.21, 2.99] |
| Age | 0.15 | 0.05 | .25 | 3.00 | .003 | [0.05, 0.25] |
| Gender | -0.30 | 0.12 | -.18 | -2.50 | .014 | [-0.54, -0.06] |

Note. *R*² = .18, Adjusted *R*² = .16, *F*(2, 117) = 12.45, *p* < .001.
```

## Extractor Contract

- Model Fit section rows: `Model`, `R`, `R2`, `Adjusted R2`, `F`, `df1`, `df2`, `p`
- Coefficients section rows: `Term`, `Estimate`, `SE`, `Lower`, `Upper`, `t`, `p`
- APA reporter must compute *β* (standardized beta) if not directly provided.
- *β* values omit leading zero when |β| < 1: `.25` not `0.25`.
