from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from coa_finaid_subs.model_plan import DEFAULT_MODEL_CONFIG, ModelSpec, add_model_derived_terms, load_model_specs


DEFAULT_SAMPLE_DIR = Path("outputs/model_samples/samples")
DEFAULT_OUTPUT_DIR = Path("outputs/fixed_effects")


def numeric_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(float)
    return pd.to_numeric(series, errors="coerce")


def normal_two_sided_pvalue(t_stat: float) -> float:
    if not math.isfinite(t_stat):
        return float("nan")
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def weighted_group_means(values: pd.DataFrame, groups: pd.Series, weights: pd.Series | None) -> pd.DataFrame:
    if weights is None:
        return values.groupby(groups, sort=False, dropna=False).transform("mean")

    weighted_values = values.mul(weights, axis=0)
    numerator = weighted_values.groupby(groups, sort=False, dropna=False).transform("sum")
    denominator = weights.groupby(groups, sort=False, dropna=False).transform("sum")
    return numerator.div(denominator.replace(0, np.nan), axis=0).fillna(0.0)


def fixed_effect_balance(values: pd.DataFrame, fixed_effects: pd.DataFrame, weights: pd.Series | None) -> float:
    if fixed_effects.empty or values.empty:
        return 0.0
    max_balance = 0.0
    for fe_column in fixed_effects.columns:
        means = weighted_group_means(values, fixed_effects[fe_column], weights)
        max_balance = max(max_balance, float(np.nanmax(np.abs(means.to_numpy()))))
    return max_balance


def sparse_absorb_fixed_effects(
    values: pd.DataFrame,
    fixed_effects: pd.DataFrame,
    weights: pd.Series | None,
    tolerance: float,
    max_iterations: int,
) -> tuple[pd.DataFrame, int, float] | None:
    if weights is not None:
        return None
    try:
        from scipy import sparse
        from scipy.sparse.linalg import lsmr
    except ImportError:
        return None

    nobs = len(values)
    row_parts: list[np.ndarray] = []
    col_parts: list[np.ndarray] = []
    data_parts: list[np.ndarray] = []
    offset = 0
    for fe_column in fixed_effects.columns:
        codes, uniques = pd.factorize(fixed_effects[fe_column], sort=False)
        valid = codes >= 0
        row_parts.append(np.arange(nobs, dtype=int)[valid])
        col_parts.append((codes[valid] + offset).astype(int))
        data_parts.append(np.ones(int(valid.sum()), dtype=float))
        offset += len(uniques)

    if offset == 0:
        return values.astype(float).copy(), 0, 0.0

    rows = np.concatenate(row_parts)
    cols = np.concatenate(col_parts)
    data = np.concatenate(data_parts)
    design = sparse.csr_matrix((data, (rows, cols)), shape=(nobs, offset))
    weighted_design = design

    residualized = pd.DataFrame(index=values.index)
    max_lsmr_iterations = 0
    lsmr_tolerance = min(tolerance, 1e-12)
    lsmr_max_iterations = max(max_iterations, 10_000)
    for column in values.columns:
        target = values[column].to_numpy(dtype=float)
        solution = lsmr(weighted_design, target, atol=lsmr_tolerance, btol=lsmr_tolerance, maxiter=lsmr_max_iterations)
        fitted = design @ solution[0]
        residualized[column] = target - fitted
        max_lsmr_iterations = max(max_lsmr_iterations, int(solution[2]))

    balance = fixed_effect_balance(residualized, fixed_effects, weights)
    return residualized, min(max_lsmr_iterations, max_iterations), balance


def absorb_fixed_effects(
    values: pd.DataFrame,
    fixed_effects: pd.DataFrame,
    weights: pd.Series | None = None,
    tolerance: float = 1e-10,
    max_iterations: int = 1_000,
) -> tuple[pd.DataFrame, int, float]:
    residualized = values.astype(float).copy()
    if fixed_effects.empty:
        return residualized, 0, 0.0

    sparse_result = sparse_absorb_fixed_effects(
        residualized,
        fixed_effects,
        weights=weights,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )
    if sparse_result is not None:
        return sparse_result

    last_change = float("inf")
    for iteration in range(1, max_iterations + 1):
        before = residualized.to_numpy(copy=True)
        for fe_column in fixed_effects.columns:
            means = weighted_group_means(residualized, fixed_effects[fe_column], weights)
            residualized = residualized - means
        change = float(np.nanmax(np.abs(residualized.to_numpy() - before)))
        last_change = change
        if change < tolerance:
            return residualized, iteration, last_change
    return residualized, max_iterations, last_change


def cluster_covariance(x: np.ndarray, residual: np.ndarray, clusters: pd.Series, rank: int) -> np.ndarray:
    nobs, k_params = x.shape
    bread = np.linalg.pinv(x.T @ x)
    scores = x * residual.reshape(-1, 1)
    meat = np.zeros((k_params, k_params), dtype=float)
    cluster_codes = pd.factorize(clusters, sort=False)[0]
    unique_clusters = np.unique(cluster_codes)
    for cluster_code in unique_clusters:
        cluster_score = scores[cluster_codes == cluster_code].sum(axis=0).reshape(k_params, 1)
        meat += cluster_score @ cluster_score.T

    n_clusters = len(unique_clusters)
    if n_clusters > 1 and nobs > rank:
        correction = (n_clusters / (n_clusters - 1.0)) * ((nobs - 1.0) / (nobs - rank))
    else:
        correction = 1.0
    return correction * bread @ meat @ bread


def within_variation_groups(frame: pd.DataFrame, group_column: str, value_column: str) -> int:
    if group_column not in frame.columns or value_column not in frame.columns:
        return 0
    counts = frame.groupby(group_column, dropna=True).size()
    observed_twice = counts[counts.ge(2)].index
    if len(observed_twice) == 0:
        return 0
    unique_values = frame.groupby(group_column, dropna=True)[value_column].nunique(dropna=True)
    return int(unique_values.loc[unique_values.index.intersection(observed_twice)].le(1).sum())


def estimation_variables(spec: ModelSpec) -> list[str]:
    variables = [spec.dependent_variable, spec.focal_variable]
    variables.extend(spec.controls)
    seen: set[str] = set()
    return [var for var in variables if not (var in seen or seen.add(var))]


def required_columns(spec: ModelSpec) -> list[str]:
    columns = estimation_variables(spec)
    columns.extend(spec.fixed_effects)
    if "SECTOR_YEAR" in spec.fixed_effects:
        columns.append("year")
    if spec.cluster_level:
        columns.append(spec.cluster_level)
    if spec.weight_variable:
        columns.append(spec.weight_variable)
    seen: set[str] = set()
    return [col for col in columns if not (col in seen or seen.add(col))]


def prepare_estimation_frame(sample: pd.DataFrame, spec: ModelSpec) -> tuple[pd.DataFrame, pd.Series | None, dict[str, object]]:
    sample = add_model_derived_terms(sample, estimation_variables(spec))
    missing = [col for col in required_columns(spec) if col not in sample.columns]
    if missing:
        raise ValueError(f"{spec.model_id} sample is missing columns: {', '.join(missing)}")

    work = sample[required_columns(spec)].copy()
    numeric_columns = estimation_variables(spec)
    if spec.weight_variable:
        numeric_columns.append(spec.weight_variable)
    for col in numeric_columns:
        work[col] = numeric_series(work[col])

    before = len(work)
    work = work.dropna(subset=required_columns(spec)).copy()
    if spec.weight_variable:
        work = work[work[spec.weight_variable].gt(0)].copy()
        weights = work[spec.weight_variable].astype(float)
    else:
        weights = None

    diagnostics = {
        "source_rows": int(len(sample)),
        "estimation_rows": int(len(work)),
        "dropped_rows": int(before - len(work)),
    }
    return work.reset_index(drop=True), None if weights is None else weights.reset_index(drop=True), diagnostics


def fit_fixed_effects_model(sample: pd.DataFrame, spec: ModelSpec) -> tuple[pd.DataFrame, dict[str, object]]:
    work, weights, prep = prepare_estimation_frame(sample, spec)
    terms = [spec.focal_variable, *spec.controls]
    if not terms:
        raise ValueError(f"{spec.model_id} has no right-hand-side variables")
    if len(work) == 0:
        raise ValueError(f"{spec.model_id} has no usable estimation rows")

    values = work[[spec.dependent_variable, *terms]].astype(float)
    fixed_effect_frame = work[list(spec.fixed_effects)].copy() if spec.fixed_effects else pd.DataFrame(index=work.index)
    residualized, iterations, last_change = absorb_fixed_effects(values, fixed_effect_frame, weights=weights)
    y = residualized[spec.dependent_variable].to_numpy(dtype=float)
    x = residualized[terms].to_numpy(dtype=float)

    if weights is not None:
        sqrt_weights = np.sqrt(weights.to_numpy(dtype=float))
        y_design = y * sqrt_weights
        x_design = x * sqrt_weights.reshape(-1, 1)
    else:
        y_design = y
        x_design = x

    beta, _, matrix_rank, singular_values = np.linalg.lstsq(x_design, y_design, rcond=None)
    fitted = x_design @ beta
    residual = y_design - fitted
    rank = int(matrix_rank)
    vcov = cluster_covariance(x_design, residual, work[spec.cluster_level], rank) if spec.cluster_level else np.full((len(terms), len(terms)), np.nan)
    variance = np.diag(vcov)
    std_errors = np.sqrt(np.where(variance >= 0, variance, np.nan))

    tss = float(np.sum((y_design - np.mean(y_design)) ** 2))
    rss = float(np.sum(residual**2))
    within_r_squared = float(1.0 - rss / tss) if tss > 0 else float("nan")

    coefficient_rows: list[dict[str, object]] = []
    for idx, term in enumerate(terms):
        estimate = float(beta[idx])
        std_error = float(std_errors[idx]) if np.isfinite(std_errors[idx]) else float("nan")
        t_stat = estimate / std_error if std_error > 0 else float("nan")
        coefficient_rows.append(
            {
                "model_id": spec.model_id,
                "stage": spec.stage,
                "role": spec.role,
                "sample_filter": spec.sample_filter,
                "term": term,
                "is_focal": term == spec.focal_variable,
                "estimate": estimate,
                "std_error": std_error,
                "t_stat": float(t_stat),
                "p_value_normal": normal_two_sided_pvalue(float(t_stat)),
                "nobs": int(len(work)),
                "clusters": int(work[spec.cluster_level].nunique(dropna=True)) if spec.cluster_level else 0,
                "fixed_effects": ";".join(spec.fixed_effects),
                "weight_variable": spec.weight_variable,
                "within_r_squared": within_r_squared,
                "matrix_rank": rank,
                "rank_deficient": rank < len(terms),
            }
        )

    cluster_counts = work.groupby(spec.cluster_level, dropna=True).size() if spec.cluster_level else pd.Series(dtype="int64")
    diagnostics = {
        "model_id": spec.model_id,
        "stage": spec.stage,
        "role": spec.role,
        "sample_filter": spec.sample_filter,
        "filter_notes": spec.filter_notes,
        "dependent_variable": spec.dependent_variable,
        "focal_variable": spec.focal_variable,
        "controls": ";".join(spec.controls),
        "fixed_effects": ";".join(spec.fixed_effects),
        "cluster_level": spec.cluster_level,
        "weight_variable": spec.weight_variable,
        "source_rows": prep["source_rows"],
        "estimation_rows": prep["estimation_rows"],
        "dropped_rows": prep["dropped_rows"],
        "institutions": int(work["UNITID"].nunique(dropna=True)) if "UNITID" in work.columns else 0,
        "clusters": int(work[spec.cluster_level].nunique(dropna=True)) if spec.cluster_level else 0,
        "singleton_clusters": int(cluster_counts.eq(1).sum()) if len(cluster_counts) else 0,
        "groups_without_focal_within_variation": within_variation_groups(work, spec.cluster_level, spec.focal_variable) if spec.cluster_level else 0,
        "k_parameters": int(len(terms)),
        "matrix_rank": rank,
        "rank_deficient": rank < len(terms),
        "absorbed_iterations": int(iterations),
        "absorbed_last_change": float(last_change),
        "within_r_squared": within_r_squared,
        "residual_df": int(len(work) - rank),
        "smallest_singular_value": float(np.min(singular_values)) if len(singular_values) else float("nan"),
        "status": "estimated",
    }
    return pd.DataFrame(coefficient_rows), diagnostics


def focal_table(coefficients: pd.DataFrame) -> pd.DataFrame:
    if coefficients.empty:
        return coefficients
    columns = [
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
    return coefficients[coefficients["is_focal"].astype(bool)][columns].copy()


def run_fixed_effects(
    sample_dir: Path = DEFAULT_SAMPLE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    config: Path = DEFAULT_MODEL_CONFIG,
    model_ids: Iterable[str] | None = None,
) -> dict[str, Path]:
    specs = load_model_specs(config)
    selected = set(model_ids) if model_ids else None
    if selected is not None:
        specs = [spec for spec in specs if spec.model_id in selected]
        missing_model_ids = selected - {spec.model_id for spec in specs}
        if missing_model_ids:
            raise ValueError(f"Model id not found in config: {', '.join(sorted(missing_model_ids))}")
    if not specs:
        raise ValueError("No model specifications selected")

    output_dir.mkdir(parents=True, exist_ok=True)
    coefficient_frames: list[pd.DataFrame] = []
    diagnostics_rows: list[dict[str, object]] = []
    for spec in specs:
        sample_path = sample_dir / f"{spec.model_id}.parquet"
        if not sample_path.exists():
            raise FileNotFoundError(f"Model sample not found for {spec.model_id}: {sample_path}")
        sample = pd.read_parquet(sample_path)
        coefficients, diagnostics = fit_fixed_effects_model(sample, spec)
        diagnostics["sample_path"] = str(sample_path)
        coefficient_frames.append(coefficients)
        diagnostics_rows.append(diagnostics)

    coefficient_table = pd.concat(coefficient_frames, ignore_index=True) if coefficient_frames else pd.DataFrame()
    diagnostics_table = pd.DataFrame(diagnostics_rows)
    focal = focal_table(coefficient_table)

    coefficients_path = output_dir / "fixed_effects_coefficients.csv"
    focal_path = output_dir / "fixed_effects_focal_coefficients.csv"
    diagnostics_path = output_dir / "fixed_effects_model_diagnostics.csv"
    summary_path = output_dir / "fixed_effects_summary.json"
    coefficient_table.to_csv(coefficients_path, index=False)
    focal.to_csv(focal_path, index=False)
    diagnostics_table.to_csv(diagnostics_path, index=False)

    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config),
        "sample_dir": str(sample_dir),
        "models_estimated": int(len(diagnostics_table)),
        "rank_deficient_models": int(diagnostics_table["rank_deficient"].sum()) if not diagnostics_table.empty else 0,
        "outputs": {
            "coefficients": str(coefficients_path),
            "focal_coefficients": str(focal_path),
            "diagnostics": str(diagnostics_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "coefficients": coefficients_path,
        "focal_coefficients": focal_path,
        "diagnostics": diagnostics_path,
        "summary": summary_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed-effects estimates from materialized model samples.")
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--model-id", action="append", dest="model_ids", help="Run one model id. Repeat for multiple models.")
    args = parser.parse_args()
    paths = run_fixed_effects(
        sample_dir=args.sample_dir,
        output_dir=args.output_dir,
        config=args.config,
        model_ids=args.model_ids,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
