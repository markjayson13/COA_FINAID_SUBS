from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from coa_finaid_subs.fixed_effects import fit_fixed_effects_model
from coa_finaid_subs.model_plan import ModelSpec


DEFAULT_ANALYSIS_ROOT = Path("outputs/analysis_panel")
DEFAULT_MODEL_SAMPLE_DIR = Path("outputs/model_samples/samples")
DEFAULT_FMR_COMPARISON = Path(
    "outputs/local_housing_controls/fmr_control_estimates/fixed_effects_hud_fmr_comparison.csv"
)
DEFAULT_OUTPUT_DIR = Path("outputs/manuscript")

BASELINE_CONTROLS = (
    "OPEN_ADMISSIONS_FLAG",
    "LN_SCFA1N",
    "LN_FIN_TOTAL_REVENUE",
    "LN_FIN_TOTAL_EXPENSES",
    "LN_FIN_TOTAL_ASSETS",
)
SELECTIVITY_CONTROLS = (
    "SELECTIVITY_INDEX",
    "ADMIT_RATE",
    "LN_SCFA1N",
    "LN_FIN_TOTAL_REVENUE",
    "LN_FIN_TOTAL_EXPENSES",
    "LN_FIN_TOTAL_ASSETS",
)
SECTOR_CODES = {"public": 1, "private_nonprofit": 2}

AID_OUTCOMES = (
    ("Institutional grants", "IGRNT_PER_FTFT_COHORT", "HEADROOM_MAIN", "$H_{it}$"),
    (
        "Institutional grant share",
        "INST_GRANT_SHARE_OF_TOTAL_GRANT_FTFT",
        "HEADROOM_MAIN_SHARE_COA",
        "$h_{it}$",
    ),
    ("Pell grants", "PGRNT_PER_FTFT_COHORT", "HEADROOM_MAIN", "$H_{it}$"),
    ("Pell grant share", "PELL_SHARE_OF_TOTAL_GRANT_FTFT", "HEADROOM_MAIN_SHARE_COA", "$h_{it}$"),
    ("Federal loans", "FLOAN_PER_FTFT_COHORT", "HEADROOM_MAIN", "$H_{it}$"),
)

ROBUSTNESS_CHECKS = (
    ("Baseline", "fe_inst_grant_per_student.parquet", BASELINE_CONTROLS, ""),
    ("FTFT-weighted", "fe_weighted_inst_grant.parquet", BASELINE_CONTROLS, "SCFA1N"),
    ("Minimum 10 observed years", "sensitivity_min_years_10_inst_grant.parquet", BASELINE_CONTROLS, ""),
    ("Balanced 2009-2023 panel", "sensitivity_balanced_inst_grant.parquet", BASELINE_CONTROLS, ""),
    ("No metadata-exposure rows", "sensitivity_metadata_clean_inst_grant.parquet", BASELINE_CONTROLS, ""),
    ("No suspect aid-zero rows", "sensitivity_no_suspect_zero_inst_grant.parquet", BASELINE_CONTROLS, ""),
    ("Selective-admissions sample", "selectivity_inst_grant.parquet", SELECTIVITY_CONTROLS, ""),
)
MAIN_ROBUSTNESS_CHECKS = {
    "Baseline",
    "FTFT-weighted",
    "Selective-admissions sample",
    "HUD FMR local rent control",
}


def fit_transient_fe_model(
    sample: pd.DataFrame,
    model_id: str,
    dependent_variable: str,
    focal_variable: str,
    controls: tuple[str, ...] = BASELINE_CONTROLS,
    weight_variable: str = "",
) -> tuple[pd.Series, dict[str, object]]:
    """Fit a table-only model without changing the registered estimation outputs."""
    spec = ModelSpec(
        model_id=model_id,
        stage="manuscript_exhibit",
        sample_scope="transient",
        analysis_panel="",
        dependent_variable=dependent_variable,
        focal_variable=focal_variable,
        controls=controls,
        weight_variable=weight_variable,
        fixed_effects=("UNITID", "year"),
        cluster_level="UNITID",
        role="manuscript_exhibit",
        notes="Transient sector estimate used to build manuscript tables and figures.",
    )
    coefficients, diagnostics = fit_fixed_effects_model(sample, spec)
    match = coefficients[coefficients["term"].eq(focal_variable)]
    if match.empty:
        raise ValueError(f"No focal coefficient for {model_id}: {focal_variable}")
    return match.iloc[0], diagnostics


def sector_sample(sample_path: Path, sector: str) -> pd.DataFrame:
    sample = pd.read_parquet(sample_path)
    if "SECTOR" not in sample.columns:
        raise ValueError(f"Sample lacks SECTOR column: {sample_path}")
    return sample[pd.to_numeric(sample["SECTOR"], errors="coerce").eq(SECTOR_CODES[sector])].copy()


def add_sector_result(
    record: dict[str, object],
    sector: str,
    coefficient: pd.Series,
    diagnostics: dict[str, object],
) -> None:
    record[f"{sector}_estimate"] = float(coefficient["estimate"])
    record[f"{sector}_std_error"] = float(coefficient["std_error"])
    record[f"{sector}_p_value"] = float(coefficient["p_value_normal"])
    record[f"{sector}_nobs"] = int(diagnostics["estimation_rows"])
    record[f"{sector}_institutions"] = int(diagnostics["institutions"])


def build_sector_aid_outcomes(
    analysis_root: Path = DEFAULT_ANALYSIS_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Estimate each aid outcome separately for public and private nonprofit institutions."""
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for label, dependent, focal, regressor in AID_OUTCOMES:
        record: dict[str, object] = {"outcome": label, "regressor": regressor}
        for sector in ("public", "private_nonprofit"):
            sample_path = analysis_root / sector / f"analysis_panel_coa_headroom_2009_2023_{sector}.parquet"
            sample = pd.read_parquet(sample_path)
            coefficient, diagnostics = fit_transient_fe_model(
                sample,
                model_id=f"manuscript_{sector}_{dependent.lower()}",
                dependent_variable=dependent,
                focal_variable=focal,
            )
            add_sector_result(record, sector, coefficient, diagnostics)
        records.append(record)

    output_path = output_dir / "sector_aid_outcomes_for_manuscript.csv"
    pd.DataFrame(records).to_csv(output_path, index=False)
    return output_path


def hud_fmr_robustness_record(fmr_comparison: Path) -> dict[str, object]:
    if not fmr_comparison.exists():
        raise FileNotFoundError(
            f"Required HUD FMR comparison is missing: {fmr_comparison}. "
            "Run scripts/build_fmr_control_estimates.py before building manuscript exhibits."
        )
    comparison = pd.read_csv(fmr_comparison)
    required = {
        "model_id",
        "estimate_hud_fmr",
        "std_error_hud_fmr",
        "p_value_normal_hud_fmr",
        "nobs_hud_fmr",
        "clusters_hud_fmr",
    }
    missing = sorted(required - set(comparison.columns))
    if missing:
        raise ValueError(f"{fmr_comparison} is missing required columns: {', '.join(missing)}")

    record: dict[str, object] = {
        "check": "HUD FMR local rent control",
        "weight": "",
        "source_sample": "",
        "added_control": "ln_hud_fmr_2br",
        "source": str(fmr_comparison),
    }
    model_ids = {"public": "public_inst_grant", "private_nonprofit": "private_np_inst_grant"}
    for sector, model_id in model_ids.items():
        match = comparison[comparison["model_id"].eq(model_id)]
        if len(match) != 1:
            raise ValueError(f"{fmr_comparison} must contain exactly one row for {model_id}; found {len(match)}")
        row = match.iloc[0]
        record[f"{sector}_estimate"] = float(row["estimate_hud_fmr"])
        record[f"{sector}_std_error"] = float(row["std_error_hud_fmr"])
        record[f"{sector}_p_value"] = float(row["p_value_normal_hud_fmr"])
        record[f"{sector}_nobs"] = int(row["nobs_hud_fmr"])
        record[f"{sector}_institutions"] = int(row["clusters_hud_fmr"])
        if "estimate_delta" in row.index:
            record[f"{sector}_estimate_delta"] = float(row["estimate_delta"])
    return record


def build_sector_robustness(
    model_sample_dir: Path = DEFAULT_MODEL_SAMPLE_DIR,
    fmr_comparison: Path = DEFAULT_FMR_COMPARISON,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    """Build selected manuscript checks and the complete sector robustness audit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for label, sample_file, controls, weight in ROBUSTNESS_CHECKS:
        record: dict[str, object] = {"check": label, "weight": weight, "source_sample": sample_file}
        for sector in ("public", "private_nonprofit"):
            sample = sector_sample(model_sample_dir / sample_file, sector)
            coefficient, diagnostics = fit_transient_fe_model(
                sample,
                model_id=f"manuscript_{sector}_{label.lower().replace(' ', '_')}",
                dependent_variable="IGRNT_PER_FTFT_COHORT",
                focal_variable="HEADROOM_MAIN",
                controls=controls,
                weight_variable=weight,
            )
            add_sector_result(record, sector, coefficient, diagnostics)
        records.append(record)

    records.append(hud_fmr_robustness_record(fmr_comparison))
    full = pd.DataFrame(records)
    selected = full[full["check"].isin(MAIN_ROBUSTNESS_CHECKS)].copy()
    selected_order = {
        "Baseline": 0,
        "FTFT-weighted": 1,
        "Selective-admissions sample": 2,
        "HUD FMR local rent control": 3,
    }
    selected["_order"] = selected["check"].map(selected_order)
    selected = selected.sort_values("_order").drop(columns="_order")

    selected_path = output_dir / "sector_robustness_for_manuscript.csv"
    full_path = output_dir / "sector_robustness_full_for_appendix.csv"
    selected.to_csv(selected_path, index=False)
    full.to_csv(full_path, index=False)
    return {"selected": selected_path, "full": full_path}


def build_manuscript_exhibit_data(
    analysis_root: Path = DEFAULT_ANALYSIS_ROOT,
    model_sample_dir: Path = DEFAULT_MODEL_SAMPLE_DIR,
    fmr_comparison: Path = DEFAULT_FMR_COMPARISON,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    paths = {"aid_outcomes": build_sector_aid_outcomes(analysis_root, output_dir)}
    paths.update({f"robustness_{key}": value for key, value in build_sector_robustness(model_sample_dir, fmr_comparison, output_dir).items()})
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the sector-specific data behind manuscript tables and figures.")
    parser.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    parser.add_argument("--model-sample-dir", type=Path, default=DEFAULT_MODEL_SAMPLE_DIR)
    parser.add_argument("--fmr-comparison", type=Path, default=DEFAULT_FMR_COMPARISON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = build_manuscript_exhibit_data(
        analysis_root=args.analysis_root,
        model_sample_dir=args.model_sample_dir,
        fmr_comparison=args.fmr_comparison,
        output_dir=args.output_dir,
    )
    print(f"Wrote {len(paths)} manuscript exhibit data files under {args.output_dir}")


if __name__ == "__main__":
    main()
