from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_CONFIG = REPO_ROOT / "config" / "model_specifications.csv"
DEFAULT_PANEL_DIR = REPO_ROOT / "outputs" / "analysis_panel"

MODEL_DERIVED_TERM_SOURCES: dict[str, tuple[str, ...]] = {
    "SECTOR_YEAR": ("SECTOR", "year"),
    "SECTOR_PRIVATE_NONPROFIT": ("SECTOR",),
    "HEADROOM_MAIN_X_PRIVATE_NONPROFIT": ("HEADROOM_MAIN", "SECTOR"),
    "HEADROOM_MAIN_SHARE_COA_X_PRIVATE_NONPROFIT": ("HEADROOM_MAIN_SHARE_COA", "SECTOR"),
}


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    stage: str
    sample_scope: str
    analysis_panel: str
    dependent_variable: str
    focal_variable: str
    controls: tuple[str, ...]
    weight_variable: str
    fixed_effects: tuple[str, ...]
    cluster_level: str
    role: str
    notes: str
    sample_filter: str = ""
    filter_notes: str = ""


def split_semicolon(value: object) -> tuple[str, ...]:
    text = "" if pd.isna(value) else str(value)
    return tuple(part.strip() for part in text.split(";") if part.strip())


def load_model_specs(path: Path = DEFAULT_MODEL_CONFIG) -> list[ModelSpec]:
    if not path.exists():
        raise FileNotFoundError(f"Model specification config not found: {path}")
    df = pd.read_csv(path)
    required = {
        "model_id",
        "stage",
        "sample_scope",
        "analysis_panel",
        "dependent_variable",
        "focal_variable",
        "controls",
        "weight_variable",
        "fixed_effects",
        "cluster_level",
        "role",
        "notes",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Model specification config is missing columns: {', '.join(sorted(missing))}")

    specs: list[ModelSpec] = []
    seen: set[str] = set()
    for row in df.to_dict("records"):
        model_id = str(row["model_id"]).strip()
        if not model_id:
            continue
        if model_id in seen:
            raise ValueError(f"Duplicate model_id in model specification config: {model_id}")
        seen.add(model_id)
        specs.append(
            ModelSpec(
                model_id=model_id,
                stage=str(row["stage"]).strip(),
                sample_scope=str(row["sample_scope"]).strip(),
                analysis_panel=str(row["analysis_panel"]).strip(),
                dependent_variable=str(row["dependent_variable"]).strip(),
                focal_variable=str(row["focal_variable"]).strip(),
                controls=split_semicolon(row["controls"]),
                weight_variable="" if pd.isna(row["weight_variable"]) else str(row["weight_variable"]).strip(),
                fixed_effects=split_semicolon(row["fixed_effects"]),
                cluster_level=str(row["cluster_level"]).strip(),
                role=str(row["role"]).strip(),
                notes=str(row["notes"]).strip(),
                sample_filter="" if "sample_filter" not in row or pd.isna(row["sample_filter"]) else str(row["sample_filter"]).strip(),
                filter_notes="" if "filter_notes" not in row or pd.isna(row["filter_notes"]) else str(row["filter_notes"]).strip(),
            )
        )
    return specs


def panel_path(panel_dir: Path, spec: ModelSpec) -> Path:
    return panel_dir / spec.sample_scope / spec.analysis_panel


def model_terms_for_spec(spec: ModelSpec) -> list[str]:
    variables = [spec.dependent_variable, spec.focal_variable]
    variables.extend(spec.controls)
    variables.extend(spec.fixed_effects)
    if spec.weight_variable:
        variables.append(spec.weight_variable)
    if spec.cluster_level:
        variables.append(spec.cluster_level)
    seen: set[str] = set()
    return [var for var in variables if not (var in seen or seen.add(var))]


def filter_source_variables(spec: ModelSpec) -> list[str]:
    if spec.sample_filter == "metadata_clean":
        return ["FLAG_IPEDS_ANY_METADATA_EXPOSURE"]
    if spec.sample_filter in {
        "min_years_10",
        "balanced_full_window",
        "no_suspect_aid_zero",
        "yrp_2017_window",
        "max_pell_window",
        "max_pell_window_no_2020_2021",
        "max_pell_placebo_window",
    }:
        return ["UNITID", "year"]
    if spec.sample_filter == "yrp_2017_window_pre3":
        return ["UNITID", "year", "PELL_EXPOSURE_PRE2017_YEARS_OBSERVED"]
    if spec.sample_filter in {"yrp_2017_window_no_2020_2021", "placebo_2016_window"}:
        return ["UNITID", "year"]
    return []


def source_variables_for_terms(terms: list[str]) -> list[str]:
    variables: list[str] = []
    for term in terms:
        variables.extend(MODEL_DERIVED_TERM_SOURCES.get(term, (term,)))
    seen: set[str] = set()
    return [var for var in variables if not (var in seen or seen.add(var))]


def variables_for_spec(spec: ModelSpec) -> list[str]:
    variables = source_variables_for_terms(model_terms_for_spec(spec))
    variables.extend(filter_source_variables(spec))
    seen: set[str] = set()
    return [var for var in variables if not (var in seen or seen.add(var))]


def add_model_derived_terms(frame: pd.DataFrame, terms: list[str]) -> pd.DataFrame:
    work = frame.copy()
    required = set(terms)
    if "SECTOR_YEAR" in required and {"SECTOR", "year"} <= set(work.columns):
        sector = pd.to_numeric(work["SECTOR"], errors="coerce").astype("Int64").astype(str)
        year = pd.to_numeric(work["year"], errors="coerce").astype("Int64").astype(str)
        work["SECTOR_YEAR"] = sector + "_" + year
    if "SECTOR_PRIVATE_NONPROFIT" in required and "SECTOR" in work.columns:
        work["SECTOR_PRIVATE_NONPROFIT"] = pd.to_numeric(work["SECTOR"], errors="coerce").eq(2).astype(float)
    interaction_terms = {
        "HEADROOM_MAIN_X_PRIVATE_NONPROFIT": "HEADROOM_MAIN",
        "HEADROOM_MAIN_SHARE_COA_X_PRIVATE_NONPROFIT": "HEADROOM_MAIN_SHARE_COA",
    }
    for term, base in interaction_terms.items():
        if term in required and {base, "SECTOR"} <= set(work.columns):
            private_flag = pd.to_numeric(work["SECTOR"], errors="coerce").eq(2).astype(float)
            work[term] = pd.to_numeric(work[base], errors="coerce") * private_flag
    return work


def scope_dir_for_spec(panel_dir: Path, spec: ModelSpec) -> Path:
    return panel_dir / spec.sample_scope


def balance_table(scope_dir: Path) -> pd.DataFrame:
    path = scope_dir / "analysis_panel_balance_by_institution.csv"
    if not path.exists():
        raise FileNotFoundError(f"Panel-balance file not found for sample filter: {path}")
    return pd.read_csv(path)


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"true", "1", "yes", "y"})


def sample_filter_mask(frame: pd.DataFrame, spec: ModelSpec, scope_dir: Path) -> pd.Series:
    if not spec.sample_filter:
        return pd.Series(True, index=frame.index)

    if spec.sample_filter == "metadata_clean":
        if "FLAG_IPEDS_ANY_METADATA_EXPOSURE" not in frame.columns:
            raise ValueError("metadata_clean filter requires FLAG_IPEDS_ANY_METADATA_EXPOSURE")
        return ~bool_series(frame["FLAG_IPEDS_ANY_METADATA_EXPOSURE"])

    if spec.sample_filter == "min_years_10":
        balance = balance_table(scope_dir)
        keep = set(balance.loc[pd.to_numeric(balance["years_observed"], errors="coerce").ge(10), "UNITID"])
        return frame["UNITID"].isin(keep)

    if spec.sample_filter == "balanced_full_window":
        balance = balance_table(scope_dir)
        keep = set(balance.loc[bool_series(balance["balanced_full_window"]), "UNITID"])
        return frame["UNITID"].isin(keep)

    if spec.sample_filter == "no_suspect_aid_zero":
        path = scope_dir / "analysis_aid_zero_suspect_rows.csv"
        if not path.exists():
            raise FileNotFoundError(f"Aid-zero suspect-row file not found for sample filter: {path}")
        suspect = pd.read_csv(path)
        if suspect.empty:
            return pd.Series(True, index=frame.index)
        if "any_issue" in suspect.columns:
            suspect = suspect[bool_series(suspect["any_issue"])]
        suspect_keys = set(zip(pd.to_numeric(suspect["UNITID"], errors="coerce"), pd.to_numeric(suspect["year"], errors="coerce")))
        keys = list(zip(pd.to_numeric(frame["UNITID"], errors="coerce"), pd.to_numeric(frame["year"], errors="coerce")))
        return pd.Series([key not in suspect_keys for key in keys], index=frame.index)

    if spec.sample_filter == "yrp_2017_window":
        years = pd.to_numeric(frame["year"], errors="coerce")
        return years.between(2014, 2023)

    if spec.sample_filter == "max_pell_window":
        years = pd.to_numeric(frame["year"], errors="coerce")
        return years.between(2014, 2023)

    if spec.sample_filter == "max_pell_window_no_2020_2021":
        years = pd.to_numeric(frame["year"], errors="coerce")
        return years.between(2014, 2023) & ~years.isin([2020, 2021])

    if spec.sample_filter == "max_pell_placebo_window":
        years = pd.to_numeric(frame["year"], errors="coerce")
        return years.between(2014, 2016)

    if spec.sample_filter == "yrp_2017_window_pre3":
        if "PELL_EXPOSURE_PRE2017_YEARS_OBSERVED" not in frame.columns:
            raise ValueError("yrp_2017_window_pre3 filter requires PELL_EXPOSURE_PRE2017_YEARS_OBSERVED")
        years = pd.to_numeric(frame["year"], errors="coerce")
        pre_years = pd.to_numeric(frame["PELL_EXPOSURE_PRE2017_YEARS_OBSERVED"], errors="coerce")
        return years.between(2014, 2023) & pre_years.ge(3)

    if spec.sample_filter == "yrp_2017_window_no_2020_2021":
        years = pd.to_numeric(frame["year"], errors="coerce")
        return years.between(2014, 2023) & ~years.isin([2020, 2021])

    if spec.sample_filter == "placebo_2016_window":
        years = pd.to_numeric(frame["year"], errors="coerce")
        return years.between(2014, 2016)

    raise ValueError(f"Unknown sample_filter for {spec.model_id}: {spec.sample_filter}")


def audit_model_plan(
    panel_dir: Path = DEFAULT_PANEL_DIR,
    output_dir: Path = Path("outputs/model_plan"),
    config: Path = DEFAULT_MODEL_CONFIG,
) -> dict[str, Path]:
    specs = load_model_specs(config)
    rows: list[dict[str, object]] = []
    for spec in specs:
        path = panel_path(panel_dir, spec)
        if not path.exists():
            rows.append(
                {
                    "model_id": spec.model_id,
                    "stage": spec.stage,
                    "sample_scope": spec.sample_scope,
                    "panel_exists": False,
                    "panel_path": str(path),
                    "missing_variables": ";".join(variables_for_spec(spec)),
                    "complete_case_rows": 0,
                    "complete_case_institutions": 0,
                    "total_rows": 0,
                    "total_institutions": 0,
                }
            )
            continue

        source_variables = variables_for_spec(spec)
        model_terms = model_terms_for_spec(spec)
        df = pd.read_parquet(path)
        missing = [var for var in source_variables if var not in df.columns]
        if missing:
            complete = df.iloc[0:0]
        else:
            work = add_model_derived_terms(df[source_variables].copy(), model_terms)
            filter_mask = sample_filter_mask(work, spec, scope_dir_for_spec(panel_dir, spec))
            complete = work[filter_mask].dropna(subset=model_terms)
        rows.append(
            {
                "model_id": spec.model_id,
                "stage": spec.stage,
                "sample_scope": spec.sample_scope,
                "role": spec.role,
                "sample_filter": spec.sample_filter,
                "dependent_variable": spec.dependent_variable,
                "focal_variable": spec.focal_variable,
                "controls": ";".join(spec.controls),
                "weight_variable": spec.weight_variable,
                "fixed_effects": ";".join(spec.fixed_effects),
                "cluster_level": spec.cluster_level,
                "panel_exists": True,
                "panel_path": str(path),
                "missing_variables": ";".join(missing),
                "variables_checked": ";".join(source_variables),
                "model_terms_checked": ";".join(model_terms),
                "complete_case_rows": int(len(complete)),
                "complete_case_institutions": int(complete["UNITID"].nunique()) if "UNITID" in complete.columns else 0,
                "total_rows": int(len(df)),
                "total_institutions": int(df["UNITID"].nunique()) if "UNITID" in df.columns else 0,
                "notes": spec.notes,
                "filter_notes": spec.filter_notes,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = output_dir / "model_specification_coverage.csv"
    summary_path = output_dir / "model_plan_summary.json"
    coverage = pd.DataFrame(rows)
    coverage.to_csv(coverage_path, index=False)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config),
        "panel_dir": str(panel_dir),
        "model_specs": int(len(specs)),
        "missing_panel_specs": int((~coverage["panel_exists"]).sum()) if not coverage.empty else 0,
        "specs_with_missing_variables": int(coverage["missing_variables"].fillna("").ne("").sum()) if not coverage.empty else 0,
        "outputs": {
            "coverage": str(coverage_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {"coverage": coverage_path, "summary": summary_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit planned model specifications before estimation.")
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/model_plan"))
    parser.add_argument("--config", type=Path, default=DEFAULT_MODEL_CONFIG)
    args = parser.parse_args()
    paths = audit_model_plan(panel_dir=args.panel_dir, output_dir=args.output_dir, config=args.config)
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
