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


def build_estimate_table(coefficients: pd.DataFrame) -> pd.DataFrame:
    # Convert raw estimator output into a table with paper-facing labels.
    selected = select_estimate_rows(coefficients)
    rows: list[dict[str, object]] = []
    for row in selected.to_dict("records"):
        stars = significance_stars(row["p_value_normal"])
        rows.append(
            {
                "Model": MODEL_LABELS.get(row["model_id"], row["model_id"]),
                "Role": str(row["role"]).replace("_", " "),
                "Term": TERM_LABELS.get(row["term"], row["term"]),
                "Estimate": f"{format_number(row['estimate'], 4)}{stars}",
                "SE": f"({format_number(row['std_error'], 4)})",
                "t": format_number(row["t_stat"], 2),
                "p": format_number(row["p_value_normal"], 3),
                "N": format_integer(row["nobs"]),
                "Clusters": format_integer(row["clusters"]),
                "Within R2": format_number(row["within_r_squared"], 3),
            }
        )
    return pd.DataFrame(rows)


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
    table = build_estimate_table(coefficients)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "paper_csv": output_dir / "fixed_effects_main_table.csv",
        "paper_md": output_dir / "fixed_effects_main_table.md",
        "paper_tex": output_dir / "fixed_effects_main_table.tex",
        "paper_docx": output_dir / "fixed_effects_main_table.docx",
        "summary": output_dir / "fixed_effects_table_summary.json",
    }
    table.to_csv(paths["paper_csv"], index=False)
    caption = "Fixed-effects estimates for COA headroom and aid outcomes"
    note = (
        "Estimates absorb institution and year fixed effects. Standard errors are clustered by institution. "
        "The pooled interaction row reports the private nonprofit slope difference relative to public institutions. "
        "Significance markers use normal-reference p-values: * p<0.10, ** p<0.05, *** p<0.01."
    )
    write_markdown_table(paths["paper_md"], table, caption, note)
    write_latex_table(paths["paper_tex"], table, caption, "tab:fixed_effects_headroom", note)
    write_word_table(paths["paper_docx"], table, caption, note)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixed_effects_dir": str(fixed_effects_dir),
        "models_in_diagnostics": int(len(diagnostics)),
        "table_rows": int(len(table)),
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
