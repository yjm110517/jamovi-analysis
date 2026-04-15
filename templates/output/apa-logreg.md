# APA Output Template: Binary Logistic Regression

## Table Format

```markdown
Table 9
*Summary of Binary Logistic Regression Analysis*

| Variable | *b* | *SE* | *z* | *p* | OR | 95% CI OR |
| --- | --- | --- | --- | --- | --- | --- |
| Intercept | -1.20 | 0.35 | -3.43 | .001 | 0.30 | [0.15, 0.60] |
| Age | 0.08 | 0.03 | 2.67 | .008 | 1.08 | [1.02, 1.15] |

Note. McFadden *R*² = .14, χ²(2) = 18.40, *p* < .001.
```

## Extractor Contract

- Model Fit rows: `Model`, `Deviance`, `AIC`, `McFadden R2`, `Chi Square`, `df`, `p`
- Coefficients rows: `Term`, `Estimate`, `SE`, `Lower`, `Upper`, `z`, `p`, `OR`, `OR Lower`, `OR Upper`
