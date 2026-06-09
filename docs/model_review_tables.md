# Model review tables

This note documents the reviewer-facing tables that summarize the model plan, model samples, estimation diagnostics, and metadata flags.

Run:

```bash
PYTHONPATH=src python scripts/build_reviewer_tables.py
```

The script reads the baseline and policy model configs, the model-plan outputs, model-sample manifests, fixed-effects diagnostics, and focal coefficient files. It writes:

- `outputs/reviewer_tables/model_cards.csv`
- `outputs/reviewer_tables/model_sample_attrition.csv`
- `outputs/reviewer_tables/metadata_flag_glossary.csv`
- `outputs/reviewer_tables/reviewer_tables_summary.json`

The current local build wrote 68 model-card rows, 68 sample-attrition rows, and 7 metadata-glossary rows.

Generated outputs remain outside Git. This note records what those files are for.

## Model cards

`model_cards.csv` has one row per configured model. It records:

- dependent variable
- focal variable
- controls
- fixed effects
- cluster level
- weighting
- sample filter
- model role
- sample rows and institutions
- clusters and singleton clusters
- rank status and within R-squared
- focal coefficient, standard error, and t statistic when the model has been estimated

The table is meant to keep the model design readable without requiring a reader to reconstruct each specification from the CSV configs and output folders.

## Sample attrition

`model_sample_attrition.csv` has one row per model. It records:

- source rows
- complete-case rows
- rows dropped
- retained share
- sample institutions
- clusters
- main missingness sources from the model-sample missingness table
- a plain-English note explaining why the sample is narrower

This is the table to use in the paper appendix when explaining why net-price, selectivity, metadata-clean, balanced-panel, or policy-window samples are smaller than the baseline panel.

## Metadata glossary

`metadata_flag_glossary.csv` mirrors `docs/metadata_glossary.md` in table form. It gives reviewers a compact definition of imputation, revision, collection-status, parent-linked, and any-exposure flags.

## How these tables affect the paper

These tables do not add new estimates. They make the existing design easier to audit.

The paper should use them to show:

- the sector-specific models are the main estimates
- pooled models are checks
- sector-year fixed-effect pooled models test whether pooled results depend on sector-specific time shocks
- complete-case drops are visible before estimation
- metadata exposure is handled as a sensitivity check
