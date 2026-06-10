# Research workflow from IPEDSDB_Panel to estimation

This memo explains how I moved from the upstream IPEDS panel build to the estimation files used in this project. It is written as a process note for review, not as a substitute for the paper's methods section.

The project has two repositories with different jobs:

- `IPEDSDB_Panel` builds the cleaned IPEDS panel from annual NCES Access databases.
- `COA_FINAID_SUBS` starts from that cleaned panel and owns the research design, sample rules, variable contract, derived measures, audits, model samples, and estimates for this paper.

That split is deliberate. The panel-construction repo handles the general IPEDS data problem. The research repo handles the paper-specific question: whether cost-of-attendance headroom is associated with institutional grant substitution and related aid outcomes among four-year Title IV public and private nonprofit institutions.

## 1. Upstream panel construction

The upstream repo, `IPEDSDB_Panel`, builds the source panel used here. Its canonical output is:

```text
Panels/panel_clean_analysis_2004_2023.parquet
Dictionary/dictionary_lake.parquet
```

The upstream panel is an unbalanced `UNITID` by `year` panel built from final IPEDS Access releases for 2004 through 2023. The panel key remains the IPEDS institution record, not an `OPEID` rollup. The upstream repo keeps parent-child and reporting-structure issues visible through QA files instead of collapsing all records into a single parent-level history.

The construction path in `IPEDSDB_Panel` is:

1. Download final annual IPEDS Access releases.
2. Extract Access tables.
3. Build metadata dictionaries from Access metadata.
4. Harmonize annual tables into yearly long files.
5. Stitch the yearly long panel.
6. Build the wide analysis panel.
7. Apply documented parent-child cleaning.
8. Run QA/QC and acceptance checks.
9. Build the panel dictionary used by downstream projects.

The release gate in the upstream repo checks one row per `UNITID` and `year`, dictionary integrity, panel structure, identifier linkage, component timing, finance comparability, parent-child cleaning, and row preservation. In the verified upstream build, the clean panel has 141,711 institution-years and 1,864 columns for 2004 through 2023.

The important point for this paper is that I did not start from hand-merged flat files. I started from a clean panel with an explicit construction method and a separate dictionary lake.

## 2. Research repo inputs

This repository reads two upstream files:

```text
panel_clean_analysis_2004_2023.parquet
dictionary_lake.parquet
```

The default local root is:

```text
$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet
$IPEDSDB_ROOT/Dictionary/dictionary_lake.parquet
```

The research repo treats those files as inputs. It does not rebuild raw NCES databases. It also does not modify the upstream panel. All paper-specific outputs are generated under `outputs/`, which is ignored by Git.

The first command is:

```bash
python scripts/prepare_analysis_panel.py
```

That command builds the paper's analysis panel, the sector-specific panels, and the first audit files.

## 3. Baseline sample

The baseline sample is:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

This keeps four-year Title IV public and private nonprofit institutions. Private for-profit institutions are excluded from the baseline because their incentives, regulatory exposure, program mix, and finance structure differ enough to require a separate design. They remain buildable as a diagnostic sample.

The 2009 start is a measurement decision. The cost-of-attendance component fields used to build the headroom measures are usable from 2009 in the verified clean panel. It is not a policy cutoff.

The default build writes three scopes:

```text
outputs/analysis_panel/public_private_nonprofit/
outputs/analysis_panel/public/
outputs/analysis_panel/private_nonprofit/
```

The current verified baseline panel has 35,443 institution-years, 2,774 institutions, and 355 columns. The public file has 11,215 institution-years and 882 institutions. The private nonprofit file has 24,228 institution-years and 1,903 institutions.

## 4. Variable contract

The raw variable contract is in:

```text
config/analysis_variables.csv
```

The selected raw-variable contract currently contains 215 variables, all present in the source panel. The contract covers:

- institutional identifiers and sample fields
- cost-of-attendance components
- Student Financial Aid grant and loan fields
- net-price income-band fields
- admissions and selectivity fields
- finance variables
- metadata, imputation, revision, and parent-child fields

The audit command is:

```bash
python scripts/audit_variable_config.py \
  --input-panel "$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet" \
  --output-dir outputs/variable_audit \
  --years 2009:2023
```

The audit reports column presence, coverage, variable-group coverage, metadata coverage, and complete-case counts for empirical scenarios. This keeps variable selection visible before model samples are built.

## 5. Analysis-panel checks

The preparation script checks the data before it writes the analysis panel. The main checks are:

- one row per `UNITID` and `year`
- no missing `UNITID` or `year`
- required variables present
- sample counts before and after filtering
- panel balance by institution
- sample entry and exit by sector and year
- entry and exit reasons using the full panel
- minimum-years sensitivity
- nonnegative checks for core money variables
- raw and cleaned net-price fields
- aid-zero consistency checks
- metadata exposure flags
- SHA-256 hashes for the input panel, input dictionary, and output parquet

The panel remains unbalanced. That is part of the design. Institutions can enter or leave the research sample because of real entry, closure, merger, reporting changes, Title IV status changes, `PSET4FLG` changes, or sector changes. The sample-dynamics tables document those events instead of forcing a balanced panel.

In the current baseline file, 1,959 of 2,774 institutions are observed in all 15 years from 2009 through 2023. The combined baseline peaks in 2018, while the sector files differ: the public file grows through 2023, and the private nonprofit file declines after its 2015 peak.

## 6. Headroom measurement

The paper studies published cost-of-attendance headroom as an institution-year budget margin inside the Title IV aid cap. The main measure is:

```text
HEADROOM_MAIN = CHG4AY0 + CHG7AY0 + CHG8AY0
COA_MAIN = CHG2AY0 + CHG4AY0 + CHG7AY0 + CHG8AY0
HEADROOM_MAIN_SHARE_COA = HEADROOM_MAIN / COA_MAIN
HEADROOM_MAIN_SHARE_TUITION = HEADROOM_MAIN / CHG2AY0
```

`HEADROOM_MAIN` uses off-campus, not-with-family non-tuition allowances: books, room and board, and other expenses. It is paired with full-time, first-time Student Financial Aid outcomes and the `SCFA1N` FTFT SFA cohort count.

The measure is not student-level unused aid capacity. IPEDS reports institution-year charge and allowance fields. The paper therefore describes headroom as a published institutional COA margin, not cash available to individual students.

The headroom audit is:

```bash
PYTHONPATH=src python scripts/audit_headroom_measures.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/headroom_measures \
  --config config/headroom_measures.csv
```

The current audit reports 26,387 nonmissing baseline rows for `HEADROOM_MAIN`, 2,271 institutions, and 74.4 percent row coverage. The mean is about $13,845, and the FTFT-weighted mean is about $14,531. `HEADROOM_MAIN_SHARE_COA` has no values outside `[0, 1]`.

The component audit supports treating headroom as an allowance-margin measure rather than a tuition proxy. In the baseline sample, `HEADROOM_MAIN` is weakly correlated with in-state tuition and fees and strongly correlated with off-campus room and board.

## 7. Derived outcomes and controls

The main aid outcomes come from IPEDS Student Financial Aid fields for full-time, first-time students. The core derived outcomes include:

- institutional grants per FTFT cohort student
- institutional grant share of total grant aid
- Pell grants per FTFT cohort student
- Pell share of total grant aid
- federal loans per FTFT cohort student
- net-price income-band fields as secondary outcomes

Finance variables are controls and diagnostics, not the main measure of student aid packaging. Public and private nonprofit institutions report finance data under different accounting standards, so the repo builds sector-harmonized finance controls rather than treating all finance variables as identical across sectors.

Admissions are handled in two layers. `OPENADMP` enters the baseline because requiring admit rates or test scores would drop open-admissions schools by design. Admit rates, SAT fields, ACT fields, and the selectivity index are reserved for a selective-admissions sensitivity sample.

Ordinary enrollment and race-share controls are not in the current baseline. The verified local panel does not provide usable coverage for `ENRTOT`, `FTE`, or `PCTENR*` in this analysis sample. That is recorded as a data limitation, not treated as a theoretical claim that those controls do not matter.

## 8. Descriptive and data-quality audits

Before estimation, the repo writes descriptive and diagnostic files:

```bash
PYTHONPATH=src python scripts/build_descriptive_decomposition.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/descriptive_decomposition

PYTHONPATH=src python scripts/audit_extremes.py \
  --input-panel outputs/analysis_panel/public_private_nonprofit/analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet \
  --input-panel outputs/analysis_panel/public/analysis_panel_coa_headroom_2009_2023_public.parquet \
  --input-panel outputs/analysis_panel/private_nonprofit/analysis_panel_coa_headroom_2009_2023_private_nonprofit.parquet \
  --output-dir outputs/extreme_audit

PYTHONPATH=src python scripts/build_descstat_tables.py \
  --input-panel outputs/analysis_panel/public_private_nonprofit/analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet \
  --output-dir outputs/descriptive_tables \
  --config config/descstat_variables.csv \
  --scope-label public_private_nonprofit
```

The descriptive decomposition separates sector-year trends from same-institution component changes. The extreme-value audit profiles variables before any winsorization decision. The descriptive-statistics table reports raw and table-capped values side by side, but it does not change the analysis parquet.

## 9. Pre-estimation model plan

The model plan is in:

```text
config/model_specifications.csv
```

The plan is checked before estimation:

```bash
PYTHONPATH=src python scripts/audit_model_plan.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/model_plan \
  --config config/model_specifications.csv
```

Then each model sample is materialized:

```bash
PYTHONPATH=src python scripts/build_model_samples.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/model_samples \
  --config config/model_specifications.csv
```

This step writes one complete-case parquet per planned model and a manifest with rows, institutions, singleton institutions, weight checks, and within-focal-variation diagnostics. This is important because complete-case drops are visible before any regression runs.

The latest local run wrote all 25 planned baseline, sector-year, component, and sensitivity model samples and found no missing model variables. The main institutional-grant dollar model has 24,247 rows and 2,082 institutions. The public-sector institutional-grant model has 8,626 rows and 713 institutions. The private nonprofit model has 15,621 rows and 1,371 institutions.

## 10. Baseline estimation

The baseline estimates are institution and year fixed-effects models:

```text
Outcome_it = institution fixed effects + year fixed effects
           + beta Headroom_it + controls_it + error_it
```

The command is:

```bash
PYTHONPATH=src python scripts/run_fixed_effects.py \
  --sample-dir outputs/model_samples/samples \
  --output-dir outputs/fixed_effects \
  --config config/model_specifications.csv
```

The estimator:

- absorbs the fixed effects named in `config/model_specifications.csv`
- uses the focal variable and controls named in the config
- clusters standard errors by `UNITID`
- uses `SCFA1N` weights only for the configured weighted check
- reports rows, institutions, clusters, singleton clusters, within-focal variation, rank, and convergence diagnostics

Most baseline models absorb `UNITID` and `year`. The sector-year pooled checks absorb `UNITID` and `SECTOR_YEAR`, where `SECTOR_YEAR` is the sector-by-calendar-year cell. The current baseline run estimated all 25 planned baseline, sector-year, component, and sensitivity models with no rank-deficient models. The baseline validation reports 25 models observed and zero validation issues.

The headline fixed-effects estimates are association estimates. They describe whether headroom and aid outcomes move together within the same institution over time after absorbing institution and year effects. They do not prove student-level aid substitution, and they do not prove that institutions intentionally changed COA allowances.

## 11. Estimator validation

The fixed-effects output is validated before paper use:

```bash
PYTHONPATH=src python scripts/validate_fixed_effects_outputs.py \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/baseline_estimation_validation \
  --config config/model_specifications.csv
```

The headline focal coefficients are also cross-checked against `linearmodels.PanelOLS`:

```bash
PYTHONPATH=src python scripts/crosscheck_fixed_effects.py \
  --sample-dir outputs/model_samples/samples \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/fixed_effects_crosscheck \
  --config config/model_specifications.csv
```

The current cross-check covers all 25 configured baseline, sector-year, component, and sensitivity focal coefficients. No model was skipped, and no focal term failed the configured tolerance. The largest absolute coefficient difference is `3.69e-12`; the largest absolute standard-error difference is `1.85e-05`.

Estimate tables are then exported with:

```bash
PYTHONPATH=src python scripts/build_estimate_tables.py \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/estimate_tables
```

That script writes CSV, Markdown, LaTeX, and Word versions of the split fixed-effects tables: main institutional-grant estimates, aid-outcome diagnostics, sector checks, robustness checks, COA component checks, and a full appendix audit. The combined notebook `notebooks/table_exports.ipynb` rebuilds the descriptive-statistics tables, fixed-effects tables, and SVG figures, then lists the export paths.

Figures are exported with:

```bash
PYTHONPATH=src python scripts/build_report_figures.py
```

The figure builder writes SVG figures plus the source CSV for each figure under `outputs/figures/`.

## 12. Policy-exposure diagnostics

The policy-exposure layer is separate from the baseline fixed-effects estimates. The first design uses the 2017 restoration of year-round Pell Grants.

The national Pell policy registry is in:

```text
config/policy_shocks.csv
```

The registry is audited before any exposure model uses it:

```bash
PYTHONPATH=src python scripts/audit_policy_shocks.py \
  --config config/policy_shocks.csv \
  --output-dir outputs/policy_shocks
```

Because Pell changes are national, year fixed effects absorb the national policy timing. The estimable object is differential change by pre-period exposure:

```text
Outcome_it = institution fixed effects + year fixed effects
           + beta(Pell exposure_i x Post 2017_t)
           + controls_it + error_it
```

The first exposure measure is the institution's mean 2014-2016 Pell share of FTFT grant dollars, standardized within pre-period sector. The first policy design interacts that exposure with the 2017 restoration of year-round Pell. The second policy design interacts that exposure with annual changes in the maximum Pell Grant award. The preferred maximum-Pell version uses real award changes in 2023 dollars; nominal changes and large-increase flags are checks.

The exposure panel, policy model samples, policy fixed-effects estimates, and event-study coefficients are built in separate directories under `outputs/`.

The current policy-exposure estimates are useful as diagnostics. The 2017 headroom policy checks are cleaner: the 2016 placebo is not sharp, and the event-study leads are not sharp. The repeated real maximum-Pell headroom model is not statistically sharp. The nominal maximum-Pell headroom model is sharper, but that is not the preferred specification because nominal increases mix policy generosity with inflation. The institutional-grant policy results are not causal-ready because the 2016, sector-year 2016, and maximum-Pell institutional-grant placebo checks show differential pre-period movement.

## 13. Claim boundary

The current research path supports these claims:

- The project starts from a cleaned, documented IPEDS `UNITID` by `year` panel.
- The baseline sample is a four-year Title IV public and private nonprofit panel for 2009 through 2023.
- COA headroom is measured as a published institution-year non-tuition budget margin.
- The estimates describe within-institution associations between headroom and aid outcomes.
- Sector-specific results matter, especially because public and private nonprofit institutions have different pricing and finance settings.
- Policy-exposure estimates should be read only after placebo and event-study diagnostics.

The current research path does not support these claims:

- The estimates prove that institutions intentionally inflated COA.
- The estimates prove student-level grant substitution.
- The policy institutional-grant result is a clean causal estimate.
- The baseline sample represents the full postsecondary sector.

## 14. Where each decision is documented

| Topic | File |
| --- | --- |
| Upstream panel construction | `IPEDSDB_Panel/METHODS_PANEL_CONSTRUCTION.md` |
| Parent-child cleaning | `IPEDSDB_Panel/METHODS_PRCH_CLEANING.md` |
| Research data boundary | `docs/data_protocol.md` |
| Replication commands | `docs/replication.md` |
| Data decisions and source trail | `docs/data_decision_register.md` |
| Design justification | `docs/design_justification.md` |
| Research design | `docs/research_design.md` |
| Variable selection | `docs/variable_selection.md` |
| Sample dynamics | `docs/sample_dynamics.md` |
| Headroom definition | `docs/headroom_measurement.md` |
| Headroom audit | `docs/headroom_measurement_audit.md` |
| Descriptive decomposition | `docs/descriptive_decomposition.md` |
| Outlier audit | `docs/outlier_audit.md` |
| Pre-estimation checks | `docs/pre_estimation_readiness.md` |
| Baseline estimates | `docs/fixed_effects_baseline.md` |
| Estimator cross-check | `docs/estimator_validation.md` |
| Policy exposure design | `docs/policy_exposure_design.md` |
| Policy estimates | `docs/policy_exposure_estimates.md` |

## 15. Short version for discussion

I first built the IPEDS panel in `IPEDSDB_Panel` from final NCES Access databases and kept the cleaned output as an unbalanced `UNITID` by `year` panel. I then used `COA_FINAID_SUBS` as the paper repo. It reads the clean panel, applies the four-year Title IV public and private nonprofit sample rule, builds the cost-of-attendance headroom measures, audits missingness and panel structure, writes sector-specific samples, materializes complete-case model files, and only then estimates fixed-effects models. The baseline estimates are within-institution associations, not causal policy estimates. The separate Pell policy-exposure layer is treated as diagnostic unless placebo and event-study checks support stronger language.
