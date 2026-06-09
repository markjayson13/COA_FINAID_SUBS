from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_FIXED_EFFECTS_DIR = Path("outputs/fixed_effects")
DEFAULT_OUTPUT_DIR = Path("outputs/estimation_validation")


def finite_number(value: object) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric)


def config_model_ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    if not path.exists():
        raise FileNotFoundError(f"Model config not found: {path}")
    df = pd.read_csv(path)
    if "model_id" not in df.columns:
        raise ValueError(f"Model config lacks model_id column: {path}")
    return set(df["model_id"].dropna().astype(str))


def issue_rows_for_diagnostics(
    diagnostics: pd.DataFrame,
    max_absorbed_iterations: int,
    absorption_tolerance: float,
    min_clusters: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in diagnostics.to_dict("records"):
        model_id = str(record.get("model_id", ""))
        if bool(record.get("rank_deficient", False)):
            rows.append({"model_id": model_id, "check": "rank_deficient", "detail": "model is rank deficient"})
        clusters = pd.to_numeric(pd.Series([record.get("clusters")]), errors="coerce").iloc[0]
        if pd.notna(clusters) and clusters < min_clusters:
            rows.append({"model_id": model_id, "check": "too_few_clusters", "detail": f"clusters={int(clusters)}"})
        iterations = pd.to_numeric(pd.Series([record.get("absorbed_iterations")]), errors="coerce").iloc[0]
        last_change = pd.to_numeric(pd.Series([record.get("absorbed_last_change")]), errors="coerce").iloc[0]
        if pd.notna(iterations) and iterations >= max_absorbed_iterations:
            rows.append({"model_id": model_id, "check": "absorption_iteration_cap", "detail": f"absorbed_iterations={int(iterations)}"})
        if pd.notna(last_change) and last_change > absorption_tolerance:
            rows.append({"model_id": model_id, "check": "absorption_not_converged", "detail": f"absorbed_last_change={last_change:.3g}"})
        singular = pd.to_numeric(pd.Series([record.get("smallest_singular_value")]), errors="coerce").iloc[0]
        if pd.notna(singular) and singular <= 1e-8:
            rows.append({"model_id": model_id, "check": "near_singular_design", "detail": f"smallest_singular_value={singular:.3g}"})
    return rows


def issue_rows_for_coefficients(
    coefficients: pd.DataFrame,
    min_std_error: float,
    max_abs_t_stat: float,
    placebo_t_threshold: float,
    check_placebo_signals: bool,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if coefficients.empty:
        return [{"model_id": "", "check": "empty_coefficients", "detail": "coefficient table has no rows"}]
    focal = coefficients[coefficients["is_focal"].astype(bool)].copy() if "is_focal" in coefficients.columns else coefficients.iloc[0:0]
    if focal.empty:
        return [{"model_id": "", "check": "no_focal_coefficients", "detail": "no focal coefficient rows found"}]
    for record in focal.to_dict("records"):
        model_id = str(record.get("model_id", ""))
        term = str(record.get("term", ""))
        for column in ("estimate", "std_error", "t_stat", "p_value_normal"):
            if not finite_number(record.get(column)):
                rows.append({"model_id": model_id, "check": f"nonfinite_{column}", "detail": f"{term}: {column}={record.get(column)}"})
        std_error = pd.to_numeric(pd.Series([record.get("std_error")]), errors="coerce").iloc[0]
        if pd.notna(std_error) and std_error <= min_std_error:
            rows.append({"model_id": model_id, "check": "tiny_focal_std_error", "detail": f"{term}: std_error={std_error:.3g}"})
        t_stat = pd.to_numeric(pd.Series([record.get("t_stat")]), errors="coerce").iloc[0]
        if pd.notna(t_stat) and abs(t_stat) >= max_abs_t_stat:
            rows.append({"model_id": model_id, "check": "extreme_focal_t_stat", "detail": f"{term}: t_stat={t_stat:.3g}"})
        role = str(record.get("role", ""))
        if check_placebo_signals and "placebo" in role and pd.notna(t_stat) and abs(t_stat) >= placebo_t_threshold:
            rows.append({"model_id": model_id, "check": "placebo_signal", "detail": f"{term}: t_stat={t_stat:.3g}"})
    return rows


def validate_fixed_effects_outputs(
    fixed_effects_dir: Path = DEFAULT_FIXED_EFFECTS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    config: Path | None = None,
    max_absorbed_iterations: int = 1_000,
    absorption_tolerance: float = 1e-4,
    min_clusters: int = 50,
    min_std_error: float = 1e-10,
    max_abs_t_stat: float = 100.0,
    placebo_t_threshold: float = 1.96,
    check_placebo_signals: bool = True,
) -> dict[str, Path]:
    coefficients_path = fixed_effects_dir / "fixed_effects_coefficients.csv"
    diagnostics_path = fixed_effects_dir / "fixed_effects_model_diagnostics.csv"
    summary_path = fixed_effects_dir / "fixed_effects_summary.json"
    missing_files = [path for path in (coefficients_path, diagnostics_path, summary_path) if not path.exists()]
    if missing_files:
        raise FileNotFoundError("Missing fixed-effects output files: " + ", ".join(str(path) for path in missing_files))

    coefficients = pd.read_csv(coefficients_path)
    diagnostics = pd.read_csv(diagnostics_path)
    expected_model_ids = config_model_ids(config)
    observed_model_ids = set(diagnostics["model_id"].dropna().astype(str)) if "model_id" in diagnostics.columns else set()
    issues: list[dict[str, object]] = []
    for missing_model in sorted(expected_model_ids - observed_model_ids):
        issues.append({"model_id": missing_model, "check": "missing_model", "detail": "model config row has no diagnostic output"})
    for extra_model in sorted(observed_model_ids - expected_model_ids):
        if expected_model_ids:
            issues.append({"model_id": extra_model, "check": "unexpected_model", "detail": "diagnostic output not listed in config"})

    issues.extend(issue_rows_for_diagnostics(diagnostics, max_absorbed_iterations, absorption_tolerance, min_clusters))
    issues.extend(issue_rows_for_coefficients(coefficients, min_std_error, max_abs_t_stat, placebo_t_threshold, check_placebo_signals))

    output_dir.mkdir(parents=True, exist_ok=True)
    issue_table = pd.DataFrame(issues)
    issue_path = output_dir / "estimation_validation_issues.csv"
    validation_summary_path = output_dir / "estimation_validation_summary.json"
    issue_table.to_csv(issue_path, index=False)
    payload = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixed_effects_dir": str(fixed_effects_dir),
        "config": None if config is None else str(config),
        "models_expected": int(len(expected_model_ids)) if expected_model_ids else None,
        "models_observed": int(len(observed_model_ids)),
        "issue_count": int(len(issues)),
        "outputs": {"issues": str(issue_path)},
        "thresholds": {
            "max_absorbed_iterations": max_absorbed_iterations,
            "absorption_tolerance": absorption_tolerance,
            "min_clusters": min_clusters,
            "min_std_error": min_std_error,
            "max_abs_t_stat": max_abs_t_stat,
            "placebo_t_threshold": placebo_t_threshold,
            "check_placebo_signals": check_placebo_signals,
        },
    }
    validation_summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if issues:
        detail = "; ".join(f"{row['model_id']}:{row['check']}" for row in issues[:10])
        raise SystemExit(f"Estimation validation failed with {len(issues)} issue(s): {detail}")
    return {"issues": issue_path, "summary": validation_summary_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate fixed-effects outputs before paper use.")
    parser.add_argument("--fixed-effects-dir", type=Path, default=DEFAULT_FIXED_EFFECTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--min-clusters", type=int, default=50)
    parser.add_argument("--max-absorbed-iterations", type=int, default=1_000)
    parser.add_argument("--absorption-tolerance", type=float, default=1e-4)
    parser.add_argument("--skip-placebo-signal-check", action="store_true")
    args = parser.parse_args()
    paths = validate_fixed_effects_outputs(
        fixed_effects_dir=args.fixed_effects_dir,
        output_dir=args.output_dir,
        config=args.config,
        min_clusters=args.min_clusters,
        max_absorbed_iterations=args.max_absorbed_iterations,
        absorption_tolerance=args.absorption_tolerance,
        check_placebo_signals=not args.skip_placebo_signal_check,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
