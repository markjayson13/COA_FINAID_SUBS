# Replication Notes

The analysis code expects a local build of the IPEDS panel produced by `markjayson13/IPEDSDB_Panel`.

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

## Expected first-stage outputs

The default first-stage extract should produce:

- a four-year Title IV sample for 2009-2023
- derived COA and headroom variables
- cleaned net-price diagnostics
- manifest and audit tables documenting all selected variables

The exact row count depends on the upstream panel file hash. With the current local input verified on June 8, 2026, the expected primary sample was 43,476 institution-years and 3,769 institutions.

