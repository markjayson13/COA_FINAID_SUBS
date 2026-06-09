# Fixed-effects baseline estimates

This note records the first fixed-effects estimates from the materialized model samples. These are baseline association estimates. They are not a policy-shock design and they are not student-level packaging estimates.

Run:

```bash
PYTHONPATH=src python scripts/run_fixed_effects.py \
  --sample-dir outputs/model_samples/samples \
  --output-dir outputs/fixed_effects \
  --config config/model_specifications.csv
```

The script writes:

- `outputs/fixed_effects/fixed_effects_coefficients.csv`
- `outputs/fixed_effects/fixed_effects_focal_coefficients.csv`
- `outputs/fixed_effects/fixed_effects_model_diagnostics.csv`
- `outputs/fixed_effects/fixed_effects_summary.json`

Generated outputs remain outside Git. This note records the current local run so the paper trail is visible.

## Estimation rule

Each model uses the complete-case sample already written by `scripts/build_model_samples.py`. The estimator:

- absorbs `UNITID` and `year`
- uses the focal variable and controls named in `config/model_specifications.csv`
- clusters standard errors by `UNITID`
- uses `SCFA1N` weights only for the configured weighted check
- writes diagnostics for rows, institutions, clusters, singleton clusters, within-focal variation, rank, and absorbed fixed-effect convergence

The p-values are normal-reference p-values from the clustered standard errors. The paper should treat them as table output, not as the main claim.

## Current key coefficients

| Model | Role | Focal variable | Estimate | SE | t | N | Clusters |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `fe_inst_grant_per_student` | main | `HEADROOM_MAIN` | 0.1314 | 0.0232 | 5.67 | 24,247 | 2,082 |
| `fe_inst_grant_share` | main | `HEADROOM_MAIN_SHARE_COA` | -0.2230 | 0.0437 | -5.11 | 24,125 | 2,075 |
| `fe_pell_per_student` | secondary | `HEADROOM_MAIN` | 0.0044 | 0.0041 | 1.08 | 24,247 | 2,082 |
| `fe_pell_share` | secondary | `HEADROOM_MAIN_SHARE_COA` | 0.2116 | 0.0379 | 5.58 | 24,125 | 2,075 |
| `fe_federal_loan_per_student` | secondary | `HEADROOM_MAIN` | 0.0072 | 0.0060 | 1.21 | 24,247 | 2,082 |
| `fe_weighted_inst_grant` | weight check | `HEADROOM_MAIN` | 0.1160 | 0.0341 | 3.40 | 24,247 | 2,082 |
| `pooled_sector_interaction_inst_grant` | sector interaction | `HEADROOM_MAIN` | -0.4371 | 0.0316 | -13.85 | 24,247 | 2,082 |
| `pooled_sector_interaction_inst_grant` | sector interaction | `HEADROOM_MAIN_X_PRIVATE_NONPROFIT` | 0.7586 | 0.0380 | 19.99 | 24,247 | 2,082 |
| `fe_net_price_low_income` | secondary | `HEADROOM_MAIN` | 0.4218 | 0.0297 | 14.22 | 21,296 | 2,025 |
| `selectivity_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1103 | 0.0308 | 3.59 | 15,201 | 1,459 |
| `public_inst_grant` | sector | `HEADROOM_MAIN` | -0.0046 | 0.0138 | -0.33 | 8,626 | 713 |
| `private_np_inst_grant` | sector | `HEADROOM_MAIN` | 0.1736 | 0.0284 | 6.12 | 15,621 | 1,371 |
| `sensitivity_min_years_10_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1403 | 0.0241 | 5.81 | 22,654 | 1,751 |
| `sensitivity_balanced_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1489 | 0.0257 | 5.80 | 20,996 | 1,590 |
| `sensitivity_metadata_clean_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1262 | 0.0237 | 5.31 | 20,311 | 2,041 |
| `sensitivity_no_suspect_zero_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1391 | 0.0237 | 5.86 | 23,222 | 2,078 |

For dollar outcomes, the `HEADROOM_MAIN` coefficient is in outcome dollars per one dollar of published headroom. For share outcomes, the focal variable is measured on a 0 to 1 scale.

## Diagnostics from the current run

All 15 planned models estimated and no model was rank deficient.

| Model | Singleton clusters | Groups without focal within variation | Within R-squared |
| --- | ---: | ---: | ---: |
| `fe_inst_grant_per_student` | 44 | 44 | 0.0151 |
| `fe_inst_grant_share` | 47 | 16 | 0.0089 |
| `fe_pell_per_student` | 44 | 44 | 0.0011 |
| `fe_pell_share` | 47 | 16 | 0.0116 |
| `fe_federal_loan_per_student` | 44 | 44 | 0.0017 |
| `fe_weighted_inst_grant` | 44 | 44 | 0.0227 |
| `pooled_sector_interaction_inst_grant` | 44 | 44 | 0.1036 |
| `fe_net_price_low_income` | 48 | 43 | 0.0595 |
| `selectivity_inst_grant` | 51 | 18 | 0.0135 |
| `public_inst_grant` | 13 | 13 | 0.0081 |
| `private_np_inst_grant` | 31 | 33 | 0.0233 |
| `sensitivity_min_years_10_inst_grant` | 9 | 14 | 0.0158 |
| `sensitivity_balanced_inst_grant` | 7 | 11 | 0.0155 |
| `sensitivity_metadata_clean_inst_grant` | 54 | 45 | 0.0140 |
| `sensitivity_no_suspect_zero_inst_grant` | 55 | 46 | 0.0160 |

The low within R-squared values are expected for institution fixed-effects models with year effects and noisy aid outcomes. They do not invalidate the estimates, but the paper should not overstate fit.

## Paper-use boundary

The main table should report the public and private nonprofit estimates separately, then show the pooled baseline and the pooled interaction as reference checks. The current results point to different sector patterns: the public-sector estimate is near zero in the sector-specific model, while the private nonprofit estimate is positive. The pooled interaction uses common control coefficients and should not replace the sector-specific estimates.

`scripts/build_estimate_tables.py` now exports the current fixed-effects table to CSV, LaTeX, and Word under `outputs/estimate_tables/`.
