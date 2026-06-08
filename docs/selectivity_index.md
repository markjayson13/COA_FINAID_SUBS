# Admissions and Selectivity

This note records how admissions variables enter the research extract.

## Baseline use

The baseline sample uses `OPENADMP`, not admit rates or test scores. The main reason is measurement. IPEDS states that the Admissions component collects information from institutions that do not have an open-admissions policy. The component includes acceptance rates, yield, and SAT/ACT scores when test scores are required. Open-admissions institutions therefore should not be forced into an admit-rate or test-score complete-case sample.

In the baseline extract, the preparation script writes:

- `OPEN_ADMISSIONS_FLAG`
- `SELECTIVE_ADMISSIONS_FLAG`
- `VALID_ADMIT_RATE_FLAG`
- `VALID_YIELD_RATE_FLAG`

The primary complete-case audit includes `OPENADMP`. Admit rates and test scores are not primary-sample requirements.

## Robustness sample

The selective-admissions robustness sample is written separately:

```text
analysis_panel_selective_admissions_robustness_2009_2023_<scope>.parquet
```

A row enters this sample when:

```text
OPENADMP = 2
APPLCN > 0
0 <= ADMSSN <= APPLCN
at least one usable SAT or ACT midpoint is present
```

`YIELD_RATE` is derived and audited, but the selectivity index does not require yield. Yield mixes admissions competition with institutional enrollment management and student choice, so it is kept as a diagnostic rather than an index component.

## Index construction

The index uses two pieces of information:

- lower admit rate, measured as the within-year z-score of `-ADMIT_RATE`
- stronger entering-student test-score signal, measured from within-year z-scores of `SAT_TOTAL_MIDPOINT` and `ACT_COMPOSITE_MIDPOINT`

The test-score component is the mean of the available SAT and ACT z-scores. The final index is the mean of the admit-rate component and the test-score component:

```text
SELECTIVITY_INDEX = mean(SELECTIVITY_ADMIT_RATE_Z, SELECTIVITY_TEST_SCORE_Z)
```

All standardization is done within year and within the output scope. A high value therefore means more selective relative to other institutions in the same year and sample scope. The index is not a replacement for Barron's categories or any proprietary college ranking.

The script also writes:

- `SELECTIVITY_PERCENTILE_WITHIN_YEAR`
- `SELECTIVITY_CATEGORY`
- `analysis_selectivity_summary.csv`

The category rules are:

| Category | Rule |
| --- | --- |
| `open_admission` | `OPENADMP = 1` |
| `selective_admissions_index_missing` | non-open admissions but missing index inputs or no within-year variation |
| `less_selective` | index percentile at or below 25 percent |
| `moderately_selective` | index percentile above 25 percent and at or below 50 percent |
| `selective` | index percentile above 50 percent and at or below 75 percent |
| `highly_selective` | index percentile above 75 percent |

With the local 2009-2023 baseline build verified on June 8, 2026, the selective-admissions robustness panel contains 18,813 institution-years and 1,599 institutions. The public-sector robustness file contains 7,299 institution-years and 579 institutions. The private nonprofit robustness file contains 11,514 institution-years and 1,022 institutions.

## Literature basis

The index follows the empirical convention that selectivity is not just a policy label. It should combine admissions competition with academic signals among entering students.

IPEDS supplies the needed public data: open-admissions status, applicants, admissions, yield, and SAT/ACT score ranges for institutions without open admissions policies.

Dale and Krueger frame the selectivity problem around the fact that elite colleges admit students partly on characteristics tied to later outcomes. Their NBER working paper also notes the use of schools' average SAT scores as a way to control for college selectivity.

Hoxby studies changing college selectivity as a re-sorting of students across institutions and emphasizes that rising selectivity is concentrated at a small part of the college distribution. That motivates within-year percentiles rather than a claim that all institutions have become more selective over time.

Sources:

- NCES, IPEDS Admissions component: https://nces.ed.gov/ipeds/survey-components/6
- Stacy Berg Dale and Alan B. Krueger, "Estimating the Payoff to Attending a More Selective College: An Application of Selection on Observables and Unobservables," NBER Working Paper 7322, 1999; published in the Quarterly Journal of Economics, 2002: https://www.nber.org/papers/w7322
- Caroline M. Hoxby, "The Changing Selectivity of American Colleges," Journal of Economic Perspectives 23(4), 2009: https://www.aeaweb.org/articles?id=10.1257/jep.23.4.95

## Paper wording

Use wording like this in the data section:

> I treat open-admissions status as the baseline admissions control. Admit rates and test scores are available only for institutions without open admissions policies, so they are not used to define the main sample. I use them in a separate selective-admissions robustness sample. The selectivity index averages a within-year admit-rate component and a within-year SAT/ACT component, then assigns percentile categories within year and sample scope.
