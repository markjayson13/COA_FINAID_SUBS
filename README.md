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

Private for-profit institutions are not part of the baseline sample. They can be built as a diagnostic sample by passing `--sectors 3` or by adding `--include-forprofit-diagnostic` to the default run.

The script does not modify the source panel. It writes a derived analysis parquet and audit tables under `outputs/`, which are ignored by Git.

## What is here

- `config/analysis_variables.csv` lists the raw IPEDS variables selected for the research extract.
- `config/descstat_variables.csv` lists the variables and caps used for descriptive-statistics exhibits.
- `config/model_specifications.csv` lists the first planned model specifications before estimation code is added.
- `src/coa_finaid_subs/prepare_analysis_panel.py` contains the preparation and validation logic.
- `scripts/prepare_analysis_panel.py` is the command-line entry point.
- `scripts/audit_variable_config.py` checks the selected variables against the real panel.
- `scripts/build_descstat_tables.py` builds the paper and appendix descriptive-statistics tables.
- `scripts/audit_model_plan.py` checks planned model variables and complete-case counts before estimation.
- `notebooks/01_descstat_pre_post_winsorization.ipynb` rebuilds and displays the descriptive-statistics tables.
- `docs/data_protocol.md` describes the data boundary, sample rule, and integrity checks.
- `docs/data_decision_register.md` links each sample, variable, and cleaning decision to code and source support.
- `docs/research_design.md` fixes the first paper design, claim boundaries, and model sequence.
- `docs/variable_selection.md` explains the variable families and what is treated as primary, secondary, or control material.
- `docs/selectivity_index.md` documents the open-admissions baseline control and the selective-admissions robustness index.
- `docs/sample_dynamics.md` records panel balance, entry/exit definitions, sector-year counts, and external NCES context for the institution-count decline.
- `docs/replication.md` gives the minimum commands needed to rebuild the first extract.
- `docs/outlier_audit.md` describes the audit-only distribution and extreme-value review before any winsorization decision.
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

The default run writes three scopes:

- `public_private_nonprofit`, the baseline sample
- `public`, the public-sector sample
- `private_nonprofit`, the private nonprofit sample

You can also pass paths directly:

```bash
python scripts/prepare_analysis_panel.py \
  --input-panel "/path/to/panel_clean_analysis_2004_2023.parquet" \
  --dictionary "/path/to/dictionary_lake.parquet" \
  --output-dir outputs/analysis_panel
```

## Outputs

The preparation script writes each scope under its own directory, for example:

```text
outputs/analysis_panel/public_private_nonprofit/
outputs/analysis_panel/public/
outputs/analysis_panel/private_nonprofit/
```

Each directory contains:

- `analysis_panel_coa_headroom_2009_2023_<scope>.parquet`
- `analysis_panel_selective_admissions_robustness_2009_2023_<scope>.parquet`
- `analysis_build_summary.json`
- `analysis_variable_manifest.csv`
- `analysis_sample_counts.csv`
- `analysis_panel_balance_by_institution.csv`
- `analysis_panel_balance_summary.csv`
- `analysis_entry_exit_by_sector_year.csv`
- `analysis_entry_exit_reason_audit.csv`
- `analysis_institution_years_by_sector_year.csv`
- `analysis_min_years_sensitivity.csv`
- `analysis_selectivity_summary.csv`
- `analysis_missingness_by_year.csv`
- `analysis_value_sanity.csv`
- `analysis_aid_zero_consistency.csv`
- `analysis_aid_zero_suspect_rows.csv`
- `analysis_metadata_flag_summary.csv`
- `analysis_metadata_code_summary.csv`

For example, the public-only output is named `analysis_panel_coa_headroom_2009_2023_public.parquet`.

The variable audit follows the same directory layout under `outputs/variable_audit/`. Each scope directory contains:

- `variable_config_coverage.csv`
- `variable_group_coverage.csv`
- `complete_case_scenarios.csv`
- `metadata_flag_summary.csv`
- `metadata_code_summary.csv`

The descriptive-statistics script writes table files under `outputs/descriptive_tables/`. For the baseline scope, it writes:

- `descstat_paper_pre_post_winsor.csv`
- `descstat_paper_pre_post_winsor.tex`
- `descstat_paper_pre_post_winsor.docx`
- `descstat_appendix_pre_post_winsor.csv`
- `descstat_appendix_pre_post_winsor.tex`
- `descstat_appendix_pre_post_winsor.docx`
- `descstat_full_pre_post_winsor.csv`
- `descstat_summary.json`

The model-plan audit writes:

- `outputs/model_plan/model_specification_coverage.csv`
- `outputs/model_plan/model_plan_summary.json`

Generated data are not committed to this repository. The public materials are the code, configuration, documentation, tests, and small audit summaries that let another researcher rebuild and inspect the extract.

## Run checks

```bash
python -m pytest
```

## Contact

For questions about the project, use the contact information on [markjayson.com](https://markjayson.com).
