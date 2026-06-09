# Variable selection

This project studies whether cost-of-attendance headroom is related to the way institutions package grants, loans, and institutional aid. The variable file is therefore built around the financial-aid mechanism, not around every IPEDS field that might be interesting.

The source is institution-level IPEDS data. IPEDS is an annual NCES collection with interrelated components covering institutional characteristics, admissions, enrollment, student financial aid, prices, and finance. The cost-of-attendance fields used here come from the IPEDS student charges and cost-of-attendance reporting flow used by institutional financial-aid offices.

Source notes:

- NCES IPEDS survey components: https://nces.ed.gov/ipeds/survey-components
- NCES IPEDS Handbook of Survey Methods: https://nces.ed.gov/statprog/handbook/pdf/ipeds.pdf
- IPEDS Student Financial Aid survey material, cost-of-attendance reporting flow: https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2014/student%20financial%20aid/package_7_16.pdf

For the full decision-by-decision source trail, see `docs/data_decision_register.md`.

## Primary variables

The main sample is four-year Title IV public and private nonprofit institutions from 2009 through 2023:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

Private for-profit institutions are not part of the baseline sample. They can be built separately with `--sectors 3` for diagnostic or appendix checks. The default build writes the baseline sample plus public-only and private nonprofit-only sector files.

The primary headroom measures use the current tuition-and-fee, books, room-and-board, and other-expense fields:

- `CHG2AY0`, `CHG4AY0`, `CHG7AY0`, `CHG8AY0`
- `CHG5AY0`, `CHG6AY0`, `CHG9AY0` for alternate living-arrangement checks
- `CHG1AY0` and `CHG3AY0` for in-district and out-of-state diagnostics

The preferred aliases are `COA_MAIN`, `HEADROOM_MAIN`, `HEADROOM_MAIN_SHARE_COA`, `HEADROOM_MAIN_SHARE_TUITION`, and `LN_HEADROOM_MAIN`. The contract in `config/headroom_measures.csv` records which measures are main, which are component checks, and which use `SCFA1N` for FTFT-cohort-weighted summaries.

The main aid variables are full-time, first-time undergraduate aid measures:

- Pell grants: `PGRNT_A`, `PGRNT_N`, `PGRNT_P`, `PGRNT_T`
- Institutional grants: `IGRNT_A`, `IGRNT_N`, `IGRNT_P`, `IGRNT_T`
- Total, federal, state/local, and other federal grants: `AGRNT*`, `FGRNT*`, `SGRNT*`, `OFGRT*`
- Loans: `LOAN*`, `FLOAN*`, `OLOAN*`

The script also keeps the all-undergraduate aid family:

- `UAGRNT*`
- `UPGRNT*`
- `UFLOAN*`

Those variables support checks that do not depend only on the full-time, first-time cohort.

## Controls

The controls are selected to cover geography, institutional mission, scale, admissions/selectivity, and fiscal capacity.

Geographic controls include state, region, county, urbanicity, and metro-area fields: `STABBR`, `FIPS`, `OBEREG`, `COUNTYNM`, `CBSA`, `CBSATYPE`, `CSA`, `LOCALE`, `LATITUDE`, and `LONGITUD`.

Institutional controls include size, Carnegie classification, degree-granting status, graduate offerings, HBCU, Tribal college, land-grant, hospital, and medical-degree indicators.

Admissions controls are split by use. `OPENADMP` is part of the baseline control set. Applications, admissions, enrolled students, SAT percentiles, ACT percentiles, and test-submission shares are reserved for the selective-admissions robustness sample because IPEDS admissions data are collected for institutions without open admissions policies.

Scale controls use the SFA cohort fields because ordinary enrollment coverage is not usable in this local clean panel for the analysis sample. The useful fields are `SCUGRAD`, `SCUGFFN`, `SCUGFFP`, `SCFA1N`, and `SCFA2`.

I do not use `ENRTOT`, `FTE`, or the `PCTENR*` race-share family in the current baseline. Those fields are either absent from the public variable contract or do not have enough usable coverage in the verified local panel. This is a data limitation, not a modeling preference. If ordinary enrollment and race-share coverage are recovered in the upstream panel, they should be added through a separate documented sensitivity.

Aid zeros are audited but not filtered. The build writes `analysis_aid_zero_consistency.csv` and `analysis_aid_zero_suspect_rows.csv` to separate rows where aid counts, percentages, averages, and totals all support a true zero from rows where a zero total conflicts with positive count, percent, or average signals.

## IPEDS metadata fields

The extract keeps IPEDS component metadata for the parts of the panel used in the paper:

- Institutional Characteristics: `IMP_IC`, `LOCK_IC`, `REV_IC`
- Student Financial Aid: `IMP_SFA`, `LOCK_SFA`, `REV_SFA`, `IDX_SFA`, `PRCH_SFA`, `PCSFA_F`
- Finance: `IMP_F`, `LOCK_F`, `REV_F`, `IDX_F`, `PRCH_F`, `PCF_F`, `PCF_F_RV`
- Enrollment: `IMP_EF`, `LOCK_EF`, `REV_EF`, `IDX_EF`, `PRCH_EF`, `PCEF_F`
- 12-month Enrollment: `IMP_E12`, `LOCK_E12`, `REV_E12`, `IDX_E12`, `PRCH_E12`, `PCE12_F`
- Admissions: `IMP_ADM`, `LOCK_ADM`, `REV_ADM`, `IDX_ADM`, `PRCH_ADM`, `PCADM_F`

The raw fields stay in the panel. The preparation script also derives component flags for imputation, prior-year revision, and parent-linked reporting. These flags support sample descriptions and later sensitivity checks. They do not replace the raw IPEDS codes.

## Finance controls

Finance variables are sector-specific in IPEDS. The raw fields are kept for audit, then the preparation script builds common controls by sector:

- public GASB fields: `F1*`
- private nonprofit FASB fields: `F2*`
- private for-profit fields: `F3*`, retained for diagnostic builds rather than the baseline sample

The derived finance controls include tuition revenue, total revenue, total expenses, total assets, beginning endowment where reported, instruction expense, academic support expense, student services expense, and institutional support expense. Public state and local appropriations are kept as a public-sector measure because the same concept is not reported the same way in the private-sector forms.

## Secondary outcomes

Net-price variables are retained as secondary outcomes and diagnostics. They are thinner than the main aid and COA fields.

The current income-band net-price variables are sector-specific in the clean panel. Public institutions report through the `NPIS410` to `NPIS450` family. Private nonprofit and private for-profit institutions report through the `NPT410` to `NPT450` family. The preparation script keeps both raw families and builds harmonized `NET_PRICE_*` fields by institution control.

## Current verification

With the local panel verified on June 8, 2026:

- selected raw variables: 215
- missing selected variables in the source panel: 0
- main sample: 35,443 institution-years and 2,774 institutions
- public-sector file: 11,215 institution-years and 882 institutions
- private nonprofit file: 24,228 institution-years and 1,903 institutions
- primary headroom, Pell, and institutional-grant complete cases: 25,023 institution-years and 2,200 institutions
- primary plus FTFT totals and denominator: 26,051 institution-years and 2,247 institutions
- all-undergraduate aid family: 29,520 institution-years and 2,302 institutions
- sector-appropriate finance controls: 32,544 institution-years and 2,514 institutions
- selective-admissions admit-rate and yield checks: 24,732 institution-years and 1,926 institutions
- selective-admissions robustness index inputs: 18,813 institution-years and 1,599 institutions
- ordinary enrollment and race-share controls based on `ENRTOT`, `FTE`, or `PCTENR*`: not used in baseline because verified local coverage is not usable
- private raw `NPT*` net-price income-band complete cases: 12,969 institution-years and 1,209 institutions
- sector-harmonized current net-price income-band complete cases: 21,304 institution-years and 1,983 institutions
- any tracked IPEDS metadata exposure: 7,103 institution-years
