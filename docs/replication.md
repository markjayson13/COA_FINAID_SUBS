# Replication notes

These notes are for readers who want to rebuild the first analysis extract from the clean IPEDS panel. The code expects a local build of the panel produced by [`markjayson13/IPEDSDB_Panel`](https://github.com/markjayson13/IPEDSDB_Panel).

The generated analysis files are intentionally left out of Git. Rebuilding them locally is part of the replication trail.

## Minimal run

```bash
export IPEDSDB_ROOT="/path/to/IPEDSDB_Paneling"
python scripts/prepare_analysis_panel.py
```

This writes the baseline sample and the two sector splits:

```text
outputs/analysis_panel/public_private_nonprofit/
outputs/analysis_panel/public/
outputs/analysis_panel/private_nonprofit/
```

## Direct-path run

```bash
python scripts/prepare_analysis_panel.py \
  --input-panel "$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet" \
  --dictionary "$IPEDSDB_ROOT/Dictionary/dictionary_lake.parquet" \
  --output-dir outputs/analysis_panel \
  --years 2009:2023
```

## Variable audit

```bash
python scripts/audit_variable_config.py \
  --input-panel "$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet" \
  --output-dir outputs/variable_audit \
  --years 2009:2023
```

The audit uses the same scope directories as the analysis-panel build.

To rebuild one scope only, pass `--sectors`. For the baseline sample:

```bash
python scripts/prepare_analysis_panel.py \
  --input-panel "$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet" \
  --dictionary "$IPEDSDB_ROOT/Dictionary/dictionary_lake.parquet" \
  --output-dir outputs/analysis_panel \
  --years 2009:2023 \
  --sectors 1,2
```

## For-profit diagnostic run

Private for-profit institutions are not part of the baseline sample. To inspect them separately:

```bash
python scripts/prepare_analysis_panel.py \
  --input-panel "$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet" \
  --dictionary "$IPEDSDB_ROOT/Dictionary/dictionary_lake.parquet" \
  --output-dir outputs/analysis_panel \
  --years 2009:2023 \
  --sectors 3
```

To write the diagnostic beside the default scopes in one command, add `--include-forprofit-diagnostic` to the minimal or direct-path run.

## Expected first-stage outputs

The default first-stage extract writes:

- a public and private nonprofit four-year Title IV sample for 2009-2023
- public-only and private nonprofit-only sector files for the same years
- panel balance, first/last observed year, sector-year count, and minimum-years sensitivity tables
- a separate selective-admissions robustness panel and selectivity summary
- derived COA and headroom variables, including the preferred `HEADROOM_MAIN` aliases
- aid-zero consistency summaries and suspect-row diagnostics
- cleaned net-price diagnostics
- sector-harmonized finance controls
- IPEDS metadata exposure flags for imputation, revisions, and parent-linked records
- admissions, location, mission, and student-body controls
- manifest and audit tables documenting all selected variables

The justification for each sample, variable, and cleaning rule is recorded in `docs/data_decision_register.md`.

To audit the headroom measurement family after the panels are built:

```bash
PYTHONPATH=src python scripts/audit_headroom_measures.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/headroom_measures \
  --config config/headroom_measures.csv
```

This writes coverage, sector-year, correlation, and FTFT-cohort-weighted summaries for the main headroom measure and its component checks. It does not estimate regressions.

The current checked-in summary of those generated files is `docs/headroom_measurement_audit.md`.

To rebuild the first descriptive decomposition:

```bash
PYTHONPATH=src python scripts/build_descriptive_decomposition.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/descriptive_decomposition
```

This writes sector-year trends and same-institution COA component changes. The current checked-in summary is `docs/descriptive_decomposition.md`.

To audit distributions and extreme values after the panels are built:

```bash
PYTHONPATH=src python scripts/audit_extremes.py \
  --input-panel outputs/analysis_panel/public_private_nonprofit/analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet \
  --input-panel outputs/analysis_panel/public/analysis_panel_coa_headroom_2009_2023_public.parquet \
  --input-panel outputs/analysis_panel/private_nonprofit/analysis_panel_coa_headroom_2009_2023_private_nonprofit.parquet \
  --output-dir outputs/extreme_audit
```

To rebuild the descriptive-statistics table for the paper and the appendix:

```bash
PYTHONPATH=src python scripts/build_descstat_tables.py \
  --input-panel outputs/analysis_panel/public_private_nonprofit/analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet \
  --output-dir outputs/descriptive_tables \
  --config config/descstat_variables.csv \
  --scope-label public_private_nonprofit
```

The same table can be inspected in `notebooks/table_exports.ipynb`. The notebook has no saved output; it rebuilds the tables from the local panel.

The table builder writes CSV, Markdown, LaTeX, and Word `.docx` files for both the shorter paper table and the longer appendix table. The Markdown files are useful as paste-ready previews; the Word and LaTeX files are the manuscript exports.

The same notebook rebuilds both the descriptive-statistics and fixed-effects manuscript tables.

To check planned model samples before writing estimation code:

```bash
PYTHONPATH=src python scripts/audit_model_plan.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/model_plan \
  --config config/model_specifications.csv
```

This writes complete-case counts and missing-variable checks for the model plan. It does not estimate regressions.

To materialize complete-case samples for the planned models:

```bash
PYTHONPATH=src python scripts/build_model_samples.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/model_samples \
  --config config/model_specifications.csv
```

This writes one complete-case parquet per model and a sample manifest. The current checked-in summary is `docs/pre_estimation_readiness.md`.

To estimate the configured institution and year fixed-effects models:

```bash
PYTHONPATH=src python scripts/run_fixed_effects.py \
  --sample-dir outputs/model_samples/samples \
  --output-dir outputs/fixed_effects \
  --config config/model_specifications.csv
```

This writes coefficient tables and model diagnostics. The current checked-in summary is `docs/fixed_effects_baseline.md`.

To export the current estimate tables:

```bash
PYTHONPATH=src python scripts/build_estimate_tables.py \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/estimate_tables
```

This writes CSV, Markdown, LaTeX, and Word versions of the main, diagnostic, sector, robustness, component, and appendix fixed-effects tables.

To export the current figures:

```bash
PYTHONPATH=src python scripts/build_report_figures.py
```

This writes SVG figures and matching figure-data CSV files under `outputs/figures/`.

To build reviewer-facing model cards, sample-attrition rows, and the metadata glossary:

```bash
PYTHONPATH=src python scripts/build_reviewer_tables.py
```

This writes `outputs/reviewer_tables/`. The files summarize the configured models, complete-case loss, estimation diagnostics, and metadata flags for appendix review.

To audit the Pell policy-shock registry before building any exposure design:

```bash
PYTHONPATH=src python scripts/audit_policy_shocks.py \
  --config config/policy_shocks.csv \
  --output-dir outputs/policy_shocks
```

This checks the verified Federal Student Aid source registry and writes policy-shock audit tables. It does not estimate policy-exposure models.

To build the first policy-exposure panels:

```bash
PYTHONPATH=src python scripts/build_policy_exposure_panels.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/policy_exposure \
  --policy-config config/policy_shocks.csv \
  --design-config config/policy_exposure_designs.csv \
  --price-index-config config/policy_price_index.csv
```

The exposure panel includes the 2017 year-round Pell design and the repeated maximum Pell design. The repeated-shock design uses real maximum Pell changes in 2023 dollars, with nominal and large-increase checks.

To check the policy-exposure model samples before estimation:

```bash
PYTHONPATH=src python scripts/audit_model_plan.py \
  --panel-dir outputs/policy_exposure \
  --output-dir outputs/policy_model_plan \
  --config config/policy_exposure_model_specifications.csv
```

To materialize policy-exposure model samples:

```bash
PYTHONPATH=src python scripts/build_model_samples.py \
  --panel-dir outputs/policy_exposure \
  --output-dir outputs/policy_model_samples \
  --config config/policy_exposure_model_specifications.csv
```

To estimate the policy-exposure models:

```bash
PYTHONPATH=src python scripts/run_fixed_effects.py \
  --sample-dir outputs/policy_model_samples/samples \
  --output-dir outputs/policy_fixed_effects \
  --config config/policy_exposure_model_specifications.csv
```

To export the policy event-study coefficients:

```bash
PYTHONPATH=src python scripts/build_policy_event_study_table.py \
  --fixed-effects-dir outputs/policy_fixed_effects \
  --output-dir outputs/policy_event_study
```

To validate fixed-effects outputs before paper use:

```bash
PYTHONPATH=src python scripts/validate_fixed_effects_outputs.py \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/baseline_estimation_validation \
  --config config/model_specifications.csv
```

For the policy-exposure models, the hard validation command is:

```bash
PYTHONPATH=src python scripts/validate_fixed_effects_outputs.py \
  --fixed-effects-dir outputs/policy_fixed_effects \
  --output-dir outputs/policy_estimation_validation \
  --config config/policy_exposure_model_specifications.csv
```

That policy validation currently flags the 2016 institutional-grant placebo check. To inspect only numerical estimation checks, pass `--skip-placebo-signal-check`.

To cross-check headline fixed-effects estimates against a standard Python panel estimator, install the optional validation dependency and run:

```bash
python -m pip install '.[validation]'

PYTHONPATH=src python scripts/crosscheck_fixed_effects.py \
  --sample-dir outputs/model_samples/samples \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/fixed_effects_crosscheck \
  --config config/model_specifications.csv
```

This check is separate from the built-in estimator. It verifies all configured focal coefficients that the standard panel estimator supports, including the sector-year fixed-effect checks. It is not a replacement for the transparent local estimator.

The exact row count depends on the upstream panel file hash. With the local input I verified on June 9, 2026, the baseline sample contained 35,443 institution-years and 2,774 institutions. The public-sector file contained 11,215 institution-years and 882 institutions. The private nonprofit file contained 24,228 institution-years and 1,903 institutions. Each extract wrote 355 columns. The selected raw-variable contract contained 215 variables, all present in the source panel.
