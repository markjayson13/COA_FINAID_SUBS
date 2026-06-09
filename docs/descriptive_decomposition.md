# Descriptive decomposition

This note records the first descriptive COA and aid decomposition. The generated CSV files stay under `outputs/`, so this file keeps the main results visible in the public repository.

Run:

```bash
PYTHONPATH=src python scripts/build_descriptive_decomposition.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/descriptive_decomposition
```

The script writes:

- `outputs/descriptive_decomposition/decomposition_trends_by_sector_year.csv`
- `outputs/descriptive_decomposition/coa_adjacent_year_component_changes.csv`
- `outputs/descriptive_decomposition/coa_full_window_component_changes.csv`
- `outputs/descriptive_decomposition/descriptive_decomposition_summary.json`

The latest local run wrote 1,575 sector-year trend rows, 98 adjacent-year change rows, and 7 full-window change rows.

## Sector trends

Selected 2009 and 2023 means from the public and private nonprofit baseline panel:

| Sector | Year | Variable | Nonmissing rows | Mean | FTFT-weighted mean |
| --- | ---: | --- | ---: | ---: | ---: |
| Public | 2009 | `COA_MAIN` | 455 | 17,001 | 17,504 |
| Public | 2023 | `COA_MAIN` | 767 | 24,358 | 26,535 |
| Public | 2009 | `HEADROOM_MAIN` | 455 | 11,837 | 12,115 |
| Public | 2023 | `HEADROOM_MAIN` | 767 | 16,025 | 16,805 |
| Private nonprofit | 2009 | `COA_MAIN` | 802 | 26,854 | 31,331 |
| Private nonprofit | 2023 | `COA_MAIN` | 1,185 | 44,523 | 55,295 |
| Private nonprofit | 2009 | `HEADROOM_MAIN` | 802 | 11,231 | 11,329 |
| Private nonprofit | 2023 | `HEADROOM_MAIN` | 1,185 | 15,500 | 16,432 |

FTFT grant outcomes rose over the same endpoints:

| Sector | Year | Variable | Nonmissing rows | Mean | FTFT-weighted mean |
| --- | ---: | --- | ---: | ---: | ---: |
| Public | 2009 | `IGRNT_PER_FTFT_COHORT` | 637 | 1,247 | 1,541 |
| Public | 2023 | `IGRNT_PER_FTFT_COHORT` | 774 | 3,051 | 3,937 |
| Public | 2009 | `PGRNT_PER_FTFT_COHORT` | 637 | 1,190 | 991 |
| Public | 2023 | `PGRNT_PER_FTFT_COHORT` | 774 | 2,320 | 1,965 |
| Private nonprofit | 2009 | `IGRNT_PER_FTFT_COHORT` | 1,242 | 7,736 | 9,581 |
| Private nonprofit | 2023 | `IGRNT_PER_FTFT_COHORT` | 1,256 | 15,968 | 21,426 |
| Private nonprofit | 2009 | `PGRNT_PER_FTFT_COHORT` | 1,242 | 1,204 | 930 |
| Private nonprofit | 2023 | `PGRNT_PER_FTFT_COHORT` | 1,256 | 2,179 | 1,673 |

These are descriptive levels, not estimates. The row counts vary by variable and year.

## Same-institution component changes

The full-window component table compares institutions observed with complete component data in both 2009 and 2023 and with stable sector labels. This avoids treating panel entry or exit as growth.

| Sector | Paired institutions | Mean COA change | Mean headroom change | Tuition/fees change | Books change | Room/board change | Other-expense change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Public and private nonprofit | 1,082 | 13,166 | 4,696 | 8,470 | 236 | 3,521 | 939 |
| Public | 436 | 8,692 | 4,786 | 3,906 | 237 | 3,636 | 913 |
| Private nonprofit | 646 | 16,185 | 4,635 | 11,550 | 236 | 3,444 | 956 |

The component accounting closes exactly in the current output:

```text
COA_MAIN change - sum(component changes) = 0.0
HEADROOM_MAIN change - sum(allowance changes) = 0.0
```

The descriptive pattern is useful for the paper design. Public-sector COA growth is split between tuition/fees and non-tuition headroom. Private nonprofit COA growth is more tuition-heavy in the same-institution full-window comparison. That difference is one reason the baseline estimates should be reported by sector.
