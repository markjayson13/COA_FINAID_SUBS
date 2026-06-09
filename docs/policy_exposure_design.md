# Policy exposure design

This note documents the first policy-exposure design. It is separate from the baseline fixed-effects estimates.

## Design

The first design uses the 2017-2018 restoration of year-round Pell Grants. The national policy change is recorded in `config/policy_shocks.csv`. The institution-level exposure is measured before the change.

Pre-period:

```text
2014, 2015, 2016
```

Post-period:

```text
2017 through 2023
```

Main exposure:

```text
PELL_EXPOSURE_PRE2017
```

This is the institution's mean pre-2017 Pell share of FTFT grant dollars:

```text
mean(PELL_SHARE_OF_TOTAL_GRANT_FTFT), 2014-2016
```

The model uses `PELL_EXPOSURE_PRE2017_Z_SECTOR`, which standardizes that pre-period measure within the institution's pre-period sector. Institutions need at least two observed pre-period years to receive a standardized exposure value.

Main interaction:

```text
PELL_EXPOSURE_PRE2017_Z_X_POST_YRP_2017
```

This equals the standardized pre-period Pell exposure multiplied by an indicator for 2017 or later.

## Sensitivity checks

The first sensitivity set adds:

- an alternative exposure based on pre-2017 Pell dollars per FTFT student
- a sample requiring all three pre-period exposure years
- a sample that excludes 2020 and 2021
- a 2016 placebo check using 2014-2015 Pell exposure

The placebo check is a pre-trend diagnostic. A sharp placebo coefficient means the policy-exposure design is detecting differential movement before the 2017 policy event.

## Why this design comes before estimation

The Pell schedule is national, so year fixed effects absorb the national policy timing. The estimable object is differential change by pre-period exposure:

```text
Outcome_it = institution fixed effects + year fixed effects
           + beta(Pell exposure_i x Post 2017_t)
           + controls_it + error_it
```

The coefficient does not say that the policy changed one institution and not another. It compares institutions with different pre-period Pell exposure before and after the national policy change.

## Files

- `config/policy_exposure_designs.csv` defines the event window and pre-period rule.
- `config/policy_exposure_model_specifications.csv` defines the first policy-exposure models.
- `scripts/build_policy_exposure_panels.py` writes the exposure panels and audit files.
- `src/coa_finaid_subs/policy_exposures.py` contains the exposure construction.
- `scripts/validate_fixed_effects_outputs.py` checks estimation outputs for numerical and placebo-design problems.

Generated files are written under `outputs/policy_exposure/` and are not committed.

## Estimation boundary

These models are policy-exposure estimates, not the baseline headroom association estimates. They should be reported after the descriptive and baseline fixed-effects tables, and they should not replace the sector-specific baseline estimates.
