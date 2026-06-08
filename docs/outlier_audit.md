# Outlier and distribution audit

This note records the Stage 7 audit for variable distributions and extreme values. The audit is diagnostic. It does not winsorize, trim, or overwrite the analysis panel.

## Command

Run the audit after the analysis panels are built:

```bash
PYTHONPATH=src python scripts/audit_extremes.py \
  --input-panel outputs/analysis_panel/public_private_nonprofit/analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet \
  --input-panel outputs/analysis_panel/public/analysis_panel_coa_headroom_2009_2023_public.parquet \
  --input-panel outputs/analysis_panel/private_nonprofit/analysis_panel_coa_headroom_2009_2023_private_nonprofit.parquet \
  --output-dir outputs/extreme_audit
```

Each input panel gets its own output directory under `outputs/extreme_audit/`.

## Generated files

- `extreme_audit_dataset_shape.csv`: rows, columns, institutions, year range, duplicate key count, memory use, and type counts.
- `extreme_audit_variable_profile.csv`: one row per variable with storage type, inferred logical type, missingness, unique counts, zero counts, negative counts, quantiles, IQR fences, skew, and tail counts.
- `extreme_audit_review_candidates.csv`: variables whose distribution should be reviewed before any outlier handling rule is chosen.
- `extreme_audit_top_rows.csv`: highest and lowest rows for each numeric variable, with institution identifiers where available.
- `extreme_audit_by_year_distribution.csv`: year-level min, p1, median, p99, and max for each numeric variable.
- `extreme_audit_categorical_profile.csv`: top values for categorical and boolean variables.
- `extreme_audit_summary.json`: run metadata and output paths.

## Review rule

A variable enters `extreme_audit_review_candidates.csv` when at least one of these conditions holds:

- values fall outside the outer IQR fence,
- the maximum is at least three times the 99th percentile,
- the 99th percentile is at least ten times the median,
- negative values appear outside fields where negative values are already tracked as diagnostic net-price values or are expected by construction.

Those rules are screening rules. They do not imply that the value is wrong or that it should be winsorized.

Numeric IPEDS code fields are still profiled, but they are not treated as winsorization candidates. That prevents identifiers, survey status codes, classification codes, and boolean flags from being mixed with continuous dollar, count, percentage, and ratio fields.

## Current local audit

Using the local 2009-2023 analysis-panel build verified on June 8, 2026:

| Scope | Rows | Columns | Numeric or numeric-like columns | Boolean columns | Categorical columns | Review-candidate columns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| public + private nonprofit | 35,443 | 349 | 293 | 52 | 4 | 163 |
| public | 11,215 | 349 | 293 | 52 | 4 | 148 |
| private nonprofit | 24,228 | 349 | 293 | 52 | 4 | 133 |

For the combined baseline, review candidates cluster in these groups:

| Group | Candidate columns |
| --- | ---: |
| other continuous fields | 41 |
| full-time first-time aid | 39 |
| net price | 36 |
| derived finance | 13 |
| undergraduate aid | 12 |
| admissions and selectivity | 10 |
| charges | 9 |
| derived COA and headroom | 3 |

Selected baseline profiles:

| Variable | Non-null rows | Missing share | p1 | Median | p99 | Maximum | Negative rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `COA_OFF_NF` | 26,386 | 25.6% | 11,584.85 | 28,056 | 69,739.80 | 90,910 | 0 |
| `HEADROOM_OFF_NF` | 26,387 | 25.6% | 5,417.20 | 13,700 | 23,878.76 | 38,574 | 0 |
| `PGRNT_T` | 29,802 | 15.9% | 0 | 608,788 | 9,798,041 | 37,856,710 | 0 |
| `IGRNT_T` | 29,802 | 15.9% | 0 | 2,162,462 | 45,928,214 | 145,786,754 | 0 |
| `FIN_TOTAL_REVENUE` | 32,560 | 8.1% | 528,350.33 | 50,546,125 | 3,479,570,836 | 18,439,120,000 | 126 |
| `NET_PRICE_0_30000` | 25,005 | 29.5% | 1,497.04 | 13,335 | 33,798.60 | 62,129 | 39 |

The top rows show that many large aid and finance values belong to very large institutions rather than obvious data-entry errors. For example, the largest `PGRNT_T` rows include Miami Dade College, the largest `IGRNT_T` rows include Northeastern University and Arizona State University Campus Immersion, and the largest finance-revenue rows include Harvard University, the University of Pennsylvania, and Stanford University. Those rows should be reviewed, but their scale is not enough by itself to justify automatic winsorization.

## Paper-use boundary

Winsorization should be variable-specific. A blanket cap across all variables would mix different measurement scales: dollars, counts, percentages, ratios, logs, flags, and categorical codes. The audit should be used to separate likely reporting errors from legitimate institutional heterogeneity.

The descriptive-statistics exhibits use a separate table-only rule in `config/descstat_variables.csv`. Those caps are applied inside `scripts/build_descstat_tables.py` and are reported beside raw means and standard deviations. They do not overwrite the panel.

For the paper, describe this stage as:

> Before estimating the models, I audited every analysis-panel variable for storage type, missingness, distributional shape, zero values, negative values, year-level shifts, and tail observations. I did not alter the panel at this stage. Any later winsorization or trimming rule is applied only after a variable-level review and is reported as a sensitivity choice rather than as a hidden cleaning step.
