# Data protocol

This document records the data boundary for the paper repository. I keep the IPEDS construction work in `IPEDSDB_Panel`; this repository starts from the released clean panel and builds the research extract used for analysis.

The point of the protocol is simple: a reader should be able to see where the input data came from, how the sample is defined, what the preparation script checks, and which files are generated locally.

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

The default sample keeps four-year Title IV institutions:

```text
PSET4FLG = 1
SECTOR in (1, 2, 3)
year = 2009:2023
```

The 2009 start follows the first non-null year for the cost-of-attendance component fields used to build headroom measures. Net-price income bands begin later, so the script keeps them as secondary diagnostics rather than primary sample requirements.

## Data integrity rules

Before writing the analysis panel, the script checks:

- one row per `UNITID` and `year`
- no missing `UNITID` or `year`
- required research variables present
- explicit sample counts before and after filtering
- nonnegative checks for core COA and aid money variables
- raw net-price values retained
- negative net-price values flagged and copied to cleaned fields with negatives set missing
- SHA-256 hashes for the input panel, input dictionary, and output analysis parquet

## Generated files

Generated files belong in `outputs/` and are ignored by Git. I commit the code and documentation needed to rebuild them, not the generated data files themselves.
