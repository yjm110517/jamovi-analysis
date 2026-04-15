# APA Output Template: Descriptive Statistics

## Simple Descriptives

```markdown
Table 1
*Descriptive Statistics for Study Variables (N = 120)*

| Variable | *M* | *SD* | Min | Max |
| --- | --- | --- | --- | --- |
| Creativity | 3.82 | 0.71 | 1.00 | 5.00 |
| Algorithmic Thinking | 3.45 | 0.89 | 1.00 | 5.00 |

Note. Scores range from 1 to 5.
```

## Grouped Descriptives (splitBy)

```markdown
Table 2
*Descriptive Statistics for Creativity by Teaching Method*

| Variable | Traditional (*n* = 25) | Experimental (*n* = 25) |
| --- | --- | --- |
|  | *M* | *SD* | *M* | *SD* |
| Pretest | 72.40 | 8.60 | 71.80 | 9.20 |
| Posttest | 78.20 | 7.90 | 85.60 | 6.40 |
```

## Extractor Contract

- Section title: `"Descriptive Statistics"` (replaces generic "Key Results")
- Row keys: `Variable`, `N`, `Missing`, `Mean`, `Median`, `SD`, `Min`, `Max`
- APA reporter maps:
  - `Mean` → `*M*`
  - `SD` → `*SD*`
  - `N` → `*n*` when used in group headers
