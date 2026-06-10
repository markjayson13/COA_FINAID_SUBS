# Fixed-effects baseline estimates

This note records the first fixed-effects estimates from the materialized model samples. These are baseline association estimates. They are not a policy-shock design and they are not student-level packaging estimates.

Run:

```bash
PYTHONPATH=src python scripts/run_fixed_effects.py \
  --sample-dir outputs/model_samples/samples \
  --output-dir outputs/fixed_effects \
  --config config/model_specifications.csv

PYTHONPATH=src python scripts/validate_fixed_effects_outputs.py \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/baseline_estimation_validation \
  --config config/model_specifications.csv
```

The script writes:

- `outputs/fixed_effects/fixed_effects_coefficients.csv`
- `outputs/fixed_effects/fixed_effects_focal_coefficients.csv`
- `outputs/fixed_effects/fixed_effects_model_diagnostics.csv`
- `outputs/fixed_effects/fixed_effects_summary.json`
- `outputs/baseline_estimation_validation/estimation_validation_summary.json`

Generated outputs remain outside Git. This note records the current local run so the paper trail is visible.

## Estimation rule

Each model uses the complete-case sample already written by `scripts/build_model_samples.py`. The estimator:

- absorbs the fixed effects named in `config/model_specifications.csv`
- uses the focal variable and controls named in `config/model_specifications.csv`
- clusters standard errors by `UNITID`
- uses `SCFA1N` weights only for the configured weighted check
- writes diagnostics for rows, institutions, clusters, singleton clusters, within-focal variation, rank, and absorbed fixed-effect convergence

The main models absorb `UNITID` and `year`. The pooled sector-year checks absorb `UNITID` and `SECTOR_YEAR`, where `SECTOR_YEAR` is the sector-by-calendar-year cell. Those checks ask whether pooled results survive sector-specific time shocks.

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
| `syfe_inst_grant_per_student` | sector-year check | `HEADROOM_MAIN` | 0.1287 | 0.0218 | 5.91 | 24,247 | 2,082 |
| `syfe_pooled_sector_interaction_inst_grant` | sector-year interaction | `HEADROOM_MAIN` | -0.0050 | 0.0144 | -0.34 | 24,247 | 2,082 |
| `syfe_pooled_sector_interaction_inst_grant` | sector-year interaction | `HEADROOM_MAIN_X_PRIVATE_NONPROFIT` | 0.1779 | 0.0319 | 5.57 | 24,247 | 2,082 |
| `fe_net_price_low_income` | secondary | `HEADROOM_MAIN` | 0.4218 | 0.0297 | 14.22 | 21,296 | 2,025 |
| `syfe_net_price_low_income` | sector-year check | `HEADROOM_MAIN` | 0.4194 | 0.0294 | 14.28 | 21,296 | 2,025 |
| `selectivity_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1103 | 0.0308 | 3.59 | 15,201 | 1,459 |
| `public_inst_grant` | sector | `HEADROOM_MAIN` | -0.0058 | 0.0136 | -0.42 | 8,626 | 713 |
| `private_np_inst_grant` | sector | `HEADROOM_MAIN` | 0.1736 | 0.0284 | 6.12 | 15,621 | 1,371 |
| `sensitivity_min_years_10_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1403 | 0.0241 | 5.81 | 22,654 | 1,751 |
| `sensitivity_balanced_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1489 | 0.0257 | 5.80 | 20,996 | 1,590 |
| `sensitivity_metadata_clean_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1262 | 0.0237 | 5.31 | 20,311 | 2,041 |
| `sensitivity_no_suspect_zero_inst_grant` | sensitivity | `HEADROOM_MAIN` | 0.1391 | 0.0237 | 5.86 | 23,222 | 2,078 |

For dollar outcomes, the `HEADROOM_MAIN` coefficient is in outcome dollars per one dollar of published headroom. For share outcomes, the focal variable is measured on a 0 to 1 scale.

## Component check

The component model enters tuition and fees, books, off-campus room and board, and other expenses side by side. It is not the headline model because the research question is about the published non-tuition headroom margin, but it is an important mechanism check.

| Model | Component | Estimate | SE | t | N | Clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `component_horse_race_inst_grant` | `CHG2AY0` tuition and fees | 0.6975 | 0.0256 | 27.25 | 24,247 | 2,082 |
| `component_horse_race_inst_grant` | `CHG4AY0` books and supplies | -0.1032 | 0.1025 | -1.01 | 24,247 | 2,082 |
| `component_horse_race_inst_grant` | `CHG7AY0` off-campus room and board | 0.0271 | 0.0211 | 1.28 | 24,247 | 2,082 |
| `component_horse_race_inst_grant` | `CHG8AY0` other expenses | -0.0407 | 0.0304 | -1.34 | 24,247 | 2,082 |
| `public_component_horse_race_inst_grant` | `CHG7AY0` off-campus room and board | -0.0085 | 0.0159 | -0.54 | 8,626 | 713 |
| `private_np_component_horse_race_inst_grant` | `CHG7AY0` off-campus room and board | 0.0571 | 0.0279 | 2.05 | 15,621 | 1,371 |

This check changes the mechanism language. The aggregate headroom result is a useful association, but the side-by-side component model shows that tuition and fees carry much of the institutional-grant movement when components are entered together. The paper should therefore describe grant substitution as a hypothesis or interpretation, not as a settled mechanism from the baseline fixed-effects model.

## Diagnostics from the current run

All 25 planned baseline, sector-year, component, and sensitivity models estimated. No model was rank deficient, and the baseline validation reported zero issues.

| Model | Singleton clusters | Groups without focal within variation | Within R-squared |
| --- | ---: | ---: | ---: |
| `fe_inst_grant_per_student` | 44 | 44 | 0.0151 |
| `fe_inst_grant_share` | 47 | 16 | 0.0089 |
| `fe_pell_per_student` | 44 | 44 | 0.0011 |
| `fe_pell_share` | 47 | 16 | 0.0116 |
| `fe_federal_loan_per_student` | 44 | 44 | 0.0017 |
| `fe_weighted_inst_grant` | 44 | 44 | 0.0227 |
| `pooled_sector_interaction_inst_grant` | 44 | 44 | 0.1036 |
| `syfe_inst_grant_per_student` | 44 | 44 | 0.0168 |
| `syfe_pooled_sector_interaction_inst_grant` | 44 | 44 | 0.0198 |
| `fe_net_price_low_income` | 48 | 43 | 0.0595 |
| `syfe_net_price_low_income` | 48 | 43 | 0.0591 |
| `selectivity_inst_grant` | 51 | 18 | 0.0135 |
| `public_inst_grant` | 13 | 13 | 0.0067 |
| `private_np_inst_grant` | 31 | 33 | 0.0233 |
| `component_horse_race_inst_grant` | 44 | 96 | 0.4501 |
| `sensitivity_min_years_10_inst_grant` | 9 | 14 | 0.0158 |
| `sensitivity_balanced_inst_grant` | 7 | 11 | 0.0155 |
| `sensitivity_metadata_clean_inst_grant` | 54 | 45 | 0.0140 |
| `sensitivity_no_suspect_zero_inst_grant` | 55 | 46 | 0.0160 |

The low within R-squared values are expected for institution fixed-effects models with year effects and noisy aid outcomes. They do not invalidate the estimates, but the paper should not overstate fit.

## Paper-use boundary

The main table should report the public and private nonprofit estimates separately, then show the pooled baseline and the pooled interaction as reference checks. The current results point to different sector patterns: the public-sector estimate is near zero in the sector-specific model, while the private nonprofit estimate is positive. The pooled interaction uses common control coefficients and should not replace the sector-specific estimates.

The sector-year pooled interaction is more consistent with the sector-specific models than the plain pooled interaction. With sector-by-year fixed effects, the public slope is near zero and the private nonprofit difference is positive. That is a stronger check than the original pooled interaction because it absorbs sector-specific time shocks.

The refreshed public-sector FE specification excludes raw `FIN_STATE_LOCAL_APPROPS_PUBLIC`. The variable remains in the analysis panel for descriptive and diagnostic work, but its raw dollar level caused unstable absorbed fixed-effect estimation when used as a default control.

The baseline validation now reports zero estimation issues across all 25 configured models. The focal coefficients for all 25 baseline, sector-year, component, and sensitivity models were cross-checked against `linearmodels.PanelOLS`. The comparison found zero failures. The largest absolute coefficient difference was `3.69e-12`; the largest absolute standard-error difference was `1.85e-05`.

`scripts/build_estimate_tables.py` now exports split fixed-effects tables to CSV, Markdown, LaTeX, and Word under `outputs/estimate_tables/`.
