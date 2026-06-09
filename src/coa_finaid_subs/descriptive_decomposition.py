from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL_DIR = REPO_ROOT / "outputs" / "analysis_panel"

TREND_VARIABLES = (
    "COA_MAIN",
    "HEADROOM_MAIN",
    "HEADROOM_MAIN_SHARE_COA",
    "HEADROOM_MAIN_SHARE_TUITION",
    "CHG2AY0",
    "CHG4AY0",
    "CHG7AY0",
    "CHG8AY0",
    "HEADROOM_ON",
    "HEADROOM_OFF_WF",
    "IGRNT_PER_FTFT_COHORT",
    "PGRNT_PER_FTFT_COHORT",
    "FLOAN_PER_FTFT_COHORT",
    "INST_GRANT_SHARE_OF_TOTAL_GRANT_FTFT",
    "PELL_SHARE_OF_TOTAL_GRANT_FTFT",
)
COA_COMPONENTS = {
    "tuition_fees": "CHG2AY0",
    "books_supplies": "CHG4AY0",
    "off_nf_room_board": "CHG7AY0",
    "off_nf_other_expenses": "CHG8AY0",
}
DERIVED_TOTALS = {
    "coa_main": "COA_MAIN",
    "headroom_main": "HEADROOM_MAIN",
}


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


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
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


def value_or_none(series: pd.Series, method: str) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    value = getattr(clean, method)()
    if pd.isna(value):
        return None
    return float(value)


def trend_table(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    if "year" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["sector"] = work["SECTOR"].map(sector_label) if "SECTOR" in work.columns else "all"
    rows: list[dict[str, object]] = []
    variables = [var for var in TREND_VARIABLES if var in work.columns]
    years = sorted(pd.to_numeric(work["year"], errors="coerce").dropna().astype(int).unique())
    sectors = ["all"] + sorted(str(sector) for sector in work["sector"].dropna().unique())

    for sector in sectors:
        sector_df = work if sector == "all" else work[work["sector"].eq(sector)]
        for year in years:
            group = sector_df[pd.to_numeric(sector_df["year"], errors="coerce").eq(year)]
            if group.empty:
                continue
            weight = numeric(group, "SCFA1N")
            for var in variables:
                values = numeric(group, var)
                rows.append(
                    {
                        "scope": scope,
                        "sector": sector,
                        "year": year,
                        "varname": var,
                        "rows": int(len(group)),
                        "nonnull_rows": int(values.notna().sum()),
                        "nonmissing_unitids": int(group.loc[values.notna(), "UNITID"].nunique()) if "UNITID" in group.columns else 0,
                        "mean": value_or_none(values, "mean"),
                        "p50": value_or_none(values, "median"),
                        "ftft_weighted_mean": weighted_mean(values, weight),
                    }
                )
    return pd.DataFrame(rows)


def stable_sector_pairs(df: pd.DataFrame, from_year: int, to_year: int) -> pd.DataFrame:
    needed = ["UNITID", "year", "SECTOR", "SCFA1N", *COA_COMPONENTS.values(), *DERIVED_TOTALS.values()]
    available = [col for col in needed if col in df.columns]
    work = df[available].copy()
    work["year"] = pd.to_numeric(work["year"], errors="coerce")
    left = work[work["year"].eq(from_year)].copy()
    right = work[work["year"].eq(to_year)].copy()
    pair = left.merge(right, on="UNITID", suffixes=("_from", "_to"))
    if pair.empty:
        return pair
    pair["sector_from_label"] = pair["SECTOR_from"].map(sector_label) if "SECTOR_from" in pair.columns else "missing"
    pair["sector_to_label"] = pair["SECTOR_to"].map(sector_label) if "SECTOR_to" in pair.columns else "missing"
    pair["stable_sector"] = pair["sector_from_label"].eq(pair["sector_to_label"])
    return pair[pair["stable_sector"]].copy()


def complete_component_mask(pair: pd.DataFrame) -> pd.Series:
    fields: list[str] = []
    for col in (*COA_COMPONENTS.values(), *DERIVED_TOTALS.values()):
        fields.extend([f"{col}_from", f"{col}_to"])
    present = [field for field in fields if field in pair.columns]
    if not present:
        return pd.Series(False, index=pair.index)
    return pair[present].apply(pd.to_numeric, errors="coerce").notna().all(axis=1)


def component_change_rows(pair: pd.DataFrame, scope: str, from_year: int, to_year: int, window: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if pair.empty:
        return rows
    mask = complete_component_mask(pair)
    complete = pair[mask].copy()
    if complete.empty:
        return rows

    sectors = ["all"] + sorted(str(sector) for sector in complete["sector_from_label"].dropna().unique())
    for sector in sectors:
        group = complete if sector == "all" else complete[complete["sector_from_label"].eq(sector)]
        if group.empty:
            continue
        weights = pd.to_numeric(group.get("SCFA1N_from", pd.Series(pd.NA, index=group.index)), errors="coerce")
        change: dict[str, pd.Series] = {}
        for name, col in COA_COMPONENTS.items():
            change[name] = pd.to_numeric(group[f"{col}_to"], errors="coerce") - pd.to_numeric(group[f"{col}_from"], errors="coerce")
        for name, col in DERIVED_TOTALS.items():
            change[name] = pd.to_numeric(group[f"{col}_to"], errors="coerce") - pd.to_numeric(group[f"{col}_from"], errors="coerce")

        allowance_sum = change["books_supplies"] + change["off_nf_room_board"] + change["off_nf_other_expenses"]
        component_sum = change["tuition_fees"] + allowance_sum
        coa_change = change["coa_main"]
        headroom_change = change["headroom_main"]
        row = {
            "scope": scope,
            "window": window,
            "sector": sector,
            "from_year": from_year,
            "to_year": to_year,
            "paired_institutions": int(group["UNITID"].nunique()) if "UNITID" in group.columns else int(len(group)),
            "mean_coa_main_change": value_or_none(coa_change, "mean"),
            "mean_headroom_main_change": value_or_none(headroom_change, "mean"),
            "mean_tuition_fees_change": value_or_none(change["tuition_fees"], "mean"),
            "mean_books_supplies_change": value_or_none(change["books_supplies"], "mean"),
            "mean_off_nf_room_board_change": value_or_none(change["off_nf_room_board"], "mean"),
            "mean_off_nf_other_expenses_change": value_or_none(change["off_nf_other_expenses"], "mean"),
            "mean_coa_change_minus_component_sum": value_or_none(coa_change - component_sum, "mean"),
            "mean_headroom_change_minus_allowance_sum": value_or_none(headroom_change - allowance_sum, "mean"),
            "ftft_weighted_coa_main_change": weighted_mean(coa_change, weights),
            "ftft_weighted_headroom_main_change": weighted_mean(headroom_change, weights),
            "ftft_weighted_tuition_fees_change": weighted_mean(change["tuition_fees"], weights),
            "ftft_weighted_books_supplies_change": weighted_mean(change["books_supplies"], weights),
            "ftft_weighted_off_nf_room_board_change": weighted_mean(change["off_nf_room_board"], weights),
            "ftft_weighted_off_nf_other_expenses_change": weighted_mean(change["off_nf_other_expenses"], weights),
        }
        mean_coa = row["mean_coa_main_change"]
        if mean_coa not in (None, 0):
            for key in (
                "mean_tuition_fees_change",
                "mean_books_supplies_change",
                "mean_off_nf_room_board_change",
                "mean_off_nf_other_expenses_change",
            ):
                row[f"{key}_share_of_coa_change"] = None if row[key] is None else float(row[key] / mean_coa)
        rows.append(row)
    return rows


def adjacent_change_table(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    years = sorted(pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique()) if "year" in df.columns else []
    rows: list[dict[str, object]] = []
    for from_year, to_year in zip(years, years[1:]):
        if to_year != from_year + 1:
            continue
        pair = stable_sector_pairs(df, from_year, to_year)
        rows.extend(component_change_rows(pair, scope, from_year, to_year, "adjacent_year"))
    return pd.DataFrame(rows)


def full_window_change_table(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    years = sorted(pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique()) if "year" in df.columns else []
    if len(years) < 2:
        return pd.DataFrame()
    pair = stable_sector_pairs(df, years[0], years[-1])
    return pd.DataFrame(component_change_rows(pair, scope, years[0], years[-1], "full_window"))


def build_descriptive_decomposition(
    panel_dir: Path = DEFAULT_PANEL_DIR,
    output_dir: Path = Path("outputs/descriptive_decomposition"),
    input_panels: list[Path] | None = None,
) -> dict[str, Path]:
    paths = panel_paths(panel_dir, input_panels)
    trend_frames: list[pd.DataFrame] = []
    adjacent_frames: list[pd.DataFrame] = []
    full_window_frames: list[pd.DataFrame] = []
    for path in paths:
        df = pd.read_parquet(path)
        scope = infer_scope(path)
        trend_frames.append(trend_table(df, scope))
        adjacent_frames.append(adjacent_change_table(df, scope))
        full_window_frames.append(full_window_change_table(df, scope))

    output_dir.mkdir(parents=True, exist_ok=True)
    trend_path = output_dir / "decomposition_trends_by_sector_year.csv"
    adjacent_path = output_dir / "coa_adjacent_year_component_changes.csv"
    full_window_path = output_dir / "coa_full_window_component_changes.csv"
    summary_path = output_dir / "descriptive_decomposition_summary.json"

    trends = pd.concat(trend_frames, ignore_index=True) if trend_frames else pd.DataFrame()
    adjacent = pd.concat(adjacent_frames, ignore_index=True) if adjacent_frames else pd.DataFrame()
    full_window = pd.concat(full_window_frames, ignore_index=True) if full_window_frames else pd.DataFrame()
    trends.to_csv(trend_path, index=False)
    adjacent.to_csv(adjacent_path, index=False)
    full_window.to_csv(full_window_path, index=False)

    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "panel_dir": str(panel_dir),
        "input_panels": [str(path) for path in paths],
        "panels_checked": int(len(paths)),
        "trend_rows": int(len(trends)),
        "adjacent_change_rows": int(len(adjacent)),
        "full_window_change_rows": int(len(full_window)),
        "outputs": {
            "trends_by_sector_year": str(trend_path),
            "adjacent_year_component_changes": str(adjacent_path),
            "full_window_component_changes": str(full_window_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "trends": trend_path,
        "adjacent_changes": adjacent_path,
        "full_window_changes": full_window_path,
        "summary": summary_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build descriptive COA component trend and change tables.")
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/descriptive_decomposition"))
    parser.add_argument("--input-panel", type=Path, action="append", default=None)
    args = parser.parse_args()
    paths = build_descriptive_decomposition(
        panel_dir=args.panel_dir,
        output_dir=args.output_dir,
        input_panels=args.input_panel,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
