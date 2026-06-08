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

The default sample keeps four-year Title IV public and private nonprofit institutions:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

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
- nonnegative checks for core COA and aid money variables
- raw net-price values retained
- negative net-price values flagged and copied to cleaned fields with negatives set missing
- raw IPEDS imputation, revision, collection-status, and parent-child fields retained where available
- component-level flags for imputed, revised, or parent-linked records
- SHA-256 hashes for the input panel, input dictionary, and output analysis parquet

The selected variable file is also auditable against the source panel. The audit reports column presence, coverage by variable, coverage by variable group, and complete-case counts for the main empirical scenarios. The audit uses the same sector directories as the analysis-panel build. This matters because some IPEDS fields are sector-specific or only begin in later years. The net-price income-band fields are handled this way: public rows use `NPIS*`, private rows use `NPT*`, and the script writes harmonized `NET_PRICE_*` fields.

The metadata fields are kept in two forms. The raw `IMP_*`, `LOCK_*`, `REV_*`, `IDX_*`, `PRCH_*`, and parent-child allocation fields remain in the extract. The script also writes conservative derived flags. A component is flagged as imputed when its `IMP_*` code is neither the baseline reported code nor the not-applicable code. It is flagged as revised when `REV_*` equals one. It is flagged as parent-linked when IPEDS reports a parent `UNITID` in `IDX_*` or a positive parent-child allocation factor. The audit also writes raw code counts for `IMP_*`, `LOCK_*`, `REV_*`, and `PRCH_*` fields.

## Generated files

Generated files belong in `outputs/` and are ignored by Git. I commit the code and documentation needed to rebuild them, not the generated data files themselves.
