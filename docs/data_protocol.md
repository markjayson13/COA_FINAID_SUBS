# Data protocol

This document records the data boundary for the paper repository. I keep the IPEDS construction work in `IPEDSDB_Panel`; this repository starts from the released clean panel and builds the research extract used for analysis.

The point of the protocol is simple: a reader should be able to see where the input data came from, how the sample is defined, what the preparation script checks, and which files are generated locally.

The source trail for each sample, variable, and cleaning decision is in `docs/data_decision_register.md`.

## Inputs

The first preparation script requires two local files:

- `panel_clean_analysis_2004_2023.parquet`
- `dictionary_lake.parquet`

By default, the script looks for them under:

```text
$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet
$IPEDSDB_ROOT/Dictionary/dictionary_lake.parquet
```

## First analysis sample

The default sample keeps four-year Title IV public and private nonprofit institutions:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

Rows with missing `PSET4FLG` or `SECTOR` fail the sample mask and are excluded from this extract. The build reports those rows in `analysis_sample_counts.csv` as `year_window_missing_pset4flg_or_sector` before writing the final analysis sample.

The 2009 start follows the first non-null year for the cost-of-attendance component fields used to build headroom measures. Net-price income bands begin later, so the script keeps them as secondary diagnostics rather than primary sample requirements.

Private for-profit institutions are outside the baseline estimand. They remain buildable as a diagnostic sample with `--sectors 3`.

The default command also writes public-only and private nonprofit-only extracts. Those sector files are built from the same source panel and the same variable contract, but they live in separate output directories:

```text
outputs/analysis_panel/public_private_nonprofit/
outputs/analysis_panel/public/
outputs/analysis_panel/private_nonprofit/
```

## Data integrity rules

Before writing the analysis panel, the script checks:

- one row per `UNITID` and `year`
- no missing `UNITID` or `year`
- required research variables present
- explicit sample counts before and after filtering
- panel balance by institution
- first and last observed years within the analysis window
- entry and exit reason audit based on full-panel status, `PSET4FLG`, and `SECTOR`
- institution-years by sector and year
- retention under minimum observed-year requirements
- open-admissions status as the baseline admissions control
- a separate selective-admissions robustness panel for admit-rate and test-score measures
- documented exclusion of ordinary enrollment and race-share controls with unusable local coverage
- nonnegative checks for core COA and aid money variables
- headroom-measure coverage, component, correlation, and FTFT-cohort-weighted summaries
- sector-year descriptive decomposition and same-institution COA component changes
- complete-case model samples with singleton and within-variation diagnostics
- aid-zero consistency checks across counts, percentages, averages, and totals
- all-variable distribution and extreme-value audit before any winsorization decision
- reviewer-facing model cards and sample-attrition rows after estimation
- raw net-price values retained
- negative net-price values flagged and copied to cleaned fields with negatives set missing
- raw IPEDS imputation, revision, collection-status, and parent-child fields retained where available
- component-level flags for imputed, revised, or parent-linked records
- SHA-256 hashes for the input panel, input dictionary, and output analysis parquet

The selected variable file is also auditable against the source panel. The audit reports column presence, coverage by variable, coverage by variable group, and complete-case counts for the main empirical scenarios. The audit uses the same sector directories as the analysis-panel build. This matters because some IPEDS fields are sector-specific or only begin in later years. The net-price income-band fields are handled this way: public rows use `NPIS*`, private rows use `NPT*`, and the script writes harmonized `NET_PRICE_*` fields.

IPEDS `year` is a panel index, not a single event date shared by every component. COA, Student Financial Aid, admissions, and finance fields can refer to different survey windows, fall snapshots, aid years, or fiscal years. The repository keeps these fields in the same institution-year panel for analysis, but the paper should not describe all variables in year `t` as if they were measured at the same moment.

Admissions variables are handled in two layers. `OPENADMP` is kept in the baseline. Admit rates, yield, SAT score ranges, and ACT score ranges are derived in the analysis panel but are assigned to the selective-admissions robustness sample, not the main sample definition.

Ordinary enrollment and race-share controls are not used in the current baseline. The local clean panel does not provide usable coverage for `ENRTOT`, `FTE`, or the `PCTENR*` race-share family in this analysis sample. I keep the student-body controls to fields with usable coverage in the current extract, mainly SFA cohort counts and institutional flags. If the upstream panel later restores ordinary enrollment and race-share coverage, those controls should enter as a documented sensitivity, not as an undocumented change to the baseline.

Headroom is handled as a family of measures. `HEADROOM_MAIN` is the preferred published non-tuition COA margin. The audit checks its normalized versions, its component fields, its living-arrangement alternatives, and `SCFA1N`-weighted means. This keeps the paper from relying on a single unaudited aggregate field.

FTFT aid outcomes and all-undergraduate aid outcomes answer related but different questions. The main models use FTFT SFA outcomes because they are closest to the pricing and aid cohort used in the COA and net-price reporting logic. All-undergraduate aid fields remain in the extract for broader checks, but they should not be described as the same estimand.

The descriptive decomposition holds institutions fixed for component-change tables. That prevents panel entry or exit from being confused with COA growth. Model samples are also materialized before estimation so complete-case decisions are visible outside the regression code.

The metadata fields are kept in two forms. The raw `IMP_*`, `LOCK_*`, `REV_*`, `IDX_*`, `PRCH_*`, and parent-child allocation fields remain in the extract. The script also writes conservative derived flags. A component is flagged as imputed when its `IMP_*` code is neither the baseline reported code nor the not-applicable code. It is flagged as revised when `REV_*` equals one. It is flagged as parent-linked when IPEDS reports a parent `UNITID` in `IDX_*` or a positive parent-child allocation factor. The audit also writes raw code counts for `IMP_*`, `LOCK_*`, `REV_*`, and `PRCH_*` fields.

The entry and exit tables use first and last observed years within this research window. They do not, by themselves, prove that an institution opened or closed. An institution first observed after 2009 may be a true entrant, a campus that became eligible for this sample, or a record whose reporting status changed. An institution last observed before 2023 may have closed, merged, changed sector, left Title IV, or stopped meeting the four-year sample rule.

The policy-exposure layer keeps national policy registries separate from the analysis panel. `config/policy_shocks.csv` records Pell schedule changes. `config/policy_price_index.csv` records CPI-U annual averages for real maximum Pell calculations. The exposure builder merges those files only when writing policy-exposure panels.

The current policy-exposure layer is diagnostic for the WEAI paper. A later causal paper should add external variation before making stronger incidence claims. Candidate extensions include state-appropriations shocks for public institutions and local housing-cost shocks for allowance-based headroom. Those extensions would require new merged data, exposure audits, and placebo checks.

The current observed panel ends in 2023. Later aid-packaging rules can motivate the policy section, but they are outside this analysis window unless a later IPEDS panel and new policy design are added.

Outlier handling is audit-first. The repository now writes all-variable distribution profiles and review-candidate tables, but it does not winsorize the panel by default. Any cap, trim, or transformation rule should be added later as a named sensitivity with a variable-level reason.

The descriptive-statistics table uses limited winsorization for display only. The cap rules live in `config/descstat_variables.csv`, and the table builder writes raw and capped means side by side. This does not alter the analysis parquet and does not make winsorization part of the baseline estimating sample.

After estimation, `scripts/build_reviewer_tables.py` writes model cards, sample-attrition rows, and a metadata glossary. These tables do not create new estimates. They put the model formula, fixed effects, controls, complete-case loss, clusters, diagnostics, and metadata flag definitions in one auditable place.

## Generated files

Generated files belong in `outputs/` and are ignored by Git. I commit the code and documentation needed to rebuild them, not the generated data files themselves.
