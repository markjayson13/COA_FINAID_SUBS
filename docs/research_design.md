# Research design

This memo fixes the first empirical design for the paper before estimation code is added. The point is to keep the paper tied to the data contract in this repository and to keep the claims matched to what IPEDS can support.

## Research question

The paper asks whether institutional cost-of-attendance headroom is related to financial-aid packaging in Title IV higher education.

The question is narrower than a general Bennett-hypothesis claim. The mechanism is the Title IV packaging cap: cost of attendance sets the upper bound for total aid, and institutions report the allowance categories that enter that cap. If an institution raises allowance-based headroom, the feasible aid package changes. The empirical question is whether that headroom lines up with less institutional grant aid, more Pell or federal grant aid, more federal borrowing, or higher net price.

## Main estimand

The main estimand is institution-year incidence among four-year Title IV public and private nonprofit institutions.

The baseline sample remains:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

Private for-profit institutions remain an appendix or diagnostic scope unless the paper is rewritten as a three-sector design. That boundary matters because the current repository defines public and private nonprofit institutions as the baseline estimand and keeps for-profits buildable but separate.

## Unit of analysis

The unit is `UNITID` by year. The paper should not collapse the main sample to `OPEID` without a separate sensitivity design. A collapse changes the object of study from institution-year behavior to aid-program grouping behavior.

The panel is intentionally unbalanced. Entry and exit are sample events unless separate evidence shows an opening, closure, merger, sector change, or Title IV status change.

## Main measurement choices

The main study object is full-time, first-time undergraduate pricing and aid.

Main COA variables:

- `COA_MAIN`
- `HEADROOM_MAIN`
- `HEADROOM_MAIN_SHARE_COA`
- `HEADROOM_MAIN_SHARE_TUITION`
- `LN_HEADROOM_MAIN`
- `HEADROOM_ON`
- `HEADROOM_OFF_WF`
- `CHG2AY0`, `CHG4AY0`, `CHG5AY0`, `CHG6AY0`, `CHG7AY0`, `CHG8AY0`, `CHG9AY0`

The preferred headroom measure is the non-tuition part of the off-campus, not-with-family published COA budget. In the panel it is named `HEADROOM_MAIN`. `COA_MAIN` is the matching total COA field. The preferred normalized measure is `HEADROOM_MAIN_SHARE_COA`; `HEADROOM_MAIN_SHARE_TUITION` and `LN_HEADROOM_MAIN` are scale checks.

The measure is an institution-year published budget margin. It is not a student-level measure of unused aid capacity. The FTFT link comes from using FTFT SFA outcomes and reporting `SCFA1N`-weighted sensitivity checks.

Main aid outcomes:

- `IGRNT_PER_FTFT_COHORT`
- `INST_GRANT_SHARE_OF_TOTAL_GRANT_FTFT`
- `PGRNT_PER_FTFT_COHORT`
- `PELL_SHARE_OF_TOTAL_GRANT_FTFT`
- `FLOAN_PER_FTFT_COHORT`
- `NET_PRICE_0_30000_CLEAN` through `NET_PRICE_OVER_110000_CLEAN` as secondary outcomes

The main aid outcomes come from the IPEDS Student Financial Aid component, not finance revenue lines. Finance variables are controls and diagnostics, not the main measure of grant or loan packaging.

## Controls

The baseline controls should be parsimonious:

- state and year fixed effects through institution and year fixed effects
- `OPEN_ADMISSIONS_FLAG`
- `LN_SCFA1N`
- `LN_FIN_TOTAL_REVENUE`
- `LN_FIN_TOTAL_EXPENSES`
- `LN_FIN_TOTAL_ASSETS`
- institutional mission and location controls when they vary or are needed for stratified checks

Admissions selectivity should not define the baseline sample. `ADMIT_RATE`, test-score fields, and `SELECTIVITY_INDEX` belong to a selective-admissions sensitivity sample.

Ordinary enrollment and race-share controls remain out of the baseline until the upstream panel provides usable coverage for `ENRTOT`, `FTE`, and `PCTENR*`.

## Evidence ladder

### Stage 1: descriptive decomposition

Start with sector-specific trends in COA components and aid outcomes. The goal is to show whether headroom is a meaningful empirical margin before estimating models.

Required exhibits:

- COA and headroom trend table by sector
- component decomposition of COA growth
- headroom-measure coverage, correlations, invalid-share counts, and FTFT-cohort-weighted means from `docs/headroom_measurement_audit.md`
- descriptive statistics before and after table-only winsorization
- complete-case counts for each planned model
- aid-zero and metadata exposure summaries for model samples

### Stage 2: baseline institution fixed effects

Estimate within-institution associations between headroom and aid outcomes:

```text
Outcome_it = institution fixed effects + year fixed effects + beta Headroom_it + controls_it + error_it
```

Run public and private nonprofit models separately. Also run a pooled model with sector interactions for formal cross-sector tests.

This stage supports an institution-level incidence claim. It does not support a student-level packaging claim.

### Stage 3: policy exposure design

The stronger design should interact predetermined exposure with national aid shocks:

```text
Outcome_it = institution fixed effects + year fixed effects + beta Exposure_i x Shock_t + controls_it + error_it
```

This stage should not begin until a separate `policy_shocks` file is built from verified federal sources. Exposure must be measured before the shock period. Candidate exposure measures include baseline Pell intensity, baseline loan intensity, and baseline institutional-grant intensity.

### Stage 4: mechanism and falsification checks

The mechanism checks should compare allowance-like COA components with charge-like components. If headroom is an institutional allowance margin, off-campus room and board plus other expenses should be more responsive than tuition and fees.

Net price is a secondary incidence outcome because its sample and denominator differ from the main COA and SFA outcomes.

## Weighting

The primary estimates should be unweighted because the theory concerns institutional behavior. FTFT cohort-weighted estimates should be reported as a secondary view of student exposure.

## Sensitivity checks

Minimum set:

- public-only and private nonprofit-only estimates
- pooled sector interaction tests
- FTFT cohort-weighted estimates
- minimum-years sample restrictions
- balanced-window subset
- metadata exposure flags
- aid-zero suspect-row flags
- selective-admissions sample
- net-price secondary sample
- for-profit diagnostic appendix, if built

## Claim boundaries

Allowed claim:

> Within four-year Title IV public and private nonprofit institutions, changes in COA headroom are associated with changes in the mix of institutional grants, Pell or federal grants, loans, and net price.

Allowed after a verified exposure design:

> Institutions with greater pre-period federal-aid exposure changed headroom or aid outcomes differently after federal-aid shocks.

Not allowed from IPEDS alone:

- student-level packaging substitution
- proof that institutions intentionally inflated allowances
- a single national Bennett-hypothesis estimate
- claims that finance-revenue Pell lines measure student grant receipt across sectors

## Next implementation steps

1. Build a model-plan audit from `config/model_specifications.csv`.
2. Write the first descriptive decomposition script.
3. Add `config/policy_shocks.csv` only after every shock date and source is verified.
4. Add fixed-effects estimation after model samples and complete-case counts are stable.
