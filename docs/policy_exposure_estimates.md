# Policy exposure estimates

This note records the first policy-exposure estimates. These are separate from the baseline fixed-effects estimates in `docs/fixed_effects_baseline.md`.

## Run

```bash
PYTHONPATH=src python scripts/build_policy_exposure_panels.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/policy_exposure \
  --policy-config config/policy_shocks.csv \
  --design-config config/policy_exposure_designs.csv \
  --price-index-config config/policy_price_index.csv

PYTHONPATH=src python scripts/audit_model_plan.py \
  --panel-dir outputs/policy_exposure \
  --output-dir outputs/policy_model_plan \
  --config config/policy_exposure_model_specifications.csv

PYTHONPATH=src python scripts/build_model_samples.py \
  --panel-dir outputs/policy_exposure \
  --output-dir outputs/policy_model_samples \
  --config config/policy_exposure_model_specifications.csv

PYTHONPATH=src python scripts/run_fixed_effects.py \
  --sample-dir outputs/policy_model_samples/samples \
  --output-dir outputs/policy_fixed_effects \
  --config config/policy_exposure_model_specifications.csv

PYTHONPATH=src python scripts/build_policy_event_study_table.py \
  --fixed-effects-dir outputs/policy_fixed_effects \
  --output-dir outputs/policy_event_study

PYTHONPATH=src python scripts/validate_fixed_effects_outputs.py \
  --fixed-effects-dir outputs/policy_fixed_effects \
  --output-dir outputs/policy_estimation_validation \
  --config config/policy_exposure_model_specifications.csv
```

## Exposure gate

The exposure build passed with zero issues.

| Scope | Rows | Institutions | 2014-2023 rows | 2014-2023 institutions | Exposure institutions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Public and private nonprofit | 35,443 | 2,774 | 23,883 | 2,682 | 1,983 |
| Public | 11,215 | 882 | 7,711 | 865 | 680 |
| Private nonprofit | 24,228 | 1,903 | 16,172 | 1,825 | 1,303 |

The model-plan audit found zero missing model variables across 43 policy-exposure specifications.

## Estimates

The focal variable is:

```text
PELL_EXPOSURE_PRE2017_Z_X_POST_YRP_2017
```

It is the 2014-2016 Pell-share exposure, standardized within pre-period sector, interacted with an indicator for 2017 or later. Coefficients are interpreted as differential post-2017 changes for a one-standard-deviation higher pre-period Pell exposure.

| Model | Outcome | Estimate | SE | t | N | Clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `yrp2017_headroom` | `HEADROOM_MAIN` | -175.69 | 53.78 | -3.27 | 16,694 | 1,808 |
| `syfe_yrp2017_headroom` | `HEADROOM_MAIN` | -171.30 | 54.22 | -3.16 | 16,694 | 1,808 |
| `yrp2017_headroom_share` | `HEADROOM_MAIN_SHARE_COA` | 0.0013 | 0.0012 | 1.08 | 16,694 | 1,808 |
| `yrp2017_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -1,245.91 | 53.90 | -23.12 | 17,734 | 1,862 |
| `syfe_yrp2017_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -1,146.47 | 47.90 | -23.94 | 17,734 | 1,862 |
| `yrp2017_pell` | `PGRNT_PER_FTFT_COHORT` | 28.92 | 18.05 | 1.60 | 17,734 | 1,862 |
| `yrp2017_federal_loan` | `FLOAN_PER_FTFT_COHORT` | 36.65 | 20.98 | 1.75 | 17,734 | 1,862 |
| `public_yrp2017_headroom` | `HEADROOM_MAIN` | -40.40 | 67.92 | -0.59 | 5,854 | 603 |
| `private_np_yrp2017_headroom` | `HEADROOM_MAIN` | -268.49 | 77.31 | -3.47 | 10,836 | 1,205 |

The `syfe_` models absorb institution fixed effects and sector-by-year fixed effects. These checks ask whether the pooled policy-exposure result depends on sector-specific time shocks. All 43 models estimated without rank deficiency.

## Maximum Pell repeated-shock design

The second policy design uses annual changes in the maximum Pell Grant award. The preferred focal variable is:

```text
PELL_EXPOSURE_PRE2017_Z_X_PELL_MAX_AWARD_REAL_DELTA_100
```

It is the 2014-2016 Pell-share exposure, standardized within pre-period sector, multiplied by the annual change in the maximum Pell award measured in hundreds of 2023 dollars.

| Model | Outcome | Estimate | SE | t | N | Clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `max_pell_real_headroom` | `HEADROOM_MAIN` | 4.17 | 8.85 | 0.47 | 16,694 | 1,808 |
| `syfe_max_pell_real_headroom` | `HEADROOM_MAIN` | 3.52 | 8.83 | 0.40 | 16,694 | 1,808 |
| `max_pell_real_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -68.36 | 9.00 | -7.59 | 17,734 | 1,862 |
| `syfe_max_pell_real_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -59.34 | 9.06 | -6.55 | 17,734 | 1,862 |
| `max_pell_real_pell` | `PGRNT_PER_FTFT_COHORT` | 12.73 | 6.63 | 1.92 | 17,734 | 1,862 |
| `max_pell_real_federal_loan` | `FLOAN_PER_FTFT_COHORT` | 18.81 | 7.29 | 2.58 | 17,734 | 1,862 |

The real maximum-Pell headroom result is not statistically sharp. The institutional-grant result is sharp, but it is not causal-ready because the maximum-Pell institutional-grant placebo check is also sharp.

Two checks are useful:

| Model | Outcome | Estimate | SE | t | N | Clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `max_pell_nominal_headroom` | `HEADROOM_MAIN` | -74.86 | 17.44 | -4.29 | 16,694 | 1,808 |
| `max_pell_nominal_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -410.92 | 18.68 | -22.00 | 17,734 | 1,862 |
| `max_pell_large_increase_headroom` | `HEADROOM_MAIN` | -210.16 | 47.59 | -4.42 | 16,694 | 1,808 |
| `max_pell_placebo_headroom` | `HEADROOM_MAIN` | 32.07 | 37.58 | 0.85 | 4,921 | 1,722 |
| `max_pell_placebo_inst_grant` | `IGRNT_PER_FTFT_COHORT` | 127.80 | 26.30 | 4.86 | 5,405 | 1,810 |

The nominal and large-increase headroom checks are sharper than the real maximum-Pell headroom model. That pattern should be treated cautiously because nominal Pell increases partly track inflation. The real-dollar specification is the cleaner policy-intensity measure.

## Event-study diagnostics

The event-study specification uses 2016 as the omitted year. The 2014 and 2015 coefficients are pre-period lead checks.

| Model | Outcome | 2014 | 2015 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `yrp2017_event_headroom` | `HEADROOM_MAIN` | 64.71 | 26.90 | 61.75 | -46.23 | -106.48 | -150.70 | -254.08 | -308.96 | -295.52 |
| `syfe_yrp2017_event_headroom` | `HEADROOM_MAIN` | 61.61 | 23.97 | 61.70 | -42.61 | -103.24 | -145.44 | -249.26 | -310.05 | -297.84 |
| `yrp2017_event_inst_grant` | `IGRNT_PER_FTFT_COHORT` | 449.01 | 237.30 | -243.36 | -587.28 | -847.76 | -1,058.25 | -1,396.37 | -1,461.98 | -1,878.44 |
| `syfe_yrp2017_event_inst_grant` | `IGRNT_PER_FTFT_COHORT` | 442.36 | 228.67 | -205.94 | -533.28 | -776.25 | -976.97 | -1,262.63 | -1,347.24 | -1,694.90 |

The headroom leads are not statistically sharp. The original event-study has `t = 1.17` for 2014 and `t = 0.71` for 2015; the sector-year version has `t = 1.11` for 2014 and `t = 0.63` for 2015. The institutional-grant leads are sharp before the 2017 restoration. The original event-study has `t = 14.34` for 2014 and `t = 10.45` for 2015; the sector-year version has `t = 14.87` for 2014 and `t = 10.67` for 2015. This reinforces the placebo result. The institutional-grant event-study path should be treated as evidence of different pre-existing trajectories, not as a causal year-round Pell effect.

## Sensitivity and placebo checks

| Model | Outcome | Estimate | SE | t | N | Clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `yrp2017_headroom_pell_dollars_exposure` | `HEADROOM_MAIN` | -163.75 | 43.81 | -3.74 | 16,737 | 1,816 |
| `yrp2017_inst_grant_pell_dollars_exposure` | `IGRNT_PER_FTFT_COHORT` | -1,022.53 | 58.91 | -17.36 | 17,779 | 1,870 |
| `yrp2017_headroom_pre3` | `HEADROOM_MAIN` | -174.11 | 54.39 | -3.20 | 16,350 | 1,740 |
| `yrp2017_inst_grant_pre3` | `IGRNT_PER_FTFT_COHORT` | -1,275.03 | 55.28 | -23.07 | 17,337 | 1,790 |
| `yrp2017_headroom_no_2020_2021` | `HEADROOM_MAIN` | -161.74 | 51.11 | -3.16 | 13,370 | 1,808 |
| `yrp2017_inst_grant_no_2020_2021` | `IGRNT_PER_FTFT_COHORT` | -1,183.88 | 50.28 | -23.55 | 14,263 | 1,862 |
| `placebo2016_headroom` | `HEADROOM_MAIN` | -47.12 | 41.19 | -1.14 | 4,921 | 1,722 |
| `syfe_placebo2016_headroom` | `HEADROOM_MAIN` | -46.15 | 41.20 | -1.12 | 4,921 | 1,722 |
| `placebo2016_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -267.39 | 27.41 | -9.75 | 5,405 | 1,810 |
| `syfe_placebo2016_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -268.00 | 26.82 | -9.99 | 5,405 | 1,810 |

The headroom result is stable across the alternative Pell-dollar exposure, the three-year pre-period sample, and the no-2020/2021 sample. The 2016 headroom placebo is not statistically sharp.

The institutional-grant policy estimate is not clean causal evidence at this stage. The 2016 placebo institutional-grant check is large and statistically sharp, which means the model detects differential institutional-grant movement before the 2017 year-round Pell restoration. The paper can report this as a diagnostic, but it should not use the institutional-grant policy coefficient as a main causal estimate without a tighter design.

## Validation

The numerical validation checks pass when placebo-signal checks are skipped:

```text
43 models observed
0 rank-deficient models
0 convergence issues
0 tiny focal standard errors
0 insufficient-cluster issues
```

The hard validation fails three design checks:

| Model | Check | Detail |
| --- | --- | --- |
| `placebo2016_inst_grant` | `placebo_signal` | `PELL_EXPOSURE_PRE2016_Z_X_POST_PLACEBO_2016: t_stat=-9.75` |
| `syfe_placebo2016_inst_grant` | `placebo_signal` | `PELL_EXPOSURE_PRE2016_Z_X_POST_PLACEBO_2016: t_stat=-9.99` |
| `max_pell_placebo_inst_grant` | `placebo_signal` | `PELL_EXPOSURE_PRE2016_Z_X_PELL_MAX_AWARD_REAL_DELTA_100: t_stat=4.86` |

## Notes

The public-sector policy model excludes `FIN_STATE_LOCAL_APPROPS_PUBLIC`. In the 2014-2023 event window, that raw public finance control prevented stable fixed-effect absorption and produced unusable clustered standard errors. The baseline public-sector model was refreshed to exclude the same raw control from the default FE specification.

Within R-squared is low in these models because they absorb institution and year fixed effects and estimate differential changes around a national policy event. The paper should report the coefficients with the design boundary, not as a student-level packaging estimate.
