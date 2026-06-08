# Variable selection

This project studies whether cost-of-attendance headroom is related to the way institutions package grants, loans, and institutional aid. The variable file is therefore built around the financial-aid mechanism, not around every IPEDS field that might be interesting.

The source is institution-level IPEDS data. IPEDS is an annual NCES collection with interrelated components covering institutional characteristics, admissions, enrollment, student financial aid, prices, and finance. The cost-of-attendance fields used here come from the IPEDS student charges and cost-of-attendance reporting flow used by institutional financial-aid offices.

Source notes:

- NCES IPEDS survey components: https://nces.ed.gov/ipeds/survey-components
- NCES IPEDS Handbook of Survey Methods: https://nces.ed.gov/statprog/handbook/pdf/ipeds.pdf
- IPEDS Student Financial Aid survey material, cost-of-attendance reporting flow: https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2014/student%20financial%20aid/package_7_16.pdf

## Primary variables

The main sample is four-year Title IV institutions from 2009 through 2023:

```text
PSET4FLG = 1
SECTOR in (1, 2, 3)
year = 2009:2023
```

The primary headroom measures use the current tuition-and-fee, books, room-and-board, and other-expense fields:

- `CHG2AY0`, `CHG4AY0`, `CHG7AY0`, `CHG8AY0`
- `CHG5AY0`, `CHG6AY0`, `CHG9AY0` for alternate living-arrangement checks
- `CHG1AY0` and `CHG3AY0` for in-district and out-of-state diagnostics

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

Admissions controls include open-admissions status, applications, admissions, enrolled students, SAT percentiles, ACT percentiles, and test-submission shares. These fields are not complete enough to be mandatory for the main sample, but they are useful for selectivity checks.

Scale controls use the SFA cohort fields because the ordinary enrollment totals in this local clean panel are present in the schema but empty for the analysis sample. The useful fields are `SCUGRAD`, `SCUGFFN`, `SCUGFFP`, `SCFA1N`, and `SCFA2`.

## Finance controls

Finance variables are sector-specific in IPEDS. The raw fields are kept for audit, then the preparation script builds common controls by sector:

- public GASB fields: `F1*`
- private nonprofit FASB fields: `F2*`
- private for-profit fields: `F3*`

The derived finance controls include tuition revenue, total revenue, total expenses, total assets, beginning endowment where reported, instruction expense, academic support expense, student services expense, and institutional support expense. Public state and local appropriations are kept as a public-sector measure because the same concept is not reported the same way in the private-sector forms.

## Secondary outcomes

Net-price variables are retained as secondary outcomes and diagnostics. They are thinner than the main aid and COA fields. In the verified local panel, complete cases for all five current income-band net-price fields were 15,175 institution-years and 1,744 institutions.

## Current verification

With the local panel verified on June 8, 2026:

- selected raw variables: 176
- missing selected variables in the source panel: 0
- main sample: 43,476 institution-years and 3,769 institutions
- primary headroom, Pell, and institutional-grant complete cases: 28,989 institution-years and 2,885 institutions
- primary plus FTFT totals and denominator: 30,996 institution-years and 3,009 institutions
- all-undergraduate aid family: 36,758 institution-years and 3,212 institutions
- sector-appropriate finance controls: 38,564 institution-years and 3,232 institutions
- admissions/selectivity complete cases: 16,649 institution-years and 1,530 institutions
- current net-price income-band complete cases: 15,175 institution-years and 1,744 institutions
