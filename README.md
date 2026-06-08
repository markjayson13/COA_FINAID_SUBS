# COA_FINAID_SUBS

This is the public research repository for my project on cost-of-attendance headroom and institutional grant substitution in Title IV higher education finance.

The repository is meant for readers who want to inspect the empirical work behind the paper: how I define the analysis sample, which IPEDS variables enter the study, how I construct the first analysis panel, and what checks run before any estimates are produced.

## Project boundary

This project starts from a clean IPEDS panel. It does not rebuild the raw NCES/IPEDS Access databases.

The upstream panel is produced in [`markjayson13/IPEDSDB_Panel`](https://github.com/markjayson13/IPEDSDB_Panel). This repository treats that panel as an input and owns the research layer: sample definition, variable selection, constructed measures, validation checks, and replication materials for this paper.

The first preparation script reads:

```text
panel_clean_analysis_2004_2023.parquet
dictionary_lake.parquet
```

The default analysis sample is four-year Title IV public and private nonprofit institutions:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

Private for-profit institutions are not part of the baseline sample. They can be built as a diagnostic sample by passing `--sectors 3`.

The script does not modify the source panel. It writes a derived analysis parquet and audit tables under `outputs/`, which are ignored by Git.

## What is here

- `config/analysis_variables.csv` lists the raw IPEDS variables selected for the research extract.
- `src/coa_finaid_subs/prepare_analysis_panel.py` contains the preparation and validation logic.
- `scripts/prepare_analysis_panel.py` is the command-line entry point.
- `scripts/audit_variable_config.py` checks the selected variables against the real panel.
- `docs/data_protocol.md` describes the data boundary, sample rule, and integrity checks.
- `docs/variable_selection.md` explains the variable families and what is treated as primary, secondary, or control material.
- `docs/replication.md` gives the minimum commands needed to rebuild the first extract.
- `tests/` covers the main data-integrity checks with small synthetic panels.

This repository currently covers the first analysis-panel build. Estimation scripts, tables, and manuscript exhibits will be added after the sample and variable checks are final.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Build the analysis panel

Set `IPEDSDB_ROOT` to the local panel build root:

```bash
export IPEDSDB_ROOT="/Users/markjaysonfarol13/Projects/IPEDSDB_Paneling"
python scripts/prepare_analysis_panel.py
```

You can also pass paths directly:

```bash
python scripts/prepare_analysis_panel.py \
  --input-panel "/path/to/panel_clean_analysis_2004_2023.parquet" \
  --dictionary "/path/to/dictionary_lake.parquet" \
  --output-dir outputs/analysis_panel
```

## Outputs

The script writes:

- `analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet`
- `analysis_build_summary.json`
- `analysis_variable_manifest.csv`
- `analysis_sample_counts.csv`
- `analysis_missingness_by_year.csv`
- `analysis_value_sanity.csv`
- `analysis_metadata_flag_summary.csv`
- `analysis_metadata_code_summary.csv`

The variable audit writes:

- `variable_config_coverage.csv`
- `variable_group_coverage.csv`
- `complete_case_scenarios.csv`
- `metadata_flag_summary.csv`
- `metadata_code_summary.csv`

Generated data are not committed to this repository. The public materials are the code, configuration, documentation, tests, and small audit summaries that let another researcher rebuild and inspect the extract.

## Run checks

```bash
python -m pytest
```

## Contact

For questions about the project, use the contact information on [markjayson.com](https://markjayson.com).
