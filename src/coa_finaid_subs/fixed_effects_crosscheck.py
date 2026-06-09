from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from coa_finaid_subs.fixed_effects import DEFAULT_OUTPUT_DIR as DEFAULT_FIXED_EFFECTS_DIR
from coa_finaid_subs.fixed_effects import DEFAULT_SAMPLE_DIR, prepare_estimation_frame
from coa_finaid_subs.model_plan import DEFAULT_MODEL_CONFIG, ModelSpec, load_model_specs


DEFAULT_OUTPUT_DIR = Path("outputs/fixed_effects_crosscheck")


def require_panel_ols():
    try:
        from linearmodels.panel import PanelOLS
    except ImportError as exc:
        raise RuntimeError(
            "The standard-estimator cross-check requires the optional validation dependency. "
            "Install it with `python -m pip install '.[validation]'` or `python -m pip install linearmodels`."
        ) from exc
    return PanelOLS


def supported_fixed_effects(spec: ModelSpec) -> bool:
    effects = set(spec.fixed_effects)
    if not effects.issubset({"UNITID", "year", "SECTOR_YEAR"}):
        return False
    if "SECTOR_YEAR" in effects and "year" in effects:
        return False
    return True


def linearmodels_fit(sample: pd.DataFrame, spec: ModelSpec) -> pd.DataFrame:
    if not supported_fixed_effects(spec):
        raise ValueError(f"{spec.model_id} has unsupported fixed effects for the linearmodels cross-check: {spec.fixed_effects}")
    PanelOLS = require_panel_ols()
    work, weights, _ = prepare_estimation_frame(sample, spec)
    terms = [spec.focal_variable, *spec.controls]
    work = work.copy()
    if weights is not None:
        work["_crosscheck_weight"] = weights.to_numpy(dtype=float)
    work["UNITID"] = pd.to_numeric(work["UNITID"], errors="raise")
    work["year"] = pd.to_numeric(work["year"], errors="raise")
    work = work.set_index(["UNITID", "year"]).sort_index()

    y = work[spec.dependent_variable].astype(float)
    x = work[terms].astype(float)
    model_kwargs = {
        "entity_effects": "UNITID" in spec.fixed_effects,
        "time_effects": "year" in spec.fixed_effects,
        "drop_absorbed": True,
        "check_rank": True,
    }
    if "SECTOR_YEAR" in spec.fixed_effects:
        other_effects = work[["SECTOR_YEAR"]].copy()
        other_effects["SECTOR_YEAR"] = pd.Categorical(other_effects["SECTOR_YEAR"]).codes
        model_kwargs["other_effects"] = other_effects
    if weights is not None:
        aligned_weights = work.pop("_crosscheck_weight").astype(float)
        model_kwargs["weights"] = aligned_weights
    model = PanelOLS(y, x, **model_kwargs)
    result = model.fit(
        cov_type="clustered",
        cluster_entity=spec.cluster_level == "UNITID",
        debiased=False,
        auto_df=False,
        count_effects=False,
    )

    rows = []
    for term in result.params.index:
        rows.append(
            {
                "model_id": spec.model_id,
                "term": term,
                "is_focal": term == spec.focal_variable,
                "linearmodels_estimate": float(result.params.loc[term]),
                "linearmodels_std_error": float(result.std_errors.loc[term]),
                "linearmodels_t_stat": float(result.tstats.loc[term]),
                "linearmodels_p_value": float(result.pvalues.loc[term]),
                "linearmodels_nobs": int(result.nobs),
            }
        )
    return pd.DataFrame(rows)


def load_current_coefficients(fixed_effects_dir: Path) -> pd.DataFrame:
    path = fixed_effects_dir / "fixed_effects_coefficients.csv"
    if not path.exists():
        return pd.DataFrame(columns=["model_id", "term", "estimate", "std_error", "t_stat", "p_value_normal", "nobs"])
    return pd.read_csv(path)


def run_fixed_effects_crosscheck(
    sample_dir: Path = DEFAULT_SAMPLE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    config: Path = DEFAULT_MODEL_CONFIG,
    fixed_effects_dir: Path = DEFAULT_FIXED_EFFECTS_DIR,
    model_ids: list[str] | None = None,
    estimate_tolerance: float = 1e-6,
    std_error_tolerance: float = 1e-4,
    focal_only: bool = True,
    skip_unsupported: bool = True,
) -> dict[str, Path]:
    specs = load_model_specs(config)
    selected = set(model_ids) if model_ids else None
    if selected is not None:
        specs = [spec for spec in specs if spec.model_id in selected]
        missing = selected - {spec.model_id for spec in specs}
        if missing:
            raise ValueError(f"Model id not found in config: {', '.join(sorted(missing))}")
    if not specs:
        raise ValueError("No model specifications selected")

    current = load_current_coefficients(fixed_effects_dir)
    frames: list[pd.DataFrame] = []
    skipped_rows: list[dict[str, object]] = []
    for spec in specs:
        if not supported_fixed_effects(spec):
            if not skip_unsupported:
                raise ValueError(f"{spec.model_id} has unsupported fixed effects for the linearmodels cross-check: {spec.fixed_effects}")
            skipped_rows.append(
                {
                    "model_id": spec.model_id,
                    "fixed_effects": ";".join(spec.fixed_effects),
                    "reason": "unsupported_fixed_effect_structure",
                }
            )
            continue
        sample_path = sample_dir / f"{spec.model_id}.parquet"
        if not sample_path.exists():
            raise FileNotFoundError(f"Model sample not found for {spec.model_id}: {sample_path}")
        sample = pd.read_parquet(sample_path)
        frames.append(linearmodels_fit(sample, spec))

    check = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if check.empty:
        raise ValueError("No supported model specifications were available for cross-checking")
    if focal_only and "is_focal" in check.columns:
        check = check[check["is_focal"].astype(bool)].copy()
    merged = check.merge(
        current[["model_id", "term", "estimate", "std_error", "t_stat", "p_value_normal", "nobs"]],
        how="left",
        on=["model_id", "term"],
    )
    merged = merged.rename(
        columns={
            "estimate": "current_estimate",
            "std_error": "current_std_error",
            "t_stat": "current_t_stat",
            "p_value_normal": "current_p_value_normal",
            "nobs": "current_nobs",
        }
    )
    merged["estimate_abs_diff"] = (merged["linearmodels_estimate"] - pd.to_numeric(merged["current_estimate"], errors="coerce")).abs()
    merged["std_error_abs_diff"] = (
        merged["linearmodels_std_error"] - pd.to_numeric(merged["current_std_error"], errors="coerce")
    ).abs()
    merged["estimate_match"] = merged["estimate_abs_diff"].le(estimate_tolerance)
    merged["std_error_match"] = merged["std_error_abs_diff"].le(std_error_tolerance)
    merged["passes_crosscheck"] = merged["estimate_match"] & merged["std_error_match"]

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = output_dir / "fixed_effects_linearmodels_comparison.csv"
    skipped_path = output_dir / "fixed_effects_linearmodels_skipped.csv"
    summary_path = output_dir / "fixed_effects_linearmodels_summary.json"
    merged.to_csv(comparison_path, index=False)
    pd.DataFrame(skipped_rows).to_csv(skipped_path, index=False)
    failed = merged[~merged["passes_crosscheck"].fillna(False)].copy()
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_dir": str(sample_dir),
        "config": str(config),
        "fixed_effects_dir": str(fixed_effects_dir),
        "terms_checked": int(len(merged)),
        "models_checked": int(merged["model_id"].nunique()) if not merged.empty else 0,
        "models_skipped": int(len(skipped_rows)),
        "failed_terms": int(len(failed)),
        "estimate_tolerance": estimate_tolerance,
        "std_error_tolerance": std_error_tolerance,
        "focal_only": focal_only,
        "max_estimate_abs_diff": float(merged["estimate_abs_diff"].max()) if not merged.empty else None,
        "max_std_error_abs_diff": float(merged["std_error_abs_diff"].max()) if not merged.empty else None,
        "outputs": {"comparison": str(comparison_path), "skipped": str(skipped_path)},
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if not failed.empty:
        examples = "; ".join(f"{row.model_id}:{row.term}" for row in failed.head(10).itertuples(index=False))
        raise SystemExit(f"linearmodels cross-check failed for {len(failed)} term(s): {examples}")
    return {"comparison": comparison_path, "summary": summary_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-check fixed-effects estimates against linearmodels.PanelOLS.")
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--fixed-effects-dir", type=Path, default=DEFAULT_FIXED_EFFECTS_DIR)
    parser.add_argument("--model-id", action="append", dest="model_ids", help="Cross-check one model id. Repeat for multiple models.")
    parser.add_argument("--estimate-tolerance", type=float, default=1e-6)
    parser.add_argument("--std-error-tolerance", type=float, default=1e-4)
    parser.add_argument("--all-terms", action="store_true", help="Check controls as well as focal coefficients.")
    parser.add_argument("--fail-unsupported", action="store_true", help="Fail if any selected model uses unsupported fixed effects.")
    args = parser.parse_args()
    paths = run_fixed_effects_crosscheck(
        sample_dir=args.sample_dir,
        output_dir=args.output_dir,
        config=args.config,
        fixed_effects_dir=args.fixed_effects_dir,
        model_ids=args.model_ids,
        estimate_tolerance=args.estimate_tolerance,
        std_error_tolerance=args.std_error_tolerance,
        focal_only=not args.all_terms,
        skip_unsupported=not args.fail_unsupported,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
