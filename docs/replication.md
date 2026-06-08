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
- derived COA and headroom variables
- cleaned net-price diagnostics
- sector-harmonized finance controls
- IPEDS metadata exposure flags for imputation, revisions, and parent-linked records
- admissions, location, mission, and student-body controls
- manifest and audit tables documenting all selected variables

The justification for each sample, variable, and cleaning rule is recorded in `docs/data_decision_register.md`.

The exact row count depends on the upstream panel file hash. With the local input I verified on June 8, 2026, the baseline sample contained 35,443 institution-years and 2,774 institutions. The public-sector file contained 11,215 institution-years and 882 institutions. The private nonprofit file contained 24,228 institution-years and 1,903 institutions. Each extract wrote 335 columns. The selected raw-variable contract contained 215 variables, all present in the source panel.
