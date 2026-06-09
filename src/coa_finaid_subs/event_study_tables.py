from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_FIXED_EFFECTS_DIR = Path("outputs/policy_fixed_effects")
DEFAULT_OUTPUT_DIR = Path("outputs/policy_event_study")
EVENT_TERM_PATTERN = re.compile(r"^PELL_EXPOSURE_PRE2017_Z_X_EVENT_(\d{4})$")
REFERENCE_YEAR = 2016
MODEL_OUTCOMES = {
    "yrp2017_event_headroom": "HEADROOM_MAIN",
    "yrp2017_event_inst_grant": "IGRNT_PER_FTFT_COHORT",
}


def event_year_from_term(term: str) -> int | None:
    match = EVENT_TERM_PATTERN.match(term)
    if not match:
        return None
    return int(match.group(1))


def build_policy_event_study_table(
    fixed_effects_dir: Path = DEFAULT_FIXED_EFFECTS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    reference_year: int = REFERENCE_YEAR,
) -> dict[str, Path]:
    coefficients_path = fixed_effects_dir / "fixed_effects_coefficients.csv"
    if not coefficients_path.exists():
        raise FileNotFoundError(f"Policy fixed-effects coefficients not found: {coefficients_path}")

    coefficients = pd.read_csv(coefficients_path)
    rows: list[dict[str, object]] = []
    for record in coefficients.to_dict("records"):
        model_id = str(record.get("model_id", ""))
        if model_id not in MODEL_OUTCOMES:
            continue
        term = str(record.get("term", ""))
        event_year = event_year_from_term(term)
        if event_year is None:
            continue
        rows.append(
            {
                "model_id": model_id,
                "outcome": MODEL_OUTCOMES[model_id],
                "event_year": event_year,
                "relative_year": event_year - reference_year,
                "reference_year": reference_year,
                "term": term,
                "estimate": record.get("estimate"),
                "std_error": record.get("std_error"),
                "t_stat": record.get("t_stat"),
                "p_value_normal": record.get("p_value_normal"),
                "nobs": record.get("nobs"),
                "clusters": record.get("clusters"),
            }
        )

    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError("No event-study coefficient rows found in policy fixed-effects output")

    reference_rows = []
    for model_id, outcome in MODEL_OUTCOMES.items():
        observed = table[table["model_id"].eq(model_id)]
        if observed.empty:
            continue
        first = observed.iloc[0].to_dict()
        reference_rows.append(
            {
                "model_id": model_id,
                "outcome": outcome,
                "event_year": reference_year,
                "relative_year": 0,
                "reference_year": reference_year,
                "term": "omitted_reference_year",
                "estimate": 0.0,
                "std_error": pd.NA,
                "t_stat": pd.NA,
                "p_value_normal": pd.NA,
                "nobs": first.get("nobs"),
                "clusters": first.get("clusters"),
            }
        )
    if reference_rows:
        table = pd.concat([table, pd.DataFrame(reference_rows)], ignore_index=True)

    table = table.sort_values(["model_id", "event_year"]).reset_index(drop=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    table_path = output_dir / "policy_event_study_coefficients.csv"
    summary_path = output_dir / "policy_event_study_summary.json"
    table.to_csv(table_path, index=False)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixed_effects_dir": str(fixed_effects_dir),
        "reference_year": reference_year,
        "models": sorted(table["model_id"].dropna().unique().tolist()),
        "event_years": sorted(int(year) for year in table["event_year"].dropna().unique()),
        "outputs": {"coefficients": str(table_path)},
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {"coefficients": table_path, "summary": summary_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build policy event-study tables from fixed-effects coefficients.")
    parser.add_argument("--fixed-effects-dir", type=Path, default=DEFAULT_FIXED_EFFECTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--reference-year", type=int, default=REFERENCE_YEAR)
    args = parser.parse_args()
    paths = build_policy_event_study_table(
        fixed_effects_dir=args.fixed_effects_dir,
        output_dir=args.output_dir,
        reference_year=args.reference_year,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
