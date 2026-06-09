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
```

## Exposure gate

The exposure build passed with zero issues.

| Scope | Rows | Institutions | 2014-2023 rows | 2014-2023 institutions | Exposure institutions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Public and private nonprofit | 35,443 | 2,774 | 23,883 | 2,682 | 2,004 |
| Public | 11,215 | 882 | 7,711 | 865 | 681 |
| Private nonprofit | 24,228 | 1,903 | 16,172 | 1,825 | 1,323 |

The model-plan audit found zero missing model variables across seven policy-exposure specifications.

## Estimates

The focal variable is:

```text
PELL_EXPOSURE_PRE2017_Z_X_POST_YRP_2017
```

It is the 2014-2016 Pell-share exposure, standardized within pre-period sector, interacted with an indicator for 2017 or later. Coefficients are interpreted as differential post-2017 changes for a one-standard-deviation higher pre-period Pell exposure.

| Model | Outcome | Estimate | SE | t | N | Clusters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `yrp2017_headroom` | `HEADROOM_MAIN` | -171.47 | 53.71 | -3.19 | 16,762 | 1,823 |
| `yrp2017_headroom_share` | `HEADROOM_MAIN_SHARE_COA` | 0.0013 | 0.0012 | 1.13 | 16,762 | 1,823 |
| `yrp2017_inst_grant` | `IGRNT_PER_FTFT_COHORT` | -1,257.87 | 53.95 | -23.31 | 17,814 | 1,878 |
| `yrp2017_pell` | `PGRNT_PER_FTFT_COHORT` | 30.13 | 18.12 | 1.66 | 17,814 | 1,878 |
| `yrp2017_federal_loan` | `FLOAN_PER_FTFT_COHORT` | 36.57 | 21.00 | 1.74 | 17,814 | 1,878 |
| `public_yrp2017_headroom` | `HEADROOM_MAIN` | -40.40 | 67.92 | -0.59 | 5,854 | 603 |
| `private_np_yrp2017_headroom` | `HEADROOM_MAIN` | -262.34 | 77.38 | -3.39 | 10,904 | 1,220 |

All seven models estimated without rank deficiency.

## Notes

The public-sector policy model excludes `FIN_STATE_LOCAL_APPROPS_PUBLIC`. In the 2014-2023 event window, that raw public finance control prevented stable fixed-effect absorption and produced unusable clustered standard errors. The baseline public-sector model still keeps the public appropriations control.

Within R-squared is low in these models because they absorb institution and year fixed effects and estimate differential changes around a national policy event. The paper should report the coefficients with the design boundary, not as a student-level packaging estimate.
