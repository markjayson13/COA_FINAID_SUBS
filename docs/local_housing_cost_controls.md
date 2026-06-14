# Local housing-cost controls

This note documents the local housing-cost control layer for a later robustness version of the project. It does not change the baseline WEAI estimates.

## Why HUD Fair Market Rent

The baseline paper already absorbs institution fixed effects and year fixed effects. Those fixed effects handle time-invariant local differences and national price movement. They do not absorb local housing-cost shocks that vary over time within a county or metro housing market.

HUD Fair Market Rent is a better match than a state-level CPI series for this specific concern because the relevant COA component is housing and living allowance, not the full consumption basket. State CPI or regional CPI is broader, coarser, and often unavailable at county detail. HUD FMR is not a perfect institutional-cost measure, but it is closer to the housing channel that can move non-tuition cost-of-attendance budgets.

This control should remain a robustness check. If local rents are part of the pathway through which published non-tuition COA changes, controlling for them can remove part of the mechanism. The paper should therefore report the baseline estimates first and then show whether the sector estimates survive after adding a local housing-cost control.

## Source

HUD publishes historical Fair Market Rent files at:

```text
https://www.huduser.gov/portal/datasets/fmr.html
```

The two-bedroom historical file used by this repository is:

```text
https://www.huduser.gov/portal/datasets/FMR/FMR_2Bed_1983_2026.csv
```

The scripts keep the downloaded file outside Git under:

```text
data/external/hud_fmr/FMR_2Bed_1983_2026.csv
```

## Build commands

Try the downloader first:

```bash
python scripts/download_hud_fmr.py
```

HUD sometimes serves an access challenge to command-line clients. If that happens, download the CSV in a browser from the HUD page above, place it at `data/external/hud_fmr/FMR_2Bed_1983_2026.csv`, and run:

```bash
python scripts/build_local_housing_controls.py
```

If you downloaded the annual county-level Excel files instead, keep them together in one folder and point the builder at that folder:

```bash
python scripts/build_local_housing_controls.py --raw-fmr-dir "/path/to/FMR"
```

The build command normalizes the HUD file, keeps 2009-2023, and merges county-year FMR to the baseline public and private nonprofit analysis panel. The builder enforces two merge-quality gates by default: at least 99 percent of analysis rows must match a HUD FMR value, and every sector-year cell must have at least a 95 percent match rate. It also fails if any requested year is missing or duplicated in the annual-file folder.

After the merge passes, run the companion estimates:

```bash
python scripts/build_fmr_control_estimates.py
```

This command does not edit the baseline model specifications. It reads the configured fixed-effects and policy-diagnostic model samples, appends log HUD two-bedroom FMR only for the companion run, and writes comparison files against the existing estimates.

## Outputs

The build writes these generated files under `outputs/local_housing_controls/`:

- `hud_fmr_2br_2009_2023.csv`
- `hud_fmr_duplicate_county_year_rows_2009_2023.csv`
- `hud_fmr_summary.json`
- `hud_fmr_source_files_2009_2023.csv`
- `local_housing_controls_hud_fmr_2br_2009_2023_public_private_nonprofit.parquet`
- `analysis_panel_with_hud_fmr_2br_2009_2023_public_private_nonprofit.parquet`
- `hud_fmr_merge_audit_public_private_nonprofit.csv`
- `hud_fmr_unmatched_rows_public_private_nonprofit.csv`
- `hud_fmr_multi_match_rows_public_private_nonprofit.csv`
- `hud_fmr_merge_summary_public_private_nonprofit.json`
- `fmr_control_estimates/fixed_effects_hud_fmr_coefficients.csv`
- `fmr_control_estimates/fixed_effects_hud_fmr_focal_coefficients.csv`
- `fmr_control_estimates/fixed_effects_hud_fmr_diagnostics.csv`
- `fmr_control_estimates/fixed_effects_hud_fmr_comparison.csv`
- `fmr_control_estimates/policy_hud_fmr_coefficients.csv`
- `fmr_control_estimates/policy_hud_fmr_focal_coefficients.csv`
- `fmr_control_estimates/policy_hud_fmr_diagnostics.csv`
- `fmr_control_estimates/policy_hud_fmr_comparison.csv`
- `fmr_control_estimates/hud_fmr_control_estimates_summary.json`

The merge audit is part of the evidence. If the match rate is not high, the control should not enter the paper until the unmatched rows are reviewed. The companion estimate summary records how many configured models estimate successfully, how many fail, and how much each focal coefficient moves after the rent control is added. Rows with `hud_fmr_match_status = multi_match` are matched rows where HUD reports more than one rent value for the same state-county-year name, often because New England and similar places include sub-county FMR areas. Those rows are exported separately so the robustness table can report or exclude them if needed.

## Merge rule and limitation

The current analysis panel has `STABBR`, `COUNTYNM`, `LATITUDE`, and `LONGITUD`, but not a county FIPS code. The first implementation therefore merges by reporting year, state abbreviation, and normalized county name.

That rule is transparent but not ideal. A future upstream panel should preserve county FIPS or another stable county identifier. Until then, every run writes unmatched rows and duplicate county-year HUD rows so the researcher can inspect whether county-name ambiguity matters.

## Paper language

Use this language only after the merge audit passes:

> As a robustness check, I merge HUD two-bedroom Fair Market Rent by reporting year, state, and county name to proxy for local housing-cost movement. The control is not part of the baseline because housing costs may be one channel through which published non-tuition cost-of-attendance allowances change.

Do not describe HUD FMR as a county CPI. It is a rent standard used in housing policy, not a general price index.
