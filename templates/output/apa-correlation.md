# APA Output Template: Correlation Matrix

## Matrix Table

```markdown
Table 7
*Correlation Matrix for Study Variables*

| Variable | 1 | 2 | 3 |
| --- | --- | --- | --- |
| 1. Creativity | — |  |  |
| 2. Algorithmic Thinking | .45** | — |  |
| 3. Critical Thinking | .32* | .28 | — |

Note. *p < .05. **p < .01.
```

## Alternative Long-Form Table

```markdown
Table 7
*Correlation Matrix for Study Variables*

| Variable 1 | Variable 2 | *r* | *df* | *p* |
| --- | --- | --- | --- | --- |
| Creativity | Algorithmic Thinking | .45 | 118 | <.001 |
| Creativity | Critical Thinking | .32 | 118 | .002 |
```

## Extractor Contract

- Row keys: `Variable 1`, `Variable 2`, `r`, `df`, `p`, `N`
- APA reporter must format the lower-triangular matrix with `—` on the diagonal and significance stars.
- Correlations omit leading zero: `.45` not `0.45`.
