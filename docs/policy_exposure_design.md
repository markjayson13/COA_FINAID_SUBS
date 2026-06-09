# Policy exposure design

This note documents the policy-exposure designs. They are separate from the baseline fixed-effects estimates.

## Design 1: year-round Pell restoration

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
- event-year interactions from 2014 through 2023, with 2016 omitted

The placebo check is a pre-trend diagnostic. A sharp placebo coefficient means the policy-exposure design is detecting differential movement before the 2017 policy event.

The event-study specification estimates exposure-by-year interactions in one model. The omitted year is 2016, the last pre-restoration year. The 2014 and 2015 coefficients are lead checks; the 2017-2023 coefficients are post-restoration dynamics. The event-study table is diagnostic unless the lead coefficients support the parallel-trend story for the outcome.

## Why this design comes before estimation

The Pell schedule is national, so year fixed effects absorb the national policy timing. The estimable object is differential change by pre-period exposure:

```text
Outcome_it = institution fixed effects + year fixed effects
           + beta(Pell exposure_i x Post 2017_t)
           + controls_it + error_it
```

Event-study form:

```text
Outcome_it = institution fixed effects + year fixed effects
           + sum over k != 2016 beta_k(Pell exposure_i x 1[year = k])
           + controls_it + error_it
```

The coefficient does not say that the policy changed one institution and not another. It compares institutions with different pre-period Pell exposure before and after the national policy change.

## Design 2: annual maximum Pell changes

The second design uses annual changes in the maximum Pell Grant award. The maximum award is set nationally, so the design again requires pre-period institution exposure. The main estimating variable is:

```text
PELL_EXPOSURE_PRE2017_Z_X_PELL_MAX_AWARD_REAL_DELTA_100
```

This is the institution's 2014-2016 Pell-exposure z-score, standardized within pre-period sector, multiplied by the annual change in the maximum Pell award measured in hundreds of 2023 dollars.

The panel also writes two checks:

```text
PELL_EXPOSURE_PRE2017_Z_X_PELL_MAX_AWARD_DELTA_100
PELL_EXPOSURE_PRE2017_Z_X_PELL_LARGE_INCREASE
```

The first uses nominal maximum Pell changes. The second uses the large-increase flag in the Pell schedule registry. The real-dollar version is preferred because nominal increases can mix policy generosity with inflation.

The pre-period placebo variables are:

```text
PELL_EXPOSURE_PRE2016_Z_X_PELL_MAX_AWARD_REAL_DELTA_100
PELL_EXPOSURE_PRE2016_Z_X_PELL_MAX_AWARD_DELTA_100
```

These use 2014-2015 Pell exposure and 2014-2016 rows. A sharp placebo coefficient means high- and low-exposure institutions were already moving differently before the later post-2017 period.

The real-dollar conversion uses `config/policy_price_index.csv`, which records CPI-U annual averages and expresses Pell awards in 2023 dollars.

## Files

- `config/policy_exposure_designs.csv` defines the event window and pre-period rule.
- `config/policy_exposure_model_specifications.csv` defines the first policy-exposure models.
- `config/policy_price_index.csv` defines the CPI-U annual averages used for real maximum Pell awards.
- `scripts/build_policy_exposure_panels.py` writes the exposure panels and audit files.
- `scripts/build_policy_event_study_table.py` writes the event-study coefficient table after policy fixed-effects models are run.
- `src/coa_finaid_subs/policy_exposures.py` contains the exposure construction.
- `scripts/validate_fixed_effects_outputs.py` checks estimation outputs for numerical and placebo-design problems.

Generated files are written under `outputs/policy_exposure/` and are not committed.

## Estimation boundary

These models are policy-exposure estimates, not the baseline headroom association estimates. They should be reported after the descriptive and baseline fixed-effects tables, and they should not replace the sector-specific baseline estimates.
