from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HEADROOM_CONFIG = REPO_ROOT / "config" / "headroom_measures.csv"
DEFAULT_PANEL_DIR = REPO_ROOT / "outputs" / "analysis_panel"


@dataclass(frozen=True)
class HeadroomMeasureSpec:
    measure_id: str
    varname: str
    label: str
    family: str
    role: str
    component_vars: tuple[str, ...]
    denominator_var: str
    weight_variable: str
    main_model: bool
    diagnostic: bool
    bounded_0_1: bool
    notes: str


def parse_bool(value: object) -> bool:
    text = "" if pd.isna(value) else str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def split_semicolon(value: object) -> tuple[str, ...]:
    text = "" if pd.isna(value) else str(value)
    return tuple(part.strip() for part in text.split(";") if part.strip())


def load_headroom_specs(path: Path = DEFAULT_HEADROOM_CONFIG) -> list[HeadroomMeasureSpec]:
    if not path.exists():
        raise FileNotFoundError(f"Headroom measure config not found: {path}")
    df = pd.read_csv(path)
    required = {
        "measure_id",
        "varname",
        "label",
        "family",
        "role",
        "component_vars",
        "denominator_var",
        "weight_variable",
        "main_model",
        "diagnostic",
        "bounded_0_1",
        "notes",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Headroom measure config is missing columns: {', '.join(sorted(missing))}")

    specs: list[HeadroomMeasureSpec] = []
    seen_ids: set[str] = set()
    for row in df.to_dict("records"):
        measure_id = str(row["measure_id"]).strip()
        if not measure_id:
            continue
        if measure_id in seen_ids:
            raise ValueError(f"Duplicate measure_id in headroom config: {measure_id}")
        seen_ids.add(measure_id)
        specs.append(
            HeadroomMeasureSpec(
                measure_id=measure_id,
                varname=str(row["varname"]).strip(),
                label=str(row["label"]).strip(),
                family=str(row["family"]).strip(),
                role=str(row["role"]).strip(),
                component_vars=split_semicolon(row["component_vars"]),
                denominator_var="" if pd.isna(row["denominator_var"]) else str(row["denominator_var"]).strip(),
                weight_variable="" if pd.isna(row["weight_variable"]) else str(row["weight_variable"]).strip(),
                main_model=parse_bool(row["main_model"]),
                diagnostic=parse_bool(row["diagnostic"]),
                bounded_0_1=parse_bool(row["bounded_0_1"]),
                notes=str(row["notes"]).strip(),
            )
        )
    return specs


def panel_paths(panel_dir: Path, explicit: list[Path] | None = None) -> list[Path]:
    if explicit:
        return [path for path in explicit if path.exists()]
    return sorted(panel_dir.glob("*/analysis_panel_coa_headroom_*.parquet"))


def infer_scope(path: Path) -> str:
    return path.parent.name or path.stem


def sector_label(value: object) -> str:
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


def numeric_or_empty(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="Float64")
    return pd.to_numeric(df[column], errors="coerce")


def weighted_mean(values: pd.Series, weights: pd.Series) -> float | None:
    value = pd.to_numeric(values, errors="coerce")
    weight = pd.to_numeric(weights, errors="coerce")
    mask = value.notna() & weight.notna() & weight.gt(0)
    if not bool(mask.any()):
        return None
    return float((value[mask] * weight[mask]).sum() / weight[mask].sum())


def quantile_value(series: pd.Series, q: float) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    return float(clean.quantile(q))


def value_or_none(series: pd.Series, method: str) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    value = getattr(clean, method)()
    if pd.isna(value):
        return None
    return float(value)


def measure_coverage(df: pd.DataFrame, specs: list[HeadroomMeasureSpec], scope: str, panel_path: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_rows = len(df)
    unitids = int(df["UNITID"].nunique(dropna=True)) if "UNITID" in df.columns else 0
    years = pd.to_numeric(df["year"], errors="coerce") if "year" in df.columns else pd.Series(dtype="Float64")

    for spec in specs:
        present = spec.varname in df.columns
        series = numeric_or_empty(df, spec.varname)
        nonnull = int(series.notna().sum()) if present else 0
        component_missing = [var for var in spec.component_vars if var not in df.columns]
        denominator = numeric_or_empty(df, spec.denominator_var) if spec.denominator_var else pd.Series(pd.NA, index=df.index)
        weight = numeric_or_empty(df, spec.weight_variable) if spec.weight_variable else pd.Series(pd.NA, index=df.index)
        invalid_share = int((series.lt(0) | series.gt(1)).sum()) if present and spec.bounded_0_1 else 0
        row = {
            "scope": scope,
            "panel_path": str(panel_path),
            "measure_id": spec.measure_id,
            "varname": spec.varname,
            "label": spec.label,
            "family": spec.family,
            "role": spec.role,
            "main_model": spec.main_model,
            "diagnostic": spec.diagnostic,
            "bounded_0_1": spec.bounded_0_1,
            "present": present,
            "component_vars": ";".join(spec.component_vars),
            "missing_component_vars": ";".join(component_missing),
            "denominator_var": spec.denominator_var,
            "weight_variable": spec.weight_variable,
            "rows": total_rows,
            "panel_unitids": unitids,
            "min_year": None if years.dropna().empty else int(years.min()),
            "max_year": None if years.dropna().empty else int(years.max()),
            "nonnull_rows": nonnull,
            "nonnull_share": float(nonnull / total_rows) if total_rows else 0.0,
            "nonmissing_unitids": int(df.loc[series.notna(), "UNITID"].nunique(dropna=True)) if present and "UNITID" in df.columns else 0,
            "zero_count": int(series.eq(0).sum()) if present else 0,
            "negative_count": int(series.lt(0).sum()) if present else 0,
            "invalid_share_count": invalid_share,
            "denominator_nonpositive_count": int(denominator.le(0).sum()) if spec.denominator_var else 0,
            "weight_positive_rows": int(weight.gt(0).sum()) if spec.weight_variable else 0,
            "mean": value_or_none(series, "mean") if present else None,
            "sd": value_or_none(series, "std") if present else None,
            "min": value_or_none(series, "min") if present else None,
            "p10": quantile_value(series, 0.10) if present else None,
            "p25": quantile_value(series, 0.25) if present else None,
            "p50": quantile_value(series, 0.50) if present else None,
            "p75": quantile_value(series, 0.75) if present else None,
            "p90": quantile_value(series, 0.90) if present else None,
            "p99": quantile_value(series, 0.99) if present else None,
            "max": value_or_none(series, "max") if present else None,
            "ftft_weighted_mean": weighted_mean(series, weight) if present and spec.weight_variable else None,
            "notes": spec.notes,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def sector_year_summary(df: pd.DataFrame, specs: list[HeadroomMeasureSpec], scope: str) -> pd.DataFrame:
    if "year" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["sector"] = work["SECTOR"].map(sector_label) if "SECTOR" in work.columns else "all"
    rows: list[dict[str, object]] = []

    for spec in specs:
        if spec.varname not in work.columns:
            continue
        value = pd.to_numeric(work[spec.varname], errors="coerce")
        weight = numeric_or_empty(work, spec.weight_variable) if spec.weight_variable else pd.Series(pd.NA, index=work.index)
        for (sector, year), group in work.assign(_value=value, _weight=weight).groupby(["sector", "year"], dropna=False, sort=True):
            clean = pd.to_numeric(group["_value"], errors="coerce")
            rows.append(
                {
                    "scope": scope,
                    "sector": sector,
                    "year": int(year) if pd.notna(year) else None,
                    "measure_id": spec.measure_id,
                    "varname": spec.varname,
                    "role": spec.role,
                    "rows": int(len(group)),
                    "nonnull_rows": int(clean.notna().sum()),
                    "mean": value_or_none(clean, "mean"),
                    "p50": quantile_value(clean, 0.50),
                    "ftft_weighted_mean": weighted_mean(clean, group["_weight"]) if spec.weight_variable else None,
                }
            )
    return pd.DataFrame(rows)


def correlations(df: pd.DataFrame, specs: list[HeadroomMeasureSpec], scope: str) -> pd.DataFrame:
    variables = [spec.varname for spec in specs if spec.varname in df.columns]
    if len(variables) < 2:
        return pd.DataFrame(columns=["scope", "varname", "comparison_varname", "correlation", "pairwise_rows"])
    numeric = df[variables].apply(pd.to_numeric, errors="coerce")
    corr = numeric.corr()
    rows: list[dict[str, object]] = []
    for left in variables:
        for right in variables:
            if left == right:
                continue
            pair = numeric[[left, right]].dropna()
            rows.append(
                {
                    "scope": scope,
                    "varname": left,
                    "comparison_varname": right,
                    "correlation": None if pd.isna(corr.loc[left, right]) else float(corr.loc[left, right]),
                    "pairwise_rows": int(len(pair)),
                }
            )
    return pd.DataFrame(rows)


def audit_headroom_measures(
    panel_dir: Path = DEFAULT_PANEL_DIR,
    output_dir: Path = Path("outputs/headroom_measures"),
    config: Path = DEFAULT_HEADROOM_CONFIG,
    input_panels: list[Path] | None = None,
) -> dict[str, Path]:
    specs = load_headroom_specs(config)
    paths = panel_paths(panel_dir, input_panels)
    coverage_frames: list[pd.DataFrame] = []
    sector_year_frames: list[pd.DataFrame] = []
    correlation_frames: list[pd.DataFrame] = []

    for path in paths:
        df = pd.read_parquet(path)
        scope = infer_scope(path)
        coverage_frames.append(measure_coverage(df, specs, scope, path))
        sector_year_frames.append(sector_year_summary(df, specs, scope))
        correlation_frames.append(correlations(df, specs, scope))

    output_dir.mkdir(parents=True, exist_ok=True)
    coverage = pd.concat(coverage_frames, ignore_index=True) if coverage_frames else pd.DataFrame()
    by_sector_year = pd.concat(sector_year_frames, ignore_index=True) if sector_year_frames else pd.DataFrame()
    corr = pd.concat(correlation_frames, ignore_index=True) if correlation_frames else pd.DataFrame()

    coverage_path = output_dir / "headroom_measure_coverage.csv"
    by_sector_year_path = output_dir / "headroom_measure_by_sector_year.csv"
    correlations_path = output_dir / "headroom_measure_correlations.csv"
    summary_path = output_dir / "headroom_measure_summary.json"
    coverage.to_csv(coverage_path, index=False)
    by_sector_year.to_csv(by_sector_year_path, index=False)
    corr.to_csv(correlations_path, index=False)

    missing_main = 0
    invalid_share_rows = 0
    if not coverage.empty:
        missing_main = int((coverage["main_model"].eq(True) & coverage["present"].eq(False)).sum())
        invalid_share_rows = int(coverage["invalid_share_count"].sum())
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config),
        "panel_dir": str(panel_dir),
        "input_panels": [str(path) for path in paths],
        "measure_specs": int(len(specs)),
        "panels_checked": int(len(paths)),
        "missing_main_measures": missing_main,
        "invalid_share_rows": invalid_share_rows,
        "outputs": {
            "coverage": str(coverage_path),
            "by_sector_year": str(by_sector_year_path),
            "correlations": str(correlations_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "coverage": coverage_path,
        "by_sector_year": by_sector_year_path,
        "correlations": correlations_path,
        "summary": summary_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit candidate COA headroom measures before estimation.")
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/headroom_measures"))
    parser.add_argument("--config", type=Path, default=DEFAULT_HEADROOM_CONFIG)
    parser.add_argument("--input-panel", type=Path, action="append", default=None)
    args = parser.parse_args()
    paths = audit_headroom_measures(
        panel_dir=args.panel_dir,
        output_dir=args.output_dir,
        config=args.config,
        input_panels=args.input_panel,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
