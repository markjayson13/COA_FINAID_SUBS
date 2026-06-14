from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from coa_finaid_subs.fixed_effects import fit_fixed_effects_model, focal_table
from coa_finaid_subs.model_plan import ModelSpec, load_model_specs


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path("outputs/local_housing_controls/fmr_control_estimates")
DEFAULT_FMR_CONTROLS = Path(
    "outputs/local_housing_controls/local_housing_controls_hud_fmr_2br_2009_2023_public_private_nonprofit.parquet"
)
DEFAULT_FIXED_CONFIG = REPO_ROOT / "config" / "model_specifications.csv"
DEFAULT_FIXED_SAMPLE_DIR = Path("outputs/model_samples/samples")
DEFAULT_FIXED_ORIGINAL_FOCAL = Path("outputs/fixed_effects/fixed_effects_focal_coefficients.csv")
DEFAULT_POLICY_CONFIG = REPO_ROOT / "config" / "policy_exposure_model_specifications.csv"
DEFAULT_POLICY_SAMPLE_DIR = Path("outputs/policy_model_samples/samples")
DEFAULT_POLICY_ORIGINAL_FOCAL = Path("outputs/policy_fixed_effects/fixed_effects_focal_coefficients.csv")
FMR_CONTROL = "ln_hud_fmr_2br"


def public_path_label(path: Path | str) -> str:
    """Return a shareable path label without embedding personal absolute paths."""
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate)
    try:
        return str(candidate.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return candidate.name


def repo_path(path: Path | str) -> Path:
    """Resolve repository-relative paths without depending on the caller's shell directory."""
    resolved = Path(path)
    return resolved if resolved.is_absolute() else REPO_ROOT / resolved


def add_control_to_spec(spec: ModelSpec, control: str = FMR_CONTROL) -> ModelSpec:
    """Return the same model specification with the FMR control appended once."""
    controls = spec.controls if control in spec.controls else (*spec.controls, control)
    return replace(spec, controls=controls)


def load_fmr_controls(path: Path = DEFAULT_FMR_CONTROLS) -> pd.DataFrame:
    """Load only the keys and HUD FMR fields needed for estimation."""
    control_path = repo_path(path)
    if not control_path.exists():
        raise FileNotFoundError(f"HUD FMR controls not found: {control_path}")
    frame = pd.read_parquet(control_path)
    required = {"UNITID", "year", FMR_CONTROL}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"HUD FMR controls are missing columns: {', '.join(sorted(missing))}")
    keep = ["UNITID", "year", "hud_fmr_2br", FMR_CONTROL, "hud_fmr_match_status"]
    keep = [column for column in keep if column in frame.columns]
    controls = frame[keep].copy()
    controls["UNITID"] = pd.to_numeric(controls["UNITID"], errors="coerce").astype("Int64")
    controls["year"] = pd.to_numeric(controls["year"], errors="coerce").astype("Int64")
    controls = controls.dropna(subset=["UNITID", "year"]).drop_duplicates(["UNITID", "year"])
    return controls


def attach_fmr_control(sample: pd.DataFrame, controls: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Merge the HUD FMR control into one materialized model sample."""
    if {"UNITID", "year"} - set(sample.columns):
        raise ValueError("Model sample must contain UNITID and year before HUD FMR controls can be merged")

    work = sample.copy()
    work["UNITID"] = pd.to_numeric(work["UNITID"], errors="coerce").astype("Int64")
    work["year"] = pd.to_numeric(work["year"], errors="coerce").astype("Int64")

    if FMR_CONTROL in work.columns:
        merged = work
    else:
        merged = work.merge(controls, on=["UNITID", "year"], how="left", validate="many_to_one")

    nonmissing = int(pd.to_numeric(merged[FMR_CONTROL], errors="coerce").notna().sum())
    metadata = {
        "source_rows": int(len(sample)),
        "fmr_nonmissing_rows": nonmissing,
        "fmr_missing_rows": int(len(sample) - nonmissing),
        "fmr_match_rate_in_model_sample": float(nonmissing / len(sample)) if len(sample) else np.nan,
    }
    return merged, metadata


def select_specs(specs: list[ModelSpec], model_ids: Iterable[str] | None) -> list[ModelSpec]:
    selected = set(model_ids) if model_ids else None
    if selected is None:
        return specs
    kept = [spec for spec in specs if spec.model_id in selected]
    missing = selected - {spec.model_id for spec in kept}
    if missing:
        raise ValueError(f"Model id not found in config: {', '.join(sorted(missing))}")
    return kept


def compare_focal_estimates(focal: pd.DataFrame, original_focal_path: Path) -> pd.DataFrame:
    """Compare the FMR-control focal coefficient with the already-generated baseline output."""
    original_path = repo_path(original_focal_path)
    if not original_path.exists() or focal.empty:
        return focal.copy()

    original = pd.read_csv(original_path)
    keep_original = [
        "model_id",
        "term",
        "estimate",
        "std_error",
        "t_stat",
        "p_value_normal",
        "nobs",
        "clusters",
        "within_r_squared",
        "rank_deficient",
    ]
    keep_original = [column for column in keep_original if column in original.columns]
    keep_fmr = [
        "model_id",
        "role",
        "sample_filter",
        "term",
        "estimate",
        "std_error",
        "t_stat",
        "p_value_normal",
        "nobs",
        "clusters",
        "within_r_squared",
        "rank_deficient",
    ]
    keep_fmr = [column for column in keep_fmr if column in focal.columns]
    comparison = focal[keep_fmr].merge(
        original[keep_original],
        how="left",
        on=["model_id", "term"],
        suffixes=("_hud_fmr", "_original"),
    )
    numeric_pairs = [
        ("estimate", "estimate_delta"),
        ("std_error", "std_error_delta"),
        ("t_stat", "t_stat_delta"),
        ("p_value_normal", "p_value_delta"),
        ("nobs", "nobs_delta"),
        ("clusters", "clusters_delta"),
        ("within_r_squared", "within_r_squared_delta"),
    ]
    for stem, delta in numeric_pairs:
        fmr_col = f"{stem}_hud_fmr"
        original_col = f"{stem}_original"
        if fmr_col in comparison.columns and original_col in comparison.columns:
            comparison[delta] = pd.to_numeric(comparison[fmr_col], errors="coerce") - pd.to_numeric(
                comparison[original_col], errors="coerce"
            )
    return comparison


def summarize_comparison(comparison: pd.DataFrame) -> dict[str, object]:
    if comparison.empty or "estimate_delta" not in comparison.columns:
        return {"rows_compared": int(len(comparison)), "median_abs_estimate_delta": None, "max_abs_estimate_delta": None}
    delta = pd.to_numeric(comparison["estimate_delta"], errors="coerce").abs().dropna()
    return {
        "rows_compared": int(len(delta)),
        "median_abs_estimate_delta": float(delta.median()) if len(delta) else None,
        "max_abs_estimate_delta": float(delta.max()) if len(delta) else None,
    }


def run_fmr_control_group(
    *,
    config: Path,
    sample_dir: Path,
    original_focal: Path,
    fmr_controls: pd.DataFrame,
    output_dir: Path,
    prefix: str,
    model_ids: Iterable[str] | None = None,
) -> dict[str, object]:
    """Estimate one group of configured models after adding log HUD two-bedroom FMR."""
    specs = select_specs(load_model_specs(repo_path(config)), model_ids)
    if not specs:
        raise ValueError(f"No model specifications selected for {prefix}")

    coefficient_frames: list[pd.DataFrame] = []
    diagnostics_rows: list[dict[str, object]] = []
    error_rows: list[dict[str, object]] = []
    sample_root = repo_path(sample_dir)

    for spec in specs:
        sample_path = sample_root / f"{spec.model_id}.parquet"
        if not sample_path.exists():
            error_rows.append({"model_id": spec.model_id, "status": "missing_sample", "error": public_path_label(sample_path)})
            continue
        try:
            sample = pd.read_parquet(sample_path)
            augmented_sample, merge_metadata = attach_fmr_control(sample, fmr_controls)
            fmr_spec = add_control_to_spec(spec)
            coefficients, diagnostics = fit_fixed_effects_model(augmented_sample, fmr_spec)
            coefficients["added_control"] = FMR_CONTROL
            diagnostics.update(merge_metadata)
            diagnostics["sample_path"] = public_path_label(sample_path)
            diagnostics["added_control"] = FMR_CONTROL
            diagnostics["status"] = "estimated"
            coefficient_frames.append(coefficients)
            diagnostics_rows.append(diagnostics)
        except Exception as exc:  # pragma: no cover - exercised by real data when a model is malformed
            error_rows.append({"model_id": spec.model_id, "status": "error", "error": str(exc)})

    coefficients = pd.concat(coefficient_frames, ignore_index=True) if coefficient_frames else pd.DataFrame()
    diagnostics = pd.DataFrame(diagnostics_rows)
    errors = pd.DataFrame(error_rows, columns=["model_id", "status", "error"])
    focal = focal_table(coefficients) if not coefficients.empty else pd.DataFrame()
    comparison = compare_focal_estimates(focal, original_focal)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "coefficients": output_dir / f"{prefix}_hud_fmr_coefficients.csv",
        "focal_coefficients": output_dir / f"{prefix}_hud_fmr_focal_coefficients.csv",
        "diagnostics": output_dir / f"{prefix}_hud_fmr_diagnostics.csv",
        "comparison": output_dir / f"{prefix}_hud_fmr_comparison.csv",
        "errors": output_dir / f"{prefix}_hud_fmr_errors.csv",
    }
    coefficients.to_csv(paths["coefficients"], index=False)
    focal.to_csv(paths["focal_coefficients"], index=False)
    diagnostics.to_csv(paths["diagnostics"], index=False)
    comparison.to_csv(paths["comparison"], index=False)
    errors.to_csv(paths["errors"], index=False)

    summary = {
        "prefix": prefix,
        "models_configured": int(len(specs)),
        "models_estimated": int(len(diagnostics)),
        "models_with_errors": int(len(errors)),
        "added_control": FMR_CONTROL,
        "comparison": summarize_comparison(comparison),
        "outputs": {key: public_path_label(path) for key, path in paths.items()},
    }
    if not diagnostics.empty and "fmr_match_rate_in_model_sample" in diagnostics.columns:
        summary["minimum_model_sample_fmr_match_rate"] = float(
            pd.to_numeric(diagnostics["fmr_match_rate_in_model_sample"], errors="coerce").min()
        )
    return summary


def build_fmr_control_estimates(
    *,
    fmr_controls_path: Path = DEFAULT_FMR_CONTROLS,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    fixed_config: Path = DEFAULT_FIXED_CONFIG,
    fixed_sample_dir: Path = DEFAULT_FIXED_SAMPLE_DIR,
    fixed_original_focal: Path = DEFAULT_FIXED_ORIGINAL_FOCAL,
    policy_config: Path = DEFAULT_POLICY_CONFIG,
    policy_sample_dir: Path = DEFAULT_POLICY_SAMPLE_DIR,
    policy_original_focal: Path = DEFAULT_POLICY_ORIGINAL_FOCAL,
) -> dict[str, Path]:
    """Build HUD FMR-control companion outputs for baseline and policy estimates."""
    output_root = repo_path(output_dir)
    controls = load_fmr_controls(fmr_controls_path)

    fixed_summary = run_fmr_control_group(
        config=fixed_config,
        sample_dir=fixed_sample_dir,
        original_focal=fixed_original_focal,
        fmr_controls=controls,
        output_dir=output_root,
        prefix="fixed_effects",
    )
    policy_summary = run_fmr_control_group(
        config=policy_config,
        sample_dir=policy_sample_dir,
        original_focal=policy_original_focal,
        fmr_controls=controls,
        output_dir=output_root,
        prefix="policy",
    )

    summary_path = output_root / "hud_fmr_control_estimates_summary.json"
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "added_control": FMR_CONTROL,
        "fmr_controls": public_path_label(repo_path(fmr_controls_path)),
        "fixed_effects": fixed_summary,
        "policy": policy_summary,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "summary": summary_path,
        "fixed_comparison": output_root / "fixed_effects_hud_fmr_comparison.csv",
        "policy_comparison": output_root / "policy_hud_fmr_comparison.csv",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run HUD FMR-control companion estimates for all configured models.")
    parser.add_argument("--fmr-controls", type=Path, default=DEFAULT_FMR_CONTROLS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fixed-config", type=Path, default=DEFAULT_FIXED_CONFIG)
    parser.add_argument("--fixed-sample-dir", type=Path, default=DEFAULT_FIXED_SAMPLE_DIR)
    parser.add_argument("--fixed-original-focal", type=Path, default=DEFAULT_FIXED_ORIGINAL_FOCAL)
    parser.add_argument("--policy-config", type=Path, default=DEFAULT_POLICY_CONFIG)
    parser.add_argument("--policy-sample-dir", type=Path, default=DEFAULT_POLICY_SAMPLE_DIR)
    parser.add_argument("--policy-original-focal", type=Path, default=DEFAULT_POLICY_ORIGINAL_FOCAL)
    args = parser.parse_args()
    paths = build_fmr_control_estimates(
        fmr_controls_path=args.fmr_controls,
        output_dir=args.output_dir,
        fixed_config=args.fixed_config,
        fixed_sample_dir=args.fixed_sample_dir,
        fixed_original_focal=args.fixed_original_focal,
        policy_config=args.policy_config,
        policy_sample_dir=args.policy_sample_dir,
        policy_original_focal=args.policy_original_focal,
    )
    print(f"Wrote HUD FMR-control estimate summary: {paths['summary']}")


if __name__ == "__main__":
    main()
