# Research design

This memo fixes the first empirical design for the paper before estimation code is added. The point is to keep the paper tied to the data contract in this repository and to keep the claims matched to what IPEDS can support.

## Research question

The paper asks whether institutional cost-of-attendance headroom is related to financial-aid packaging in Title IV higher education.

The question is narrower than a general Bennett-hypothesis claim. The mechanism is the Title IV packaging cap: cost of attendance sets the upper bound for total aid, and institutions report the allowance categories that enter that cap. If an institution raises allowance-based headroom, the feasible aid package changes. The empirical question is whether that headroom lines up with less institutional grant aid, more Pell or federal grant aid, more federal borrowing, or higher net price.

## Source and theory trail

`docs/design_justification.md` records the justification for each major design choice. It separates four bases:

- federal aid and IPEDS reporting rules
- higher-education pricing, aid, and Bennett-hypothesis literature
- nonprofit, public-sector, and organizational theory
- causal-design logic for exposure, placebo, and pre-trend checks

The design memo should be read with that crosswalk. If a design choice is changed, the source or theory basis should be changed there as well.

## Main estimand

The main estimand is institution-year incidence among four-year Title IV public and private nonprofit institutions.

The baseline sample remains:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

Rows with missing `PSET4FLG` or `SECTOR` are excluded because they do not satisfy the sample rule. This is a sample-definition exclusion, not an imputation step.

Private for-profit institutions remain an appendix or diagnostic scope unless the paper is rewritten as a three-sector design. That boundary matters because the current repository defines public and private nonprofit institutions as the baseline estimand and keeps for-profits buildable but separate.

## Unit of analysis

The unit is `UNITID` by year. The paper should not collapse the main sample to `OPEID` without a separate sensitivity design. A collapse changes the object of study from institution-year behavior to aid-program grouping behavior.

The panel is intentionally unbalanced. Entry and exit are sample events unless separate evidence shows an opening, closure, merger, sector change, or Title IV status change.

IPEDS `year` is an organizing index across components. It should not be read as a common event date for COA, Student Financial Aid, admissions, and finance fields. The empirical design estimates institution-year relationships in reported IPEDS data while absorbing year effects; it does not require every component to share an identical measurement day.

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

All-undergraduate aid fields remain useful for external-validity checks, but they are not interchangeable with the FTFT outcomes. FTFT models stay closest to the pricing and aid cohort used in this paper. Undergraduate-wide models would answer a broader enrollment-incidence question.

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
- component decomposition of COA growth from `docs/descriptive_decomposition.md`
- headroom-measure coverage, correlations, invalid-share counts, and FTFT-cohort-weighted means from `docs/headroom_measurement_audit.md`
- descriptive statistics before and after table-only winsorization
- complete-case counts and materialized model samples from `docs/pre_estimation_readiness.md`
- aid-zero and metadata exposure summaries for model samples

### Stage 2: baseline institution fixed effects

Estimate within-institution associations between headroom and aid outcomes:

```text
Outcome_it = institution fixed effects + year fixed effects + beta Headroom_it + controls_it + error_it
```

Run public and private nonprofit models separately. Also run a pooled model with sector interactions for formal cross-sector tests.

The pooled models have two layers. The first uses common year fixed effects and a headroom-by-private-nonprofit interaction. The second absorbs sector-by-year fixed effects. The sector-year version is the preferred pooled diagnostic because it allows public and private nonprofit institutions to follow different calendar-year shocks.

The baseline stage also includes a component model that enters tuition and fees, books, off-campus room and board, and other expenses side by side. That model is a mechanism check. It asks whether the aggregate headroom association is carried by allowance-like components or by charge-like components.

This stage supports an institution-level incidence claim. It does not support a student-level packaging claim.

The first implementation is now in `scripts/run_fixed_effects.py`, with the current local run summarized in `docs/fixed_effects_baseline.md`. `scripts/build_estimate_tables.py` exports the current fixed-effects table to CSV, Markdown, LaTeX, and Word.

### Stage 3: policy exposure design

The stronger design should interact predetermined exposure with national aid shocks:

```text
Outcome_it = institution fixed effects + year fixed effects + beta Exposure_i x Shock_t + controls_it + error_it
```

The national Pell-shock registry is now recorded in `config/policy_shocks.csv` and audited by `scripts/audit_policy_shocks.py`. The registry records maximum Pell award changes and additional Pell authority events from verified Federal Student Aid sources.

The registry is not an institution-level treatment by itself because the Pell schedule is national. Exposure must be measured before the shock period. The first policy-exposure design uses the 2017 restoration of year-round Pell and measures Pell exposure from 2014-2016. The second policy-exposure design uses annual changes in the maximum Pell Grant award interacted with the same pre-period Pell exposure. It is documented in `docs/policy_exposure_design.md`.

The policy design now includes event-study interactions for 2014-2023, omitting 2016. The 2014 and 2015 coefficients are lead checks. The 2017-2023 coefficients show post-restoration dynamics. These estimates remain diagnostic until the lead and placebo checks are clean for the outcome.

The maximum-Pell design has a real-dollar version and nominal checks. The real-dollar version is the preferred repeated-shock design because nominal award increases partly reflect inflation. This design still needs placebo checks before any causal wording.

The policy-exposure work remains a diagnostic layer for the WEAI paper. A later journal extension should treat causal identification as a separate design problem. Two plausible merged-shock paths are state-appropriations shocks for public institutions and local housing-cost shocks for allowance-based headroom. Either path would need new exposure construction, merged-data audits, and pretrend or placebo gates before causal wording.

The sample ends in 2023. The manuscript can use later federal-aid changes as policy motivation, but the estimates should be described as evidence from the 2009-2023 IPEDS reporting window.

### Stage 4: mechanism and falsification checks

The mechanism checks should compare allowance-like COA components with charge-like components. If headroom is an institutional allowance margin, off-campus room and board plus other expenses should be more responsive than tuition and fees.

Net price is a secondary incidence outcome because its sample and denominator differ from the main COA and SFA outcomes.

## Weighting

The primary estimates should be unweighted because the theory concerns institutional behavior. FTFT cohort-weighted estimates should be reported as a secondary view of student exposure.

## Sensitivity checks

Minimum set:

- public-only and private nonprofit-only estimates
- pooled sector interaction tests
- pooled sector-by-year fixed-effect checks
- COA component horse-race checks
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

1. Tighten the institutional-grant policy design before treating that estimate as causal, because the 2016 placebo check is not clean.
2. Keep policy-exposure estimates separate from the baseline fixed-effects estimates.
3. Use the reviewer model-card and sample-attrition tables when drafting the appendix.
4. Reserve state-appropriations and local housing-cost shock designs for the later causal extension unless the WEAI paper is deliberately reframed.
5. Add manuscript exhibit scripts only after the paper table order is fixed.
