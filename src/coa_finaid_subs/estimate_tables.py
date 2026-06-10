from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from coa_finaid_subs.descstat_tables import write_latex_table, write_markdown_table, write_word_table


DEFAULT_FIXED_EFFECTS_DIR = Path("outputs/fixed_effects")
DEFAULT_OUTPUT_DIR = Path("outputs/estimate_tables")

MODEL_LABELS = {
    "fe_inst_grant_per_student": "Institutional grant dollars",
    "fe_inst_grant_share": "Institutional grant share",
    "fe_pell_per_student": "Pell dollars",
    "fe_pell_share": "Pell share",
    "fe_federal_loan_per_student": "Federal loan dollars",
    "fe_weighted_inst_grant": "Institutional grant dollars, weighted",
    "pooled_sector_interaction_inst_grant": "Pooled sector interaction",
    "syfe_inst_grant_per_student": "Institutional grant dollars, sector-year FE",
    "syfe_inst_grant_share": "Institutional grant share, sector-year FE",
    "syfe_pell_per_student": "Pell dollars, sector-year FE",
    "syfe_pell_share": "Pell share, sector-year FE",
    "syfe_federal_loan_per_student": "Federal loan dollars, sector-year FE",
    "syfe_pooled_sector_interaction_inst_grant": "Pooled sector interaction, sector-year FE",
    "fe_net_price_low_income": "Net price, income 0-30000",
    "syfe_net_price_low_income": "Net price, income 0-30000, sector-year FE",
    "selectivity_inst_grant": "Selective-admissions sample",
    "public_inst_grant": "Public institutions",
    "private_np_inst_grant": "Private nonprofit institutions",
    "component_horse_race_inst_grant": "COA component model",
    "public_component_horse_race_inst_grant": "COA component model, public",
    "private_np_component_horse_race_inst_grant": "COA component model, private nonprofit",
    "sensitivity_min_years_10_inst_grant": "Minimum 10 observed years",
    "sensitivity_balanced_inst_grant": "Balanced 2009-2023 panel",
    "sensitivity_metadata_clean_inst_grant": "No metadata exposure",
    "sensitivity_no_suspect_zero_inst_grant": "No suspect aid-zero rows",
}

TERM_LABELS = {
    "HEADROOM_MAIN": "COA headroom",
    "HEADROOM_MAIN_SHARE_COA": "Headroom share of COA",
    "HEADROOM_MAIN_X_PRIVATE_NONPROFIT": "COA headroom x private nonprofit",
    "CHG2AY0": "Tuition and fees",
    "CHG4AY0": "Books and supplies",
    "CHG7AY0": "Off-campus room and board",
    "CHG8AY0": "Other expenses",
}

OUTCOME_LABELS = {
    "IGRNT_PER_FTFT_COHORT": "Institutional grants per FTFT aid-cohort student",
    "INST_GRANT_SHARE_OF_TOTAL_GRANT_FTFT": "Institutional grant share of FTFT grant dollars",
    "PGRNT_PER_FTFT_COHORT": "Pell grants per FTFT aid-cohort student",
    "PELL_SHARE_OF_TOTAL_GRANT_FTFT": "Pell share of FTFT grant dollars",
    "FLOAN_PER_FTFT_COHORT": "Federal loans per FTFT aid-cohort student",
    "NET_PRICE_0_30000_CLEAN": "Net price, income 0-30000",
}

SPECIFICATION_LABELS = {
    "fe_inst_grant_per_student": "Main: institution and year FE",
    "fe_inst_grant_share": "Main: institution and year FE",
    "fe_pell_per_student": "Aid diagnostic: institution and year FE",
    "fe_pell_share": "Aid diagnostic: institution and year FE",
    "fe_federal_loan_per_student": "Aid diagnostic: institution and year FE",
    "fe_weighted_inst_grant": "FTFT-weighted check",
    "pooled_sector_interaction_inst_grant": "Pooled sectors with private nonprofit interaction",
    "syfe_inst_grant_per_student": "Sector-year FE check",
    "syfe_inst_grant_share": "Sector-year FE check",
    "syfe_pell_per_student": "Sector-year FE check",
    "syfe_pell_share": "Sector-year FE check",
    "syfe_federal_loan_per_student": "Sector-year FE check",
    "syfe_pooled_sector_interaction_inst_grant": "Sector-year FE interaction check",
    "fe_net_price_low_income": "Net-price diagnostic",
    "syfe_net_price_low_income": "Net-price diagnostic with sector-year FE",
    "selectivity_inst_grant": "Selective-admissions robustness sample",
    "public_inst_grant": "Public institutions only",
    "private_np_inst_grant": "Private nonprofit institutions only",
    "component_horse_race_inst_grant": "COA component model, pooled sectors",
    "public_component_horse_race_inst_grant": "COA component model, public",
    "private_np_component_horse_race_inst_grant": "COA component model, private nonprofit",
    "sensitivity_min_years_10_inst_grant": "Minimum 10 observed years",
    "sensitivity_balanced_inst_grant": "Balanced institution panel",
    "sensitivity_metadata_clean_inst_grant": "No metadata-exposure rows",
    "sensitivity_no_suspect_zero_inst_grant": "No suspect aid-zero rows",
}

MODEL_ORDER = [
    "fe_inst_grant_per_student",
    "fe_inst_grant_share",
    "fe_pell_per_student",
    "fe_pell_share",
    "fe_federal_loan_per_student",
    "fe_weighted_inst_grant",
    "pooled_sector_interaction_inst_grant",
    "syfe_inst_grant_per_student",
    "syfe_inst_grant_share",
    "syfe_pell_per_student",
    "syfe_pell_share",
    "syfe_federal_loan_per_student",
    "syfe_pooled_sector_interaction_inst_grant",
    "fe_net_price_low_income",
    "syfe_net_price_low_income",
    "selectivity_inst_grant",
    "public_inst_grant",
    "private_np_inst_grant",
    "component_horse_race_inst_grant",
    "public_component_horse_race_inst_grant",
    "private_np_component_horse_race_inst_grant",
    "sensitivity_min_years_10_inst_grant",
    "sensitivity_balanced_inst_grant",
    "sensitivity_metadata_clean_inst_grant",
    "sensitivity_no_suspect_zero_inst_grant",
]

MAIN_MODELS = [
    "fe_inst_grant_per_student",
    "fe_weighted_inst_grant",
    "syfe_inst_grant_per_student",
    "public_inst_grant",
    "private_np_inst_grant",
    "pooled_sector_interaction_inst_grant",
]

AID_OUTCOME_MODELS = [
    "fe_inst_grant_per_student",
    "fe_inst_grant_share",
    "fe_pell_per_student",
    "fe_pell_share",
    "fe_federal_loan_per_student",
]

SECTOR_MODELS = [
    "public_inst_grant",
    "private_np_inst_grant",
    "pooled_sector_interaction_inst_grant",
    "syfe_pooled_sector_interaction_inst_grant",
]

ROBUSTNESS_MODELS = [
    "syfe_inst_grant_per_student",
    "fe_net_price_low_income",
    "syfe_net_price_low_income",
    "selectivity_inst_grant",
    "sensitivity_min_years_10_inst_grant",
    "sensitivity_balanced_inst_grant",
    "sensitivity_metadata_clean_inst_grant",
    "sensitivity_no_suspect_zero_inst_grant",
]

COMPONENT_MODELS = [
    "component_horse_race_inst_grant",
    "public_component_horse_race_inst_grant",
    "private_np_component_horse_race_inst_grant",
]

READABLE_COLUMNS = ["Outcome", "Specification", "Measure", "Estimate (SE)", "p", "N", "Institutions", "Within R2"]
APPENDIX_COLUMNS = [
    "Outcome",
    "Specification",
    "Measure",
    "Estimate",
    "SE",
    "t",
    "p",
    "N",
    "Institutions",
    "Clusters",
    "Fixed effects",
    "Weight",
    "Within R2",
]


def significance_stars(p_value: object) -> str:
    # Stars are added only for display; the p-value column is still exported.
    try:
        p = float(p_value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def format_number(value: object, digits: int = 3) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):,.{digits}f}"


def format_integer(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{int(value):,}"


def format_estimate_with_se(estimate: object, std_error: object, p_value: object) -> str:
    estimate_text = f"{format_number(estimate, 4)}{significance_stars(p_value)}"
    return f"{estimate_text} ({format_number(std_error, 4)})"


def select_estimate_rows(coefficients: pd.DataFrame) -> pd.DataFrame:
    # Keep focal coefficients plus the sector interaction and COA component checks.
    component_rows = coefficients["model_id"].astype(str).str.contains("component_horse_race") & coefficients["term"].isin(
        ["CHG2AY0", "CHG4AY0", "CHG7AY0", "CHG8AY0"]
    )
    key_rows = coefficients["is_focal"].astype(bool) | coefficients["term"].eq("HEADROOM_MAIN_X_PRIVATE_NONPROFIT") | component_rows
    table = coefficients[key_rows].copy()
    order_map = {model_id: idx for idx, model_id in enumerate(MODEL_ORDER)}
    table["model_order"] = table["model_id"].map(order_map).fillna(len(order_map)).astype(int)
    table["term_order"] = table["term"].eq("HEADROOM_MAIN_X_PRIVATE_NONPROFIT").astype(int)
    return table.sort_values(["model_order", "term_order", "model_id", "term"]).reset_index(drop=True)


def merge_estimate_metadata(coefficients: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    # Diagnostics carry readable model metadata such as outcome, fixed effects, and sample size.
    selected = select_estimate_rows(coefficients)
    diagnostic_cols = [
        col
        for col in [
            "model_id",
            "dependent_variable",
            "focal_variable",
            "controls",
            "fixed_effects",
            "weight_variable",
            "estimation_rows",
            "institutions",
            "clusters",
            "within_r_squared",
            "stage",
            "role",
            "sample_filter",
            "filter_notes",
        ]
        if col in diagnostics.columns
    ]
    if diagnostic_cols == ["model_id"]:
        return selected
    return selected.merge(diagnostics[diagnostic_cols], on="model_id", how="left", suffixes=("", "_diagnostic"))


def row_value(row: dict[str, object], key: str, fallback: str | None = None) -> object:
    value = row.get(key)
    if pd.isna(value) and fallback is not None:
        return row.get(fallback)
    return value


def outcome_label(row: dict[str, object]) -> str:
    dependent = row_value(row, "dependent_variable")
    if isinstance(dependent, str) and dependent:
        return OUTCOME_LABELS.get(dependent, dependent)
    return MODEL_LABELS.get(str(row.get("model_id")), str(row.get("model_id")))


def readable_estimate_rows(table: pd.DataFrame) -> list[dict[str, object]]:
    # Main tables combine estimate and standard error to reduce visual clutter.
    rows: list[dict[str, object]] = []
    for row in table.to_dict("records"):
        institutions = row_value(row, "institutions", "clusters")
        rows.append(
            {
                "Outcome": outcome_label(row),
                "Specification": SPECIFICATION_LABELS.get(str(row["model_id"]), MODEL_LABELS.get(row["model_id"], row["model_id"])),
                "Measure": TERM_LABELS.get(row["term"], row["term"]),
                "Estimate (SE)": format_estimate_with_se(row["estimate"], row["std_error"], row["p_value_normal"]),
                "p": format_number(row["p_value_normal"], 3),
                "N": format_integer(row_value(row, "estimation_rows", "nobs")),
                "Institutions": format_integer(institutions),
                "Within R2": format_number(row_value(row, "within_r_squared"), 3),
            }
        )
    return rows


def build_readable_estimate_table(merged: pd.DataFrame, model_ids: list[str]) -> pd.DataFrame:
    rows = merged[merged["model_id"].isin(model_ids)].copy()
    order = {model_id: idx for idx, model_id in enumerate(model_ids)}
    rows["display_order"] = rows["model_id"].map(order).fillna(len(order)).astype(int)
    rows = rows.sort_values(["display_order", "term_order", "model_id", "term"]).reset_index(drop=True)
    return pd.DataFrame(readable_estimate_rows(rows), columns=READABLE_COLUMNS)


def build_component_table(merged: pd.DataFrame) -> pd.DataFrame:
    rows = merged[merged["model_id"].isin(COMPONENT_MODELS)].copy()
    order = {model_id: idx for idx, model_id in enumerate(COMPONENT_MODELS)}
    rows["display_order"] = rows["model_id"].map(order).fillna(len(order)).astype(int)
    rows = rows.sort_values(["display_order", "term", "model_id"]).reset_index(drop=True)
    return pd.DataFrame(readable_estimate_rows(rows), columns=READABLE_COLUMNS)


def build_appendix_estimate_table(merged: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in merged.to_dict("records"):
        rows.append(
            {
                "Outcome": outcome_label(row),
                "Specification": SPECIFICATION_LABELS.get(str(row["model_id"]), MODEL_LABELS.get(row["model_id"], row["model_id"])),
                "Measure": TERM_LABELS.get(row["term"], row["term"]),
                "Estimate": f"{format_number(row['estimate'], 4)}{significance_stars(row['p_value_normal'])}",
                "SE": f"({format_number(row['std_error'], 4)})",
                "t": format_number(row["t_stat"], 2),
                "p": format_number(row["p_value_normal"], 3),
                "N": format_integer(row_value(row, "estimation_rows", "nobs")),
                "Institutions": format_integer(row_value(row, "institutions", "clusters")),
                "Clusters": format_integer(row_value(row, "clusters")),
                "Fixed effects": row_value(row, "fixed_effects"),
                "Weight": row_value(row, "weight_variable"),
                "Within R2": format_number(row_value(row, "within_r_squared"), 3),
            }
        )
    return pd.DataFrame(rows, columns=APPENDIX_COLUMNS)


def build_estimate_tables(
    fixed_effects_dir: Path = DEFAULT_FIXED_EFFECTS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    # Build every export format from the same coefficient file to avoid hand-copy errors.
    coefficients_path = fixed_effects_dir / "fixed_effects_coefficients.csv"
    diagnostics_path = fixed_effects_dir / "fixed_effects_model_diagnostics.csv"
    if not coefficients_path.exists():
        raise FileNotFoundError(f"Coefficient file not found: {coefficients_path}")
    if not diagnostics_path.exists():
        raise FileNotFoundError(f"Diagnostic file not found: {diagnostics_path}")

    coefficients = pd.read_csv(coefficients_path)
    diagnostics = pd.read_csv(diagnostics_path)
    merged = merge_estimate_metadata(coefficients, diagnostics)
    tables = {
        "paper": build_readable_estimate_table(merged, MAIN_MODELS),
        "aid_outcomes": build_readable_estimate_table(merged, AID_OUTCOME_MODELS),
        "sector_checks": build_readable_estimate_table(merged, SECTOR_MODELS),
        "robustness": build_readable_estimate_table(merged, ROBUSTNESS_MODELS),
        "components": build_component_table(merged),
        "appendix": build_appendix_estimate_table(merged),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "paper_csv": output_dir / "fixed_effects_main_institutional_grants.csv",
        "paper_md": output_dir / "fixed_effects_main_institutional_grants.md",
        "paper_tex": output_dir / "fixed_effects_main_institutional_grants.tex",
        "paper_docx": output_dir / "fixed_effects_main_institutional_grants.docx",
        "aid_outcomes_csv": output_dir / "fixed_effects_aid_outcomes.csv",
        "aid_outcomes_md": output_dir / "fixed_effects_aid_outcomes.md",
        "aid_outcomes_tex": output_dir / "fixed_effects_aid_outcomes.tex",
        "aid_outcomes_docx": output_dir / "fixed_effects_aid_outcomes.docx",
        "sector_checks_csv": output_dir / "fixed_effects_sector_checks.csv",
        "sector_checks_md": output_dir / "fixed_effects_sector_checks.md",
        "sector_checks_tex": output_dir / "fixed_effects_sector_checks.tex",
        "sector_checks_docx": output_dir / "fixed_effects_sector_checks.docx",
        "robustness_csv": output_dir / "fixed_effects_robustness_checks.csv",
        "robustness_md": output_dir / "fixed_effects_robustness_checks.md",
        "robustness_tex": output_dir / "fixed_effects_robustness_checks.tex",
        "robustness_docx": output_dir / "fixed_effects_robustness_checks.docx",
        "components_csv": output_dir / "fixed_effects_component_checks.csv",
        "components_md": output_dir / "fixed_effects_component_checks.md",
        "components_tex": output_dir / "fixed_effects_component_checks.tex",
        "components_docx": output_dir / "fixed_effects_component_checks.docx",
        "appendix_csv": output_dir / "fixed_effects_appendix_full.csv",
        "appendix_md": output_dir / "fixed_effects_appendix_full.md",
        "appendix_tex": output_dir / "fixed_effects_appendix_full.tex",
        "appendix_docx": output_dir / "fixed_effects_appendix_full.docx",
        "summary": output_dir / "fixed_effects_table_summary.json",
    }
    captions = {
        "paper": "Main institutional-grant estimates",
        "aid_outcomes": "Aid-outcome diagnostics",
        "sector_checks": "Sector and interaction checks",
        "robustness": "Robustness and diagnostic specifications",
        "components": "COA component checks",
        "appendix": "Appendix fixed-effects estimate audit",
    }
    labels = {
        "paper": "tab:fe_main_institutional_grants",
        "aid_outcomes": "tab:fe_aid_outcomes",
        "sector_checks": "tab:fe_sector_checks",
        "robustness": "tab:fe_robustness_checks",
        "components": "tab:fe_component_checks",
        "appendix": "tab:fe_appendix_full",
    }
    note = (
        "Estimates absorb institution and year fixed effects. Standard errors are clustered by institution. "
        "Sector-year checks replace year fixed effects with sector-year fixed effects. "
        "Significance markers use normal-reference p-values: * p<0.10, ** p<0.05, *** p<0.01."
    )
    for table_key, table in tables.items():
        table.to_csv(paths[f"{table_key}_csv"], index=False)
        write_markdown_table(paths[f"{table_key}_md"], table, captions[table_key], note)
        write_latex_table(paths[f"{table_key}_tex"], table, captions[table_key], labels[table_key], note)
        write_word_table(paths[f"{table_key}_docx"], table, captions[table_key], note)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixed_effects_dir": str(fixed_effects_dir),
        "models_in_diagnostics": int(len(diagnostics)),
        "table_rows": {key: int(len(table)) for key, table in tables.items()},
        "outputs": {key: str(value) for key, value in paths.items() if key != "summary"},
    }
    paths["summary"].write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Build paper-ready fixed-effects estimate tables.")
    parser.add_argument("--fixed-effects-dir", type=Path, default=DEFAULT_FIXED_EFFECTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = build_estimate_tables(fixed_effects_dir=args.fixed_effects_dir, output_dir=args.output_dir)
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
