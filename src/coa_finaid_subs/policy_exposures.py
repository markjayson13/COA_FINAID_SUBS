from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from coa_finaid_subs.policy_shocks import audit_policy_shock_frame, load_policy_shocks, parse_bool


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL_DIR = REPO_ROOT / "outputs" / "analysis_panel"
DEFAULT_OUTPUT_DIR = Path("outputs/policy_exposure")
DEFAULT_POLICY_SHOCKS_CONFIG = REPO_ROOT / "config" / "policy_shocks.csv"
DEFAULT_POLICY_EXPOSURE_DESIGNS = REPO_ROOT / "config" / "policy_exposure_designs.csv"

SCOPE_PANELS = {
    "public_private_nonprofit": "analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet",
    "public": "analysis_panel_coa_headroom_2009_2023_public.parquet",
    "private_nonprofit": "analysis_panel_coa_headroom_2009_2023_private_nonprofit.parquet",
}

REQUIRED_DESIGN_COLUMNS = {
    "design_id",
    "event_year",
    "pre_start",
    "pre_end",
    "post_start",
    "post_end",
    "min_pre_years",
    "primary_exposure",
    "notes",
}

EXPOSURE_INPUTS = {
    "PELL_EXPOSURE_PRE2017": "PELL_SHARE_OF_TOTAL_GRANT_FTFT",
    "PELL_PER_FTFT_EXPOSURE_PRE2017": "PGRNT_PER_FTFT_COHORT",
    "LOAN_PER_FTFT_EXPOSURE_PRE2017": "FLOAN_PER_FTFT_COHORT",
    "INST_GRANT_SHARE_EXPOSURE_PRE2017": "INST_GRANT_SHARE_OF_TOTAL_GRANT_FTFT",
    "INST_GRANT_PER_FTFT_EXPOSURE_PRE2017": "IGRNT_PER_FTFT_COHORT",
    "FTFT_COHORT_EXPOSURE_PRE2017": "SCFA1N",
}

POLICY_RENAME = {
    "pell_max_award": "POLICY_PELL_MAX_AWARD",
    "pell_max_award_delta": "POLICY_PELL_MAX_AWARD_DELTA",
    "pell_large_increase": "POLICY_PELL_LARGE_INCREASE",
    "additional_pell_authority_status": "POLICY_ADDITIONAL_PELL_AUTHORITY_STATUS",
    "additional_pell_authority_shock": "POLICY_ADDITIONAL_PELL_AUTHORITY_SHOCK",
}


@dataclass(frozen=True)
class PolicyExposureResult:
    paths: dict[str, Path]
    issues: list[str]


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def load_policy_exposure_designs(path: Path = DEFAULT_POLICY_EXPOSURE_DESIGNS) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Policy exposure design config not found: {path}")
    designs = pd.read_csv(path)
    missing = REQUIRED_DESIGN_COLUMNS - set(designs.columns)
    if missing:
        raise ValueError(f"Policy exposure design config is missing columns: {', '.join(sorted(missing))}")
    if designs.empty:
        raise ValueError("Policy exposure design config has no rows")
    duplicated = designs["design_id"][designs["design_id"].duplicated()].dropna().tolist()
    if duplicated:
        raise ValueError(f"Duplicate design_id values: {duplicated}")
    unsupported = sorted(set(designs["design_id"]) - {"yrp2017"})
    if unsupported:
        raise ValueError(f"Unsupported policy exposure design_id values: {unsupported}")
    return designs


def policy_frame(path: Path) -> pd.DataFrame:
    policy = load_policy_shocks(path)
    audit = audit_policy_shock_frame(policy)
    if audit.issues:
        raise ValueError("Policy shock registry failed audit: " + "; ".join(audit.issues))
    keep = ["ipeds_sfa_year", *POLICY_RENAME.keys()]
    work = policy[keep].rename(columns=POLICY_RENAME).copy()
    work["ipeds_sfa_year"] = safe_numeric(work["ipeds_sfa_year"]).astype("Int64")
    work["POLICY_PELL_LARGE_INCREASE"] = work["POLICY_PELL_LARGE_INCREASE"].map(parse_bool)
    for column in ("POLICY_PELL_MAX_AWARD", "POLICY_PELL_MAX_AWARD_DELTA", "POLICY_ADDITIONAL_PELL_AUTHORITY_SHOCK"):
        work[column] = safe_numeric(work[column])
    return work


def within_group_zscore(values: pd.Series, groups: pd.Series, eligible: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype="float64")
    for group_value, group_index in groups[eligible].groupby(groups[eligible]).groups.items():
        idx = pd.Index(group_index)
        group_values = safe_numeric(values.loc[idx])
        mean = group_values.mean()
        sd = group_values.std(ddof=0)
        if pd.notna(sd) and sd > 0:
            result.loc[idx] = (group_values - mean) / sd
    return result


def build_unit_exposures(panel: pd.DataFrame, design: pd.Series) -> pd.DataFrame:
    pre_start = int(design["pre_start"])
    pre_end = int(design["pre_end"])
    min_pre_years = int(design["min_pre_years"])
    pre = panel.loc[safe_numeric(panel["year"]).between(pre_start, pre_end)].copy()
    if pre.empty:
        return pd.DataFrame(columns=["UNITID"])

    for source in EXPOSURE_INPUTS.values():
        if source in pre.columns:
            pre[source] = safe_numeric(pre[source])
    pre["year"] = safe_numeric(pre["year"])
    pre["SECTOR"] = safe_numeric(pre["SECTOR"])

    aggregations: dict[str, str] = {"year": "nunique", "SECTOR": "last"}
    for source in EXPOSURE_INPUTS.values():
        if source in pre.columns:
            aggregations[source] = "mean"
    unit = pre.sort_values(["UNITID", "year"]).groupby("UNITID", dropna=True).agg(aggregations).reset_index()
    unit = unit.rename(columns={"year": "EXPOSURE_PRE2017_YEARS_OBSERVED", "SECTOR": "EXPOSURE_SECTOR_PRE2017"})
    for exposure_name, source in EXPOSURE_INPUTS.items():
        if source in unit.columns:
            unit = unit.rename(columns={source: exposure_name})
        else:
            unit[exposure_name] = np.nan

    unit["EXPOSURE_PRE2017_HAS_MIN_YEARS"] = safe_numeric(unit["EXPOSURE_PRE2017_YEARS_OBSERVED"]).ge(min_pre_years)
    eligible = unit["EXPOSURE_PRE2017_HAS_MIN_YEARS"] & unit["PELL_EXPOSURE_PRE2017"].notna()
    unit["PELL_EXPOSURE_PRE2017_Z_SECTOR"] = within_group_zscore(
        unit["PELL_EXPOSURE_PRE2017"],
        unit["EXPOSURE_SECTOR_PRE2017"],
        eligible,
    )
    return unit


def build_scope_panel(panel: pd.DataFrame, design: pd.Series, policy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    issues: list[str] = []
    event_year = int(design["event_year"])
    pre_start = int(design["pre_start"])
    post_start = int(design["post_start"])
    post_end = int(design["post_end"])

    work = panel.copy()
    work["year"] = safe_numeric(work["year"]).astype("Int64")
    work = work.merge(policy, how="left", left_on="year", right_on="ipeds_sfa_year").drop(columns=["ipeds_sfa_year"])
    policy_missing_years = work.loc[work["POLICY_PELL_MAX_AWARD"].isna(), "year"].dropna().astype(int).unique().tolist()
    if policy_missing_years:
        issues.append(f"Policy shock merge failed for years: {sorted(policy_missing_years)}")

    unit_exposures = build_unit_exposures(work, design)
    work = work.merge(unit_exposures, how="left", on="UNITID")
    work["POST_YRP_2017"] = work["year"].ge(post_start)
    work["YRP_2017_WINDOW"] = work["year"].between(pre_start, post_end)
    work["YRP_2017_EVENT_YEAR"] = work["year"].eq(event_year)
    work["PELL_MAX_AWARD_DELTA_100"] = safe_numeric(work["POLICY_PELL_MAX_AWARD_DELTA"]) / 100.0
    work["PELL_EXPOSURE_PRE2017_Z_X_POST_YRP_2017"] = (
        safe_numeric(work["PELL_EXPOSURE_PRE2017_Z_SECTOR"]) * work["POST_YRP_2017"].astype(float)
    )
    work["PELL_EXPOSURE_PRE2017_Z_X_PELL_MAX_AWARD_DELTA_100"] = (
        safe_numeric(work["PELL_EXPOSURE_PRE2017_Z_SECTOR"]) * safe_numeric(work["PELL_MAX_AWARD_DELTA_100"])
    )

    window = work[work["YRP_2017_WINDOW"]].copy()
    if window.empty:
        issues.append("Policy exposure panel has no rows in the 2017 year-round Pell window")
    if window["POST_YRP_2017"].nunique(dropna=True) < 2:
        issues.append("Policy exposure panel lacks both pre- and post-2017 rows")
    if window["PELL_EXPOSURE_PRE2017_Z_X_POST_YRP_2017"].nunique(dropna=True) <= 1:
        issues.append("Main policy exposure interaction has no usable variation")
    if unit_exposures.empty or unit_exposures["PELL_EXPOSURE_PRE2017_Z_SECTOR"].notna().sum() == 0:
        issues.append("No institutions have a usable pre-2017 Pell exposure")

    audit = work.copy()
    audit["EXPOSURE_AVAILABLE"] = audit["PELL_EXPOSURE_PRE2017_Z_SECTOR"].notna()
    by_year = (
        audit.groupby(["year", "SECTOR"], dropna=False)
        .agg(
            institution_years=("UNITID", "size"),
            institutions=("UNITID", "nunique"),
            exposure_available_rows=("EXPOSURE_AVAILABLE", "sum"),
            policy_pell_max_award=("POLICY_PELL_MAX_AWARD", "first"),
            policy_pell_max_award_delta=("POLICY_PELL_MAX_AWARD_DELTA", "first"),
            post_yrp_2017=("POST_YRP_2017", "first"),
        )
        .reset_index()
    )
    return work, unit_exposures, by_year, issues


def scope_panel_path(panel_dir: Path, scope: str) -> Path:
    return panel_dir / scope / SCOPE_PANELS[scope]


def build_policy_exposure_panels(
    panel_dir: Path = DEFAULT_PANEL_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    policy_config: Path = DEFAULT_POLICY_SHOCKS_CONFIG,
    design_config: Path = DEFAULT_POLICY_EXPOSURE_DESIGNS,
) -> dict[str, Path]:
    designs = load_policy_exposure_designs(design_config)
    design = designs.iloc[0]
    policy = policy_frame(policy_config)

    output_dir.mkdir(parents=True, exist_ok=True)
    all_issues: list[str] = []
    outputs: dict[str, Path] = {}
    summary_rows: list[dict[str, object]] = []

    for scope in SCOPE_PANELS:
        input_path = scope_panel_path(panel_dir, scope)
        if not input_path.exists():
            all_issues.append(f"Input panel not found for {scope}: {input_path}")
            continue
        scope_dir = output_dir / scope
        scope_dir.mkdir(parents=True, exist_ok=True)
        panel = pd.read_parquet(input_path)
        exposure_panel, unit_audit, by_year, issues = build_scope_panel(panel, design, policy)
        all_issues.extend(f"{scope}: {issue}" for issue in issues)

        panel_path = scope_dir / f"policy_exposure_panel_{scope}.parquet"
        unit_path = scope_dir / "policy_exposure_unit_audit.csv"
        by_year_path = scope_dir / "policy_exposure_by_year.csv"
        exposure_panel.to_parquet(panel_path, index=False)
        unit_audit.to_csv(unit_path, index=False)
        by_year.to_csv(by_year_path, index=False)

        window = exposure_panel[exposure_panel["YRP_2017_WINDOW"]]
        summary_rows.append(
            {
                "scope": scope,
                "input_panel": str(input_path),
                "output_panel": str(panel_path),
                "rows": int(len(exposure_panel)),
                "institutions": int(exposure_panel["UNITID"].nunique(dropna=True)),
                "window_rows": int(len(window)),
                "window_institutions": int(window["UNITID"].nunique(dropna=True)) if not window.empty else 0,
                "exposure_institutions": int(unit_audit["PELL_EXPOSURE_PRE2017_Z_SECTOR"].notna().sum()) if not unit_audit.empty else 0,
                "pre_start": int(design["pre_start"]),
                "pre_end": int(design["pre_end"]),
                "post_start": int(design["post_start"]),
                "post_end": int(design["post_end"]),
            }
        )
        outputs[f"{scope}_panel"] = panel_path
        outputs[f"{scope}_unit_audit"] = unit_path
        outputs[f"{scope}_by_year"] = by_year_path

    summary = pd.DataFrame(summary_rows)
    summary_csv = output_dir / "policy_exposure_summary.csv"
    summary_json = output_dir / "policy_exposure_summary.json"
    design_audit = output_dir / "policy_exposure_design_audit.csv"
    summary.to_csv(summary_csv, index=False)
    designs.to_csv(design_audit, index=False)
    summary_payload = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "panel_dir": str(panel_dir),
        "policy_config": str(policy_config),
        "design_config": str(design_config),
        "design_id": str(design["design_id"]),
        "scopes_written": int(len(summary_rows)),
        "issue_count": int(len(all_issues)),
        "issues": all_issues,
        "outputs": {key: str(path) for key, path in outputs.items()},
    }
    summary_json.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    outputs["summary_csv"] = summary_csv
    outputs["summary_json"] = summary_json
    outputs["design_audit"] = design_audit
    if all_issues:
        raise SystemExit("Policy exposure build failed: " + "; ".join(all_issues))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build audited policy-exposure panels for policy-shock estimation.")
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--policy-config", type=Path, default=DEFAULT_POLICY_SHOCKS_CONFIG)
    parser.add_argument("--design-config", type=Path, default=DEFAULT_POLICY_EXPOSURE_DESIGNS)
    args = parser.parse_args()
    paths = build_policy_exposure_panels(
        panel_dir=args.panel_dir,
        output_dir=args.output_dir,
        policy_config=args.policy_config,
        design_config=args.design_config,
    )
    print(f"Wrote {paths['summary_json'].parent}")


if __name__ == "__main__":
    main()
