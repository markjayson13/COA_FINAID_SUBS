# Headroom measurement audit

This note records the current audit of the headroom-measure family. The generated CSV files remain under `outputs/` and are not committed, so this file keeps the main measurement facts visible in the public repository.

The audit was rebuilt on June 9, 2026 from:

- input panel hash: `4b481d38b1b3ca582062df6ef6eed66a1c4be3d916fee1ade54917f61d5c91cb`
- dictionary hash: `7633c42cb312002ff2085e10a91e28981c740f738cedc6b5e7e66ef6ec382729`
- script: `scripts/audit_headroom_measures.py`
- config: `config/headroom_measures.csv`

The baseline public and private nonprofit panel has 35,443 institution-years, 2,774 institutions, and 355 columns after the latest panel rebuild.

## Main measure coverage

| Scope | Nonmissing rows | Nonmissing institutions | Row coverage | Mean | Median | FTFT-weighted mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Public and private nonprofit | 26,387 | 2,271 | 74.4% | 13,845 | 13,700 | 14,531 |
| Public | 9,727 | 809 | 86.7% | 14,158 | 13,948 | 14,694 |
| Private nonprofit | 16,660 | 1,468 | 68.8% | 13,663 | 13,500 | 14,133 |

`HEADROOM_MAIN_SHARE_COA` has no values outside `[0, 1]` in the refreshed audit. `HEADROOM_MAIN_SHARE_TUITION` is not bounded by one because non-tuition allowances can exceed tuition and fees, especially in the public sector.

## Component pattern

In the baseline sample, `HEADROOM_MAIN` is weakly correlated with in-state tuition and fees and strongly correlated with off-campus room and board:

| Comparison variable | Correlation with `HEADROOM_MAIN` | Pairwise rows |
| --- | ---: | ---: |
| `CHG2AY0` | 0.054 | 26,386 |
| `CHG4AY0` | 0.274 | 26,387 |
| `CHG7AY0` | 0.876 | 26,387 |
| `CHG8AY0` | 0.546 | 26,387 |
| `COA_MAIN` | 0.327 | 26,386 |
| `HEADROOM_MAIN_SHARE_COA` | 0.288 | 26,386 |
| `HEADROOM_ON` | 0.583 | 21,397 |
| `HEADROOM_OFF_WF` | 0.529 | 26,375 |

This pattern supports treating the main measure as an allowance-margin variable rather than a tuition proxy. It also means the paper should report component checks, because off-campus room and board carries much of the variation.

## Implications for model design

The updated model-plan audit reports no missing variables across the ten planned specifications. The main institutional-grant dollar model has 24,247 complete-case rows and 2,082 institutions. The institutional-grant share model has 24,125 rows and 2,075 institutions.

The paper should keep the following boundary:

> Headroom is a published institution-year COA margin. It is not a student-level measure of unused aid eligibility.

The best baseline specification uses `HEADROOM_MAIN` and sector-specific estimates. `HEADROOM_MAIN_SHARE_COA`, `HEADROOM_MAIN_SHARE_TUITION`, `LN_HEADROOM_MAIN`, `HEADROOM_ON`, `HEADROOM_OFF_WF`, and the component variables belong in the measurement and sensitivity tables.

The in-district check is a denominator check, not a second raw allowance measure. `HEADROOM_IN_DISTRICT` uses the same allowance numerator as `HEADROOM_MAIN`; `HEADROOM_SHARE_IN_DISTRICT` is the public-sector diagnostic that changes the total COA denominator.
