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

The same table can be inspected in `notebooks/01_descstat_pre_post_winsorization.ipynb`. The notebook has no saved output; it rebuilds the tables from the local panel.

The table builder writes CSV, LaTeX, and Word `.docx` files for both the shorter paper table and the longer appendix table.

To check planned model samples before writing estimation code:

```bash
PYTHONPATH=src python scripts/audit_model_plan.py \
  --panel-dir outputs/analysis_panel \
  --output-dir outputs/model_plan \
  --config config/model_specifications.csv
```

This writes complete-case counts and missing-variable checks for the model plan. It does not estimate regressions.

The exact row count depends on the upstream panel file hash. With the local input I verified on June 8, 2026, the baseline sample contained 35,443 institution-years and 2,774 institutions. The public-sector file contained 11,215 institution-years and 882 institutions. The private nonprofit file contained 24,228 institution-years and 1,903 institutions. Each extract wrote 335 columns. The selected raw-variable contract contained 215 variables, all present in the source panel.
