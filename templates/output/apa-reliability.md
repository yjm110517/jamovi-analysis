# APA Output Template: Reliability Analysis

## Table Format

```markdown
Table 11
*Reliability Analysis (Cronbach's α and McDonald's ω)*

| Scale | Items | *M* | *SD* | Cronbach's α | McDonald's ω |
| --- | --- | --- | --- | --- | --- |
| Creativity | 5 | 3.82 | 0.71 | .82 | .84 |
| Algorithmic Thinking | 4 | 3.45 | 0.89 | .76 | .78 |
| Total Scale | 15 | 3.60 | 0.55 | .85 | .87 |
```

## Extractor Contract

- Row keys: `Scale`, `Mean`, `SD`, `Cronbach Alpha`, `McDonalds Omega`
- APA reporter maps:
  - `Cronbach Alpha` → `Cronbach's α`
  - `McDonalds Omega` → `McDonald's ω`
- *α* and *ω* omit leading zero when < 1: `.82` not `0.82`.
