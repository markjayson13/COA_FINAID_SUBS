# Headroom measurement

This note defines the headroom measures used before estimation. The purpose is to separate the main empirical measure from supporting checks. The current rebuilt audit results are summarized in `docs/headroom_measurement_audit.md`.

## Main measure

The preferred headroom measure is:

```text
HEADROOM_MAIN = CHG4AY0 + CHG7AY0 + CHG8AY0
COA_MAIN = CHG2AY0 + CHG4AY0 + CHG7AY0 + CHG8AY0
HEADROOM_MAIN_SHARE_COA = HEADROOM_MAIN / COA_MAIN
HEADROOM_MAIN_SHARE_TUITION = HEADROOM_MAIN / CHG2AY0
```

The main measure uses off-campus, not-with-family allowances. It treats headroom as the non-tuition part of the published cost-of-attendance budget. The measure is tied to the aid analysis by pairing it with full-time, first-time Student Financial Aid outcomes and the `SCFA1N` FTFT SFA cohort count.

The measure is not student-level unused aid capacity. IPEDS reports institution-year charge and allowance fields. Unless living-arrangement weights are added from a verified source, the main variable should be described as a published institutional COA margin.

## Supporting checks

The analysis should report:

- `HEADROOM_MAIN`
- `HEADROOM_MAIN_SHARE_COA`
- `HEADROOM_MAIN_SHARE_TUITION`
- `LN_HEADROOM_MAIN`
- `HEADROOM_ON`
- `HEADROOM_OFF_WF`
- `HEADROOM_SHARE_IN_DISTRICT`
- `CHG2AY0`, `CHG4AY0`, `CHG7AY0`, `CHG8AY0`

These checks separate charge-like variation from allowance-like variation. They also show whether the result depends on the off-campus not-with-family assumption.

`HEADROOM_IN_DISTRICT` is not a separate raw allowance numerator. It equals the main off-campus allowance sum. Its purpose is to pair that numerator with `COA_IN_DISTRICT` through `HEADROOM_SHARE_IN_DISTRICT`, which asks whether the denominator choice changes the public-sector diagnostic.

## Audit outputs

Run:

```bash
python scripts/audit_headroom_measures.py
```

The audit writes:

- `outputs/headroom_measures/headroom_measure_coverage.csv`
- `outputs/headroom_measures/headroom_measure_by_sector_year.csv`
- `outputs/headroom_measures/headroom_measure_correlations.csv`
- `outputs/headroom_measures/headroom_measure_summary.json`

The coverage table reports nonmissing rows, institutions, invalid share values, unweighted means, and FTFT-cohort-weighted means. The sector-year table gives trends by sector and year. The correlation table shows how close the main measure is to its normalizations and component checks.

## Paper language boundary

Use wording like:

> Headroom measures the non-tuition portion of the institution's published COA budget. It is an institution-year measure, not a student-level measure of unused aid eligibility.

Do not describe headroom as cash available to students or as direct individual aid capacity.
