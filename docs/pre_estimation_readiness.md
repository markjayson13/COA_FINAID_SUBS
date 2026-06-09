# Pre-estimation readiness

This note records the checks that run before fixed-effects estimation. The goal is to make model samples explicit before any regression code can drop rows silently.

Run:

```bash
PYTHONPATH=src python scripts/build_model_samples.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/model_samples \
  --config config/model_specifications.csv
```

The script writes:

- `outputs/model_samples/model_sample_manifest.csv`
- `outputs/model_samples/model_sample_variable_missingness.csv`
- one complete-case parquet for each model under `outputs/model_samples/samples/`
- `outputs/model_samples/model_sample_summary.json`

The latest local run wrote all 25 planned baseline, sector-year, component, and sensitivity model samples and found no missing model variables.

The baseline estimation validator also passed after the refreshed model samples were estimated:

```text
25 models observed
0 validation issues
```

## Current model samples

| Model | Rows | Institutions | Singleton institutions | Institutions without focal within variation |
| --- | ---: | ---: | ---: | ---: |
| `fe_inst_grant_per_student` | 24,247 | 2,082 | 44 | 44 |
| `fe_inst_grant_share` | 24,125 | 2,075 | 47 | 16 |
| `fe_pell_per_student` | 24,247 | 2,082 | 44 | 44 |
| `fe_pell_share` | 24,125 | 2,075 | 47 | 16 |
| `fe_federal_loan_per_student` | 24,247 | 2,082 | 44 | 44 |
| `fe_weighted_inst_grant` | 24,247 | 2,082 | 44 | 44 |
| `pooled_sector_interaction_inst_grant` | 24,247 | 2,082 | 44 | 44 |
| `syfe_inst_grant_per_student` | 24,247 | 2,082 | 44 | 44 |
| `syfe_inst_grant_share` | 24,125 | 2,075 | 47 | 16 |
| `syfe_pell_per_student` | 24,247 | 2,082 | 44 | 44 |
| `syfe_pell_share` | 24,125 | 2,075 | 47 | 16 |
| `syfe_federal_loan_per_student` | 24,247 | 2,082 | 44 | 44 |
| `syfe_pooled_sector_interaction_inst_grant` | 24,247 | 2,082 | 44 | 44 |
| `fe_net_price_low_income` | 21,296 | 2,025 | 48 | 43 |
| `syfe_net_price_low_income` | 21,296 | 2,025 | 48 | 43 |
| `selectivity_inst_grant` | 15,201 | 1,459 | 51 | 18 |
| `public_inst_grant` | 8,626 | 713 | 13 | 13 |
| `private_np_inst_grant` | 15,621 | 1,371 | 31 | 33 |
| `component_horse_race_inst_grant` | 24,247 | 2,082 | 44 | 96 |
| `public_component_horse_race_inst_grant` | 8,626 | 713 | 13 | 21 |
| `private_np_component_horse_race_inst_grant` | 15,621 | 1,371 | 31 | 76 |
| `sensitivity_min_years_10_inst_grant` | 22,654 | 1,751 | 9 | 14 |
| `sensitivity_balanced_inst_grant` | 20,996 | 1,590 | 7 | 11 |
| `sensitivity_metadata_clean_inst_grant` | 20,311 | 2,041 | 54 | 45 |
| `sensitivity_no_suspect_zero_inst_grant` | 23,222 | 2,078 | 55 | 46 |

All weighted samples have zero nonpositive-weight rows in the current manifest.

## Main missingness sources

For the main institutional-grant dollar model, the source panel has 35,443 rows. The main missingness sources are:

| Variable | Role | Missing rows | Missing share |
| --- | --- | ---: | ---: |
| `IGRNT_PER_FTFT_COHORT` | dependent variable | 5,727 | 16.2% |
| `HEADROOM_MAIN` | focal variable | 9,056 | 25.6% |
| `LN_SCFA1N` | control | 5,712 | 16.1% |
| `LN_FIN_TOTAL_REVENUE` | control | 3,011 | 8.5% |
| `LN_FIN_TOTAL_EXPENSES` | control | 2,883 | 8.1% |
| `LN_FIN_TOTAL_ASSETS` | control | 2,916 | 8.2% |

## What this means for estimation

The model samples feed `scripts/run_fixed_effects.py`. The estimator reports:

- rows and institutions used by each model
- singleton institutions
- institutions without within-institution focal variation
- whether weights are used
- clustering level

The complete-case samples are not committed. They are generated from the committed model specification file and the local analysis panels.

The reviewer-facing attrition table is now generated separately:

```bash
PYTHONPATH=src python scripts/build_reviewer_tables.py
```

It writes `outputs/reviewer_tables/model_sample_attrition.csv`, which gives one row per baseline and policy model with source rows, complete-case rows, rows dropped, retained share, clusters, and the main missingness sources.
