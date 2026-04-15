# APA Output Template: Independent Samples t-Test

## Narrative Format

> The experimental group (*M* = 85.00, *SD* = 10.00) scored significantly higher than the control group (*M* = 80.00, *SD* = 15.00), *t*(49) = 2.17, *p* = .021, *d* = 0.53.

## Table Format

```markdown
Table 3
*Independent Samples t-Test for Test Scores by Group*

| Variable | Group 1 | Group 2 | *t* | *df* | *p* | Cohen's *d* | 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  | *M* (*SD*) | *M* (*SD*) |  |  |  |  |  |
| Test Score | 80.00 (15.00) | 85.00 (10.00) | 2.17 | 49 | .021 | 0.53 | [0.10, 1.05] |
```

## Extractor Contract

- Key Results rows must include: `Variable`, `Test`, `Statistic`, `df`, `p`, `Cohen's d`
- Descriptive sub-section must include: `Variable`, `Group 1`, `N 1`, `Mean 1`, `SD 1`, `Group 2`, `N 2`, `Mean 2`, `SD 2`
- APA reporter merges descriptives into `*M* (*SD*)` format and produces the narrative sentence.
