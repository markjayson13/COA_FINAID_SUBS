# Policy exposure estimates

This note records the first policy-exposure estimates. These are separate from the baseline fixed-effects estimates in `docs/fixed_effects_baseline.md`.

## Run

```bash
PYTHONPATH=src python scripts/build_policy_exposure_panels.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/policy_exposure \
  --policy-config config/policy_shocks.csv \
  --design-config config/policy_exposure_designs.csv

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

The model-plan audit found zero missing model variables across 17 policy-exposure specifications.

## Estimates

The focal variable is:

```text
PELL_EXPOSURE_PRE2017_Z_X_POST_YRP_2017
```

It is the 2014-2016 Pell-share exposure, standardized within pre-period sector, interacted with an indicator for 2017 or later. Coefficients are interpreted as differential post-2017 changes for a one-standard-deviation higher pre-period Pell exposure.

| Model | Outcome | Estimate | SE | t | N | Clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `yrp2017_headroom` | `HEADROOM_MAIN` | -175.69 | 53.78 | -3.27 | 16,694 | 1,808 |
| `yrp2017_headroom_share` | `HEADROOM_MAIN_SHARE_COA` | 0.0013 | 0.0012 | 1.08 | 16,694 | 1,808 |
| `yrp2017_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -1,245.91 | 53.90 | -23.12 | 17,734 | 1,862 |
| `yrp2017_pell` | `PGRNT_PER_FTFT_COHORT` | 28.92 | 18.05 | 1.60 | 17,734 | 1,862 |
| `yrp2017_federal_loan` | `FLOAN_PER_FTFT_COHORT` | 36.65 | 20.98 | 1.75 | 17,734 | 1,862 |
| `public_yrp2017_headroom` | `HEADROOM_MAIN` | -40.40 | 67.92 | -0.59 | 5,854 | 603 |
| `private_np_yrp2017_headroom` | `HEADROOM_MAIN` | -268.49 | 77.31 | -3.47 | 10,836 | 1,205 |

All 17 models estimated without rank deficiency.

## Event-study diagnostics

The event-study specification uses 2016 as the omitted year. The 2014 and 2015 coefficients are pre-period lead checks.

| Outcome | 2014 | 2015 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `HEADROOM_MAIN` | 64.71 | 26.90 | 61.75 | -46.23 | -106.48 | -150.70 | -254.08 | -308.96 | -295.52 |
| `IGRNT_PER_FTFT_COHORT` | 449.01 | 237.30 | -243.36 | -587.28 | -847.76 | -1,058.25 | -1,396.37 | -1,461.98 | -1,878.44 |

The headroom leads are not statistically sharp: 2014 has `t = 1.17`, and 2015 has `t = 0.71`. The institutional-grant leads are sharp before the 2017 restoration: 2014 has `t = 14.34`, and 2015 has `t = 10.45`. This reinforces the placebo result. The institutional-grant event-study path should be treated as evidence of different pre-existing trajectories, not as a causal year-round Pell effect.

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
| `placebo2016_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -267.39 | 27.41 | -9.75 | 5,405 | 1,810 |

The headroom result is stable across the alternative Pell-dollar exposure, the three-year pre-period sample, and the no-2020/2021 sample. The 2016 headroom placebo is not statistically sharp.

The institutional-grant policy estimate is not clean causal evidence at this stage. The 2016 placebo institutional-grant check is large and statistically sharp, which means the model detects differential institutional-grant movement before the 2017 year-round Pell restoration. The paper can report this as a diagnostic, but it should not use the institutional-grant policy coefficient as a main causal estimate without a tighter design.

## Validation

The numerical validation checks pass when placebo-signal checks are skipped:

```text
17 models observed
0 rank-deficient models
0 convergence issues
0 tiny focal standard errors
0 insufficient-cluster issues
```

The hard validation fails one design check:

| Model | Check | Detail |
| --- | --- | --- |
| `placebo2016_inst_grant` | `placebo_signal` | `PELL_EXPOSURE_PRE2016_Z_X_POST_PLACEBO_2016: t_stat=-9.75` |

## Notes

The public-sector policy model excludes `FIN_STATE_LOCAL_APPROPS_PUBLIC`. In the 2014-2023 event window, that raw public finance control prevented stable fixed-effect absorption and produced unusable clustered standard errors. The baseline public-sector model was refreshed to exclude the same raw control from the default FE specification.

Within R-squared is low in these models because they absorb institution and year fixed effects and estimate differential changes around a national policy event. The paper should report the coefficients with the design boundary, not as a student-level packaging estimate.
