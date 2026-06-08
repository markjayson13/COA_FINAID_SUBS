# Replication notes

These notes are for readers who want to rebuild the first analysis extract from the clean IPEDS panel. The code expects a local build of the panel produced by [`markjayson13/IPEDSDB_Panel`](https://github.com/markjayson13/IPEDSDB_Panel).

The generated analysis files are intentionally left out of Git. Rebuilding them locally is part of the replication trail.

## Minimal run

```bash
export IPEDSDB_ROOT="/path/to/IPEDSDB_Paneling"
python scripts/prepare_analysis_panel.py
```

## Direct-path run

```bash
python scripts/prepare_analysis_panel.py \
  --input-panel "$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet" \
  --dictionary "$IPEDSDB_ROOT/Dictionary/dictionary_lake.parquet" \
  --output-dir outputs/analysis_panel \
  --years 2009:2023 \
  --sectors 1,2,3
```

## Variable audit

```bash
python scripts/audit_variable_config.py \
  --input-panel "$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet" \
  --output-dir outputs/variable_audit \
  --years 2009:2023 \
  --sectors 1,2,3
```

## Expected first-stage outputs

The default first-stage extract writes:

- a four-year Title IV sample for 2009-2023
- derived COA and headroom variables
- cleaned net-price diagnostics
- sector-harmonized finance controls
- IPEDS metadata exposure flags for imputation, revisions, and parent-linked records
- admissions, location, mission, and student-body controls
- manifest and audit tables documenting all selected variables

The exact row count depends on the upstream panel file hash. With the local input I verified on June 8, 2026, the primary sample contained 43,476 institution-years and 3,769 institutions. The expanded extract wrote 335 columns. The selected raw-variable contract contained 215 variables, all present in the source panel.
