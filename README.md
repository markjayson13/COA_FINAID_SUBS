# COA_FINAID_SUBS

Research code for the Cost of Attendance headroom and financial-aid substitution project.

This repository is separate from `IPEDSDB_Panel`. `IPEDSDB_Panel` builds the research-grade NCES/IPEDS panel. This repository uses the released clean panel as an input and owns the analysis sample, variable selection, constructed measures, integrity checks, and replication materials for the paper.

## Current first-stage task

Build an analysis-ready extract from:

```text
panel_clean_analysis_2004_2023.parquet
dictionary_lake.parquet
```

The default analysis sample is:

```text
PSET4FLG = 1
SECTOR in (1, 2, 3)
year = 2009:2023
```

The source panel is not modified. The script writes a derived analysis parquet and audit artifacts under `outputs/`.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run

Set `IPEDSDB_ROOT` to the local panel build root:

```bash
export IPEDSDB_ROOT="/Users/markjaysonfarol13/Projects/IPEDSDB_Paneling"
python scripts/prepare_analysis_panel.py
```

Or pass paths directly:

```bash
python scripts/prepare_analysis_panel.py \
  --input-panel "/path/to/panel_clean_analysis_2004_2023.parquet" \
  --dictionary "/path/to/dictionary_lake.parquet" \
  --output-dir outputs/analysis_panel
```

## Outputs

The script writes:

- `analysis_panel_coa_headroom_2009_2023.parquet`
- `analysis_build_summary.json`
- `analysis_variable_manifest.csv`
- `analysis_sample_counts.csv`
- `analysis_missingness_by_year.csv`
- `analysis_value_sanity.csv`

Generated data are ignored by Git. Public replication materials should include code, configuration, documentation, and small audit summaries, not the large source panel.

## Test

```bash
python -m pytest
```

