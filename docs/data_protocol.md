# Data Protocol

This repository uses `IPEDSDB_Panel` as the upstream data-construction source. It does not rebuild IPEDS Access databases and does not edit the canonical clean panel.

## Inputs

Required local inputs:

- `panel_clean_analysis_2004_2023.parquet`
- `dictionary_lake.parquet`

Recommended source location:

```text
$IPEDSDB_ROOT/Panels/panel_clean_analysis_2004_2023.parquet
$IPEDSDB_ROOT/Dictionary/dictionary_lake.parquet
```

## First analysis sample

The default sample is four-year Title IV institutions:

```text
PSET4FLG = 1
SECTOR in (1, 2, 3)
year = 2009:2023
```

The 2009 start follows the first non-null year for the COA component fields used to build headroom measures. Net-price income bands begin later and are treated as secondary diagnostics.

## Data integrity rules

The first preparation script enforces:

- one row per `UNITID` and `year`
- no missing `UNITID` or `year`
- required research variables present
- explicit sample counts before and after filtering
- nonnegative checks for core COA and aid money variables
- raw net-price values retained
- negative net-price values flagged and copied to cleaned fields with negatives set missing
- SHA-256 hashes for the input panel, input dictionary, and output analysis parquet

## Generated files

Generated files belong in `outputs/` and are ignored by Git unless a small summary is intentionally added for release documentation.

