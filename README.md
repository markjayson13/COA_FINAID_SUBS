# COA_FINAID_SUBS

This repository contains the public replication layer for my research on cost-of-attendance headroom and institutional grant aid in Title IV higher education finance.

It starts from a clean IPEDS institution-year panel produced upstream in [`markjayson13/IPEDSDB_Panel`](https://github.com/markjayson13/IPEDSDB_Panel). This repository does not rebuild the raw NCES/IPEDS Access databases. It defines the research sample, constructs the cost-of-attendance measures, audits the selected variables, materializes model samples, and estimates the institution-level fixed-effects models used in the paper.

## Scope

The baseline sample is four-year Title IV public and private nonprofit institutions from 2009 through 2023:

```text
PSET4FLG = 1
SECTOR in (1, 2)
year = 2009:2023
```

Private for-profit institutions are outside the baseline sample. They remain available only as a diagnostic build.

Generated data files are not committed. The repository publishes the code, configuration, documentation, notebooks, and tests needed to rebuild the analysis from the clean upstream panel.

## Claim Boundary

The project studies institution-year associations between published non-tuition cost-of-attendance headroom and full-time, first-time aid outcomes. The baseline estimates are not student-level packaging estimates and are not causal policy estimates.

Use this language when describing the project:

- cost-of-attendance headroom is a published institution-year non-tuition budget margin
- the main aid outcomes use full-time, first-time Student Financial Aid fields
- public and private nonprofit estimates are interpreted separately
- pooled models and Pell policy-exposure models are diagnostic unless a design-specific validation check supports stronger language

Avoid this language:

- unused aid capacity
- student-level grant substitution
- proof that institutions inflated cost of attendance
- causal institutional-grant response to Pell changes
- a full-postsecondary-sector estimate

## Repository Map

- `config/` contains the variable contract, headroom definitions, model specifications, and policy-shock registries.
- `src/coa_finaid_subs/` contains the reusable preparation, audit, measurement, model-sample, fixed-effects, and table-building code.
- `scripts/` contains command-line entry points for rebuilding panels, audits, estimates, tables, figures, and robustness checks.
- `docs/` contains the research protocol, design justification, data-decision register, measurement notes, model documentation, and replication instructions.
- `notebooks/table_exports.ipynb` rebuilds paste-ready tables and figures for paper drafting.
- `tests/` contains synthetic-data tests for the core data-integrity and estimation workflow.

Private manuscript drafts, Word exports, review packets, local data, and generated output folders are intentionally excluded from Git.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Rebuild the Analysis Layer

Set `IPEDSDB_ROOT` to the local root of the upstream clean IPEDS panel, then run:

```bash
export IPEDSDB_ROOT="/path/to/IPEDSDB_Panel"
python scripts/prepare_analysis_panel.py
```

The default build writes generated files under `outputs/`, including the baseline public/private nonprofit sample and separate public-only and private nonprofit samples. `outputs/` is ignored by Git.

The full replication sequence is documented in [`docs/replication.md`](docs/replication.md). The data rules and sample boundary are documented in [`docs/data_protocol.md`](docs/data_protocol.md). The design and claim boundary are documented in [`docs/research_design.md`](docs/research_design.md).

## Main Workflow

After the analysis panel is built, the main workflow is:

```bash
PYTHONPATH=src python scripts/audit_variable_config.py
PYTHONPATH=src python scripts/audit_headroom_measures.py
PYTHONPATH=src python scripts/build_model_samples.py
PYTHONPATH=src python scripts/run_fixed_effects.py
PYTHONPATH=src python scripts/validate_fixed_effects_outputs.py
PYTHONPATH=src python scripts/build_estimate_tables.py
PYTHONPATH=src python scripts/build_report_figures.py
```

Optional robustness layers, including HUD Fair Market Rent controls and Pell policy-exposure diagnostics, are documented in the relevant files under `docs/` and configured under `config/`.

## Checks

```bash
python -m pytest
```

## Contact

For questions about the project, use the contact information on [markjayson.com](https://markjayson.com).
