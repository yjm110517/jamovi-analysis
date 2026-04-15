# APA Output Template: One-Way ANOVA

## Narrative Format

> The effect of teaching method on creativity was significant, *F*(2, 87) = 5.94, *p* = .007, *η*²p = .12.

## ANOVA Table

```markdown
Table 5
*One-Way ANOVA for Creativity by Teaching Method*

| Source | *F* | *df*1 | *df*2 | *p* | *η*²p |
| --- | --- | --- | --- | --- | --- |
| Teaching Method | 5.94 | 2 | 87 | .007 | .12 |
```

## Group Descriptives

```markdown
Table 6
*Group Descriptives for Creativity*

| Group | *n* | *M* | *SD* | *SE* |
| --- | --- | --- | --- | --- |
| Traditional | 30 | 72.40 | 8.60 | 1.57 |
| Experimental | 30 | 85.60 | 6.40 | 1.17 |
| Blended | 30 | 80.15 | 9.87 | 1.80 |
```

## Extractor Contract

- Key Results rows: `Dependent Variable`, `Test`, `F`, `df1`, `df2`, `p`
- Descriptive rows: `Dependent Variable`, `Group`, `N`, `Mean`, `SD`, `SE`
- **Enhancement needed**: compute *η*²p (partial eta-squared) from *F* and dfs if not directly available.
