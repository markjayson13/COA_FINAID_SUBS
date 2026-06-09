from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_SHOCKS_CONFIG = REPO_ROOT / "config" / "policy_shocks.csv"
DEFAULT_OUTPUT_DIR = Path("outputs/policy_shocks")

REQUIRED_COLUMNS = {
    "award_year_start",
    "award_year_label",
    "ipeds_sfa_year",
    "pell_max_award",
    "pell_max_award_delta",
    "pell_large_increase",
    "additional_pell_authority_status",
    "additional_pell_authority_shock",
    "source_key",
    "source_date",
    "source_title",
    "source_url",
    "additional_pell_source_key",
    "additional_pell_source_url",
    "verification_status",
    "notes",
}

VALID_AUTHORITY_STATUSES = {
    "second_scheduled_award_available",
    "capped_at_one_scheduled_award",
    "up_to_150_percent_scheduled_award",
}
FSA_URL_PREFIX = "https://fsapartners.ed.gov/"


@dataclass(frozen=True)
class PolicyShockAudit:
    table: pd.DataFrame
    issues: list[str]


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_policy_shocks(path: Path = DEFAULT_POLICY_SHOCKS_CONFIG) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Policy shock config not found: {path}")
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Policy shock config is missing columns: {', '.join(sorted(missing))}")
    if df.empty:
        raise ValueError("Policy shock config has no rows")
    return df


def audit_policy_shock_frame(df: pd.DataFrame) -> PolicyShockAudit:
    work = df.copy()
    issues: list[str] = []

    work["award_year_start"] = pd.to_numeric(work["award_year_start"], errors="coerce").astype("Int64")
    work["ipeds_sfa_year"] = pd.to_numeric(work["ipeds_sfa_year"], errors="coerce").astype("Int64")
    work["pell_max_award"] = pd.to_numeric(work["pell_max_award"], errors="coerce")
    work["pell_max_award_delta"] = pd.to_numeric(work["pell_max_award_delta"], errors="coerce")
    work["additional_pell_authority_shock"] = pd.to_numeric(work["additional_pell_authority_shock"], errors="coerce")
    work["pell_large_increase_bool"] = work["pell_large_increase"].map(parse_bool)
    work = work.sort_values("award_year_start").reset_index(drop=True)

    numeric_columns = [
        "award_year_start",
        "ipeds_sfa_year",
        "pell_max_award",
        "pell_max_award_delta",
        "additional_pell_authority_shock",
    ]
    for column in numeric_columns:
        missing_years = work.loc[work[column].isna(), "award_year_start"].dropna().astype(int).tolist()
        if missing_years:
            issues.append(f"Missing or nonnumeric {column} for: {missing_years}")

    duplicate_years = work["award_year_start"][work["award_year_start"].duplicated()].dropna().tolist()
    if duplicate_years:
        issues.append(f"Duplicate award_year_start values: {duplicate_years}")

    expected_years = list(range(int(work["award_year_start"].min()), int(work["award_year_start"].max()) + 1))
    observed_years = work["award_year_start"].dropna().astype(int).tolist()
    if observed_years != expected_years:
        issues.append("Award years are not contiguous after sorting")

    mismatched_ipeds_years = work.loc[work["award_year_start"].ne(work["ipeds_sfa_year"]), "award_year_start"].dropna().astype(int).tolist()
    if mismatched_ipeds_years:
        issues.append(f"IPEDS SFA year does not match award_year_start for: {mismatched_ipeds_years}")

    expected_labels = work["award_year_start"].map(lambda year: f"{int(year)}-{int(year) + 1}")
    label_mismatch = work.loc[work["award_year_label"].ne(expected_labels), "award_year_start"].dropna().astype(int).tolist()
    if label_mismatch:
        issues.append(f"award_year_label mismatch for: {label_mismatch}")

    expected_delta = work["pell_max_award"].diff().fillna(0)
    delta_mismatch = work.loc[work["pell_max_award_delta"].sub(expected_delta).abs().gt(1e-9), "award_year_start"].dropna().astype(int).tolist()
    if delta_mismatch:
        issues.append(f"pell_max_award_delta mismatch for: {delta_mismatch}")

    expected_large = work["pell_max_award_delta"].ge(150)
    large_mismatch = work.loc[work["pell_large_increase_bool"].ne(expected_large), "award_year_start"].dropna().astype(int).tolist()
    if large_mismatch:
        issues.append(f"pell_large_increase mismatch for: {large_mismatch}")

    bad_status = sorted(set(work["additional_pell_authority_status"].dropna()) - VALID_AUTHORITY_STATUSES)
    if bad_status:
        issues.append(f"Unknown additional Pell authority status: {bad_status}")

    expected_status = work["award_year_start"].map(
        lambda year: (
            "second_scheduled_award_available"
            if int(year) <= 2010
            else "capped_at_one_scheduled_award"
            if int(year) <= 2016
            else "up_to_150_percent_scheduled_award"
        )
    )
    status_mismatch = work.loc[
        work["additional_pell_authority_status"].ne(expected_status),
        "award_year_start",
    ].dropna().astype(int).tolist()
    if status_mismatch:
        issues.append(f"additional_pell_authority_status mismatch for: {status_mismatch}")

    expected_shock = work["award_year_start"].map(lambda year: -1 if int(year) == 2011 else 1 if int(year) == 2017 else 0)
    shock_mismatch = work.loc[
        work["additional_pell_authority_shock"].ne(expected_shock),
        "award_year_start",
    ].dropna().astype(int).tolist()
    if shock_mismatch:
        issues.append(f"additional_pell_authority_shock mismatch for: {shock_mismatch}")

    unverified = work.loc[work["verification_status"].ne("verified"), "award_year_start"].dropna().astype(int).tolist()
    if unverified:
        issues.append(f"Unverified policy shock rows: {unverified}")

    missing_source = work.loc[
        work["source_url"].isna()
        | work["source_url"].astype(str).str.strip().eq("")
        | work["source_key"].isna()
        | work["source_key"].astype(str).str.strip().eq("")
        | work["source_title"].isna()
        | work["source_title"].astype(str).str.strip().eq(""),
        "award_year_start",
    ].dropna().astype(int).tolist()
    if missing_source:
        issues.append(f"Rows missing source metadata: {missing_source}")

    bad_source_dates = work.loc[
        pd.to_datetime(work["source_date"], format="%Y-%m-%d", errors="coerce").isna(),
        "award_year_start",
    ].dropna().astype(int).tolist()
    if bad_source_dates:
        issues.append(f"Rows with invalid source_date values: {bad_source_dates}")

    non_fsa_sources = work.loc[
        ~work["source_url"].astype(str).str.startswith(FSA_URL_PREFIX),
        "award_year_start",
    ].dropna().astype(int).tolist()
    if non_fsa_sources:
        issues.append(f"Rows with non-FSA source URLs: {non_fsa_sources}")

    event_rows = work["additional_pell_authority_shock"].ne(0)
    missing_event_source = work.loc[
        event_rows
        & (
            work["additional_pell_source_url"].isna()
            | work["additional_pell_source_url"].astype(str).str.strip().eq("")
            | work["additional_pell_source_key"].isna()
            | work["additional_pell_source_key"].astype(str).str.strip().eq("")
        ),
        "award_year_start",
    ].dropna().astype(int).tolist()
    if missing_event_source:
        issues.append(f"Rows missing additional Pell event source metadata: {missing_event_source}")

    non_fsa_event_sources = work.loc[
        event_rows & ~work["additional_pell_source_url"].astype(str).str.startswith(FSA_URL_PREFIX),
        "award_year_start",
    ].dropna().astype(int).tolist()
    if non_fsa_event_sources:
        issues.append(f"Rows with non-FSA additional Pell event source URLs: {non_fsa_event_sources}")

    work["pell_max_award_pct_change"] = work["pell_max_award"].pct_change().fillna(0.0)
    work["audit_status"] = "pass" if not issues else "fail"
    return PolicyShockAudit(table=work, issues=issues)


def audit_policy_shocks(
    config: Path = DEFAULT_POLICY_SHOCKS_CONFIG,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    df = load_policy_shocks(config)
    audit = audit_policy_shock_frame(df)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / "policy_shock_audit.csv"
    summary_path = output_dir / "policy_shock_summary.json"
    audit.table.to_csv(audit_path, index=False)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config),
        "rows": int(len(audit.table)),
        "min_award_year": int(audit.table["award_year_start"].min()),
        "max_award_year": int(audit.table["award_year_start"].max()),
        "large_pell_increase_years": audit.table.loc[audit.table["pell_large_increase_bool"], "award_year_start"].astype(int).tolist(),
        "additional_pell_authority_shock_years": audit.table.loc[
            audit.table["additional_pell_authority_shock"].ne(0),
            "award_year_start",
        ].astype(int).tolist(),
        "issue_count": len(audit.issues),
        "issues": audit.issues,
        "outputs": {
            "audit": str(audit_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if audit.issues:
        raise SystemExit("Policy shock audit failed: " + "; ".join(audit.issues))
    return {"audit": audit_path, "summary": summary_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the policy-shock registry before exposure designs use it.")
    parser.add_argument("--config", type=Path, default=DEFAULT_POLICY_SHOCKS_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = audit_policy_shocks(config=args.config, output_dir=args.output_dir)
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
