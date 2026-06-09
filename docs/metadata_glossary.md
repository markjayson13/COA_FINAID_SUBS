# IPEDS metadata glossary

This note explains the metadata fields retained in the analysis panel. These fields do not define the main variables. They show whether a row was exposed to IPEDS reporting conditions that should be visible in sample descriptions and sensitivity checks.

## Why these fields stay in the panel

IPEDS data are reported through component surveys. Some records have imputation codes, revision flags, collection-status codes, or parent-child reporting information. Dropping those fields would make the analysis panel easier to read, but it would hide information that matters for replication.

The analysis panel therefore keeps the raw metadata fields when they are available and also writes conservative derived flags.

## Field families

| Field family | Plain name | How I use it |
| --- | --- | --- |
| `IMP_*` | imputation or status code | Retained as the raw IPEDS component code. A row is flagged when the code is neither the normal reported code nor the not-applicable code. |
| `REV_*` | revision flag | Retained as the raw component revision field. A row is flagged when the value equals one. |
| `LOCK_*` | collection lock or status code | Retained as raw collection-status information where present. |
| `IDX_*` | parent-linked reporting identifier | Retained where IPEDS reports a parent `UNITID` linkage for the component. |
| `PRCH_*` | parent-child reporting code | Retained as raw parent-child reporting information. |
| `PC*_F` | parent-child allocation factor | Used to flag rows where a component has positive parent-child allocation exposure. |
| `FLAG_IPEDS_ANY_METADATA_EXPOSURE` | any metadata exposure | A derived flag equal to one when any retained imputation, revision, or parent-linked component exposure is detected. |

## How to read the flags

The flags are conservative screening variables. They do not prove that a row is wrong. They identify records where the paper should be able to ask whether results change when those rows are excluded.

The current baseline sensitivity model `sensitivity_metadata_clean_inst_grant` drops rows with `FLAG_IPEDS_ANY_METADATA_EXPOSURE`. That is a sensitivity check, not the main sample rule.

## Paper language

Use:

> I retain raw IPEDS metadata fields for imputation, revision, collection status, and parent-child reporting where they are available. I also create a conservative row-level metadata-exposure flag and use it in sensitivity checks.

Do not use:

> Metadata-exposed rows are bad data.

Do not use:

> The derived metadata flag replaces the raw IPEDS status fields.
