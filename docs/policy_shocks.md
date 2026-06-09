# Policy shock registry

`config/policy_shocks.csv` records national Pell Grant schedule changes for the IPEDS SFA years used in this paper. It is a source registry, not an estimation sample.

The file has one row for each award year from 2009-2010 through 2023-2024. `ipeds_sfa_year` equals the first calendar year in the award year, matching the year convention used by the prepared IPEDS SFA panel.

`config/policy_price_index.csv` records CPI-U annual averages used to express maximum Pell awards in 2023 dollars. The policy-exposure builder merges that file with the Pell schedule before writing real maximum-award fields.

## Fields

- `pell_max_award`: maximum Pell Grant award listed in the Federal Student Aid payment schedule.
- `pell_max_award_delta`: dollar change from the previous in-panel award year.
- `pell_large_increase`: `true` when the increase is at least $150.
- `additional_pell_authority_status`: whether additional Pell authority was available, capped at one scheduled award, or available up to 150 percent of a scheduled award.
- `additional_pell_authority_shock`: `-1` for the 2011-2012 removal event, `1` for the 2017-2018 restoration event, and `0` otherwise.
- `source_key`, `source_date`, `source_title`, and `source_url`: row-level Federal Student Aid source information.
- `additional_pell_source_key` and `additional_pell_source_url`: event-specific sources for the 2011-2012 removal and 2017-2018 restoration.

The price-index file records:

- `cpi_u_annual_average`: CPI-U all items annual average.
- `real_base_year`: constant-dollar base year, currently 2023.
- source metadata for the BLS CPI-U series.

## Current registry

The current registry has 15 rows. It covers 2009-2010 through 2023-2024.

Large maximum-award increases are coded for IPEDS SFA years 2010, 2018, 2020, 2021, 2022, and 2023.

Additional Pell authority events are coded for IPEDS SFA years 2011 and 2017.

## Audit

Run the registry audit with:

```bash
PYTHONPATH=src python scripts/audit_policy_shocks.py \
  --config config/policy_shocks.csv \
  --output-dir outputs/policy_shocks
```

The audit writes:

- `outputs/policy_shocks/policy_shock_audit.csv`
- `outputs/policy_shocks/policy_shock_summary.json`

The audit fails if award years are not contiguous, IPEDS SFA years do not match award-year starts, maximum-award deltas are wrong, large-increase flags are wrong, source dates are invalid, source URLs are not Federal Student Aid URLs, rows are unverified, or the additional Pell authority events are mis-coded.

## Paper use

The registry can support timing checks, maximum-award intensity checks, and exposure designs. It should not be treated as an institution-level policy treatment by itself because the Pell schedule is national.

Any policy-exposure design should interact a national shock or maximum-award change with a pre-period institution measure such as Pell intensity, loan intensity, or institutional-grant intensity. Those exposure measures should be built and audited separately before the paper uses them.
