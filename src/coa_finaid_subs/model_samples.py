from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from coa_finaid_subs.model_plan import (
    DEFAULT_MODEL_CONFIG,
    DEFAULT_PANEL_DIR,
    add_model_derived_terms,
    load_model_specs,
    model_terms_for_spec,
    panel_path,
    sample_filter_mask,
    scope_dir_for_spec,
    variables_for_spec,
)


def variable_roles(spec) -> dict[str, str]:
    roles = {
        spec.dependent_variable: "dependent_variable",
        spec.focal_variable: "focal_variable",
    }
    for var in spec.controls:
        roles.setdefault(var, "control")
    for var in spec.fixed_effects:
        roles.setdefault(var, "fixed_effect")
    if spec.weight_variable:
        roles.setdefault(spec.weight_variable, "weight")
    if spec.cluster_level:
        roles.setdefault(spec.cluster_level, "cluster")
    return roles


def sector_name(value: object) -> str:
    if pd.isna(value):
        return "missing"
    try:
        sector = int(value)
    except (TypeError, ValueError):
        return str(value)
    return {
        1: "public",
        2: "private_nonprofit",
        3: "private_forprofit",
    }.get(sector, f"sector_{sector}")


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def model_sample_summary(spec, sample: pd.DataFrame, source_rows: int, path: Path, output_path: Path) -> dict[str, object]:
    focal = safe_numeric(sample[spec.focal_variable]) if spec.focal_variable in sample.columns else pd.Series(dtype="Float64")
    outcome = safe_numeric(sample[spec.dependent_variable]) if spec.dependent_variable in sample.columns else pd.Series(dtype="Float64")
    unit_counts = sample.groupby("UNITID", dropna=True).size() if "UNITID" in sample.columns else pd.Series(dtype="int64")
    singleton_unitids = set(unit_counts[unit_counts.eq(1)].index)
    no_within_variation = 0
    if {"UNITID", spec.focal_variable} <= set(sample.columns):
        focal_nunique = sample.groupby("UNITID", dropna=True)[spec.focal_variable].nunique(dropna=True)
        observed_twice = unit_counts[unit_counts.ge(2)].index
        no_within_variation = int(focal_nunique.loc[focal_nunique.index.intersection(observed_twice)].le(1).sum())

    years = safe_numeric(sample["year"]) if "year" in sample.columns else pd.Series(dtype="Float64")
    if "SECTOR" in sample.columns:
        sector_counts = sample["SECTOR"].map(sector_name).value_counts(dropna=False).to_dict()
    else:
        sector_counts = {}
    weights = safe_numeric(sample[spec.weight_variable]) if spec.weight_variable and spec.weight_variable in sample.columns else pd.Series(dtype="Float64")

    return {
        "model_id": spec.model_id,
        "stage": spec.stage,
        "sample_scope": spec.sample_scope,
        "role": spec.role,
        "source_panel": str(path),
        "output_sample": str(output_path),
        "source_rows": int(source_rows),
        "sample_rows": int(len(sample)),
        "sample_institutions": int(sample["UNITID"].nunique(dropna=True)) if "UNITID" in sample.columns else 0,
        "min_year": None if years.dropna().empty else int(years.min()),
        "max_year": None if years.dropna().empty else int(years.max()),
        "singleton_institutions": int(len(singleton_unitids)),
        "singleton_rows": int(sample["UNITID"].isin(singleton_unitids).sum()) if "UNITID" in sample.columns else 0,
        "institutions_without_focal_within_variation": no_within_variation,
        "dependent_variable": spec.dependent_variable,
        "focal_variable": spec.focal_variable,
        "dependent_mean": None if outcome.dropna().empty else float(outcome.mean()),
        "dependent_sd": None if outcome.dropna().empty else float(outcome.std()),
        "focal_mean": None if focal.dropna().empty else float(focal.mean()),
        "focal_sd": None if focal.dropna().empty else float(focal.std()),
        "weight_variable": spec.weight_variable,
        "nonpositive_weight_rows": int(weights.le(0).sum()) if spec.weight_variable else 0,
        "sector_counts_json": json.dumps(sector_counts, sort_keys=True),
        "notes": spec.notes,
    }


def missingness_rows(spec, df: pd.DataFrame, variables: list[str]) -> list[dict[str, object]]:
    roles = variable_roles(spec)
    rows: list[dict[str, object]] = []
    for var in variables:
        if var not in df.columns:
            rows.append(
                {
                    "model_id": spec.model_id,
                    "varname": var,
                    "role": roles.get(var, "other"),
                    "present": False,
                    "source_rows": int(len(df)),
                    "missing_rows": int(len(df)),
                    "missing_share": 1.0,
                }
            )
            continue
        missing = int(df[var].isna().sum())
        rows.append(
            {
                "model_id": spec.model_id,
                "varname": var,
                "role": roles.get(var, "other"),
                "present": True,
                "source_rows": int(len(df)),
                "missing_rows": missing,
                "missing_share": float(missing / len(df)) if len(df) else 0.0,
            }
        )
    return rows


def build_model_samples(
    panel_dir: Path = DEFAULT_PANEL_DIR,
    output_dir: Path = Path("outputs/model_samples"),
    config: Path = DEFAULT_MODEL_CONFIG,
) -> dict[str, Path]:
    specs = load_model_specs(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_dir = output_dir / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, object]] = []
    missing_rows: list[dict[str, object]] = []
    for spec in specs:
        path = panel_path(panel_dir, spec)
        output_path = sample_dir / f"{spec.model_id}.parquet"
        if not path.exists():
            manifest_rows.append(
                {
                    "model_id": spec.model_id,
                    "stage": spec.stage,
                    "sample_scope": spec.sample_scope,
                    "role": spec.role,
                    "sample_filter": spec.sample_filter,
                    "source_panel": str(path),
                    "output_sample": "",
                    "source_rows": 0,
                    "sample_rows": 0,
                    "sample_institutions": 0,
                    "missing_variables": ";".join(variables_for_spec(spec)),
                    "notes": spec.notes,
                    "filter_notes": spec.filter_notes,
                }
            )
            continue

        df = pd.read_parquet(path)
        source_variables = variables_for_spec(spec)
        model_terms = model_terms_for_spec(spec)
        missing = [var for var in source_variables if var not in df.columns]
        missing_rows.extend(missingness_rows(spec, df, source_variables))
        if missing:
            manifest_rows.append(
                {
                    "model_id": spec.model_id,
                    "stage": spec.stage,
                    "sample_scope": spec.sample_scope,
                    "role": spec.role,
                    "sample_filter": spec.sample_filter,
                    "source_panel": str(path),
                    "output_sample": "",
                    "source_rows": int(len(df)),
                    "sample_rows": 0,
                    "sample_institutions": 0,
                    "missing_variables": ";".join(missing),
                    "notes": spec.notes,
                    "filter_notes": spec.filter_notes,
                }
            )
            continue

        keep_columns = [var for var in source_variables if var in df.columns]
        extra_columns = [col for col in ("INSTNM", "SECTOR", "CONTROL", "STABBR") if col in df.columns and col not in keep_columns]
        work = df[keep_columns + extra_columns].copy()
        work = add_model_derived_terms(work, model_terms)
        filter_mask = sample_filter_mask(work, spec, scope_dir_for_spec(panel_dir, spec))
        sample_mask = filter_mask & work[model_terms].notna().all(axis=1)
        if spec.weight_variable:
            sample_mask = sample_mask & safe_numeric(work[spec.weight_variable]).gt(0)
        sample = work[sample_mask].copy()
        sample.insert(0, "model_id", spec.model_id)
        sample.to_parquet(output_path, index=False)

        row = model_sample_summary(spec, sample, len(df), path, output_path)
        row["missing_variables"] = ""
        row["sample_filter"] = spec.sample_filter
        row["filter_notes"] = spec.filter_notes
        manifest_rows.append(row)

    manifest = pd.DataFrame(manifest_rows)
    missingness = pd.DataFrame(missing_rows)
    manifest_path = output_dir / "model_sample_manifest.csv"
    missingness_path = output_dir / "model_sample_variable_missingness.csv"
    summary_path = output_dir / "model_sample_summary.json"
    manifest.to_csv(manifest_path, index=False)
    missingness.to_csv(missingness_path, index=False)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config),
        "panel_dir": str(panel_dir),
        "model_specs": int(len(specs)),
        "model_samples_written": int(manifest["output_sample"].fillna("").ne("").sum()) if not manifest.empty else 0,
        "models_with_missing_variables": int(manifest["missing_variables"].fillna("").ne("").sum()) if not manifest.empty else 0,
        "outputs": {
            "manifest": str(manifest_path),
            "variable_missingness": str(missingness_path),
            "samples": str(sample_dir),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "manifest": manifest_path,
        "missingness": missingness_path,
        "summary": summary_path,
        "sample_dir": sample_dir,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize complete-case model samples from the model specification contract.")
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/model_samples"))
    parser.add_argument("--config", type=Path, default=DEFAULT_MODEL_CONFIG)
    args = parser.parse_args()
    paths = build_model_samples(panel_dir=args.panel_dir, output_dir=args.output_dir, config=args.config)
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
