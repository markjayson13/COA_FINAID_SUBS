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
            )
        )
    return specs


def panel_path(panel_dir: Path, spec: ModelSpec) -> Path:
    return panel_dir / spec.sample_scope / spec.analysis_panel


def variables_for_spec(spec: ModelSpec) -> list[str]:
    variables = [spec.dependent_variable, spec.focal_variable]
    variables.extend(spec.controls)
    variables.extend(spec.fixed_effects)
    if spec.weight_variable:
        variables.append(spec.weight_variable)
    if spec.cluster_level:
        variables.append(spec.cluster_level)
    seen: set[str] = set()
    return [var for var in variables if not (var in seen or seen.add(var))]


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

        variables = variables_for_spec(spec)
        df = pd.read_parquet(path)
        missing = [var for var in variables if var not in df.columns]
        available = [var for var in variables if var in df.columns]
        complete = df.dropna(subset=available) if available and not missing else df.iloc[0:0]
        rows.append(
            {
                "model_id": spec.model_id,
                "stage": spec.stage,
                "sample_scope": spec.sample_scope,
                "role": spec.role,
                "dependent_variable": spec.dependent_variable,
                "focal_variable": spec.focal_variable,
                "controls": ";".join(spec.controls),
                "weight_variable": spec.weight_variable,
                "fixed_effects": ";".join(spec.fixed_effects),
                "cluster_level": spec.cluster_level,
                "panel_exists": True,
                "panel_path": str(path),
                "missing_variables": ";".join(missing),
                "variables_checked": ";".join(variables),
                "complete_case_rows": int(len(complete)),
                "complete_case_institutions": int(complete["UNITID"].nunique()) if "UNITID" in complete.columns else 0,
                "total_rows": int(len(df)),
                "total_institutions": int(df["UNITID"].nunique()) if "UNITID" in df.columns else 0,
                "notes": spec.notes,
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
