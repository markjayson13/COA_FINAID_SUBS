from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from coa_finaid_subs.estimate_tables import MAIN_MODELS, TERM_LABELS, merge_estimate_metadata, outcome_label


DEFAULT_ANALYSIS_DIR = Path("outputs/analysis_panel/public_private_nonprofit")
DEFAULT_HEADROOM_DIR = Path("outputs/headroom_measures")
DEFAULT_FIXED_EFFECTS_DIR = Path("outputs/fixed_effects")
DEFAULT_OUTPUT_DIR = Path("outputs/figures")

PALETTE = ["#1f4e79", "#9c3d2e", "#4f7f3f", "#6d5a8e", "#8a6f2a"]


def svg_text(text: object) -> str:
    return html.escape("" if pd.isna(text) else str(text))


def value_range(values: pd.Series, include_zero: bool = False) -> tuple[float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return (0.0, 1.0)
    low = float(clean.min())
    high = float(clean.max())
    if include_zero:
        low = min(low, 0.0)
        high = max(high, 0.0)
    if low == high:
        pad = abs(low) * 0.05 if low else 1.0
        return low - pad, high + pad
    pad = (high - low) * 0.08
    return low - pad, high + pad


def scale(value: float, low: float, high: float, start: float, end: float) -> float:
    if high == low:
        return (start + end) / 2
    return start + (value - low) / (high - low) * (end - start)


def write_line_svg(
    path: Path,
    data: pd.DataFrame,
    title: str,
    subtitle: str,
    x_col: str,
    y_col: str,
    group_col: str,
    y_label: str,
) -> None:
    # The SVG writer avoids a plotting dependency while keeping vector output for papers.
    width, height = 960, 560
    left, right, top, bottom = 90, 200, 78, 76
    plot_w = width - left - right
    plot_h = height - top - bottom
    x_low, x_high = value_range(data[x_col])
    y_low, y_high = value_range(data[y_col])

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{svg_text(title)}</title>",
        f"<desc>{svg_text(subtitle)}</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="34" font-family="Arial" font-size="20" font-weight="700">{svg_text(title)}</text>',
        f'<text x="{left}" y="58" font-family="Arial" font-size="13" fill="#444">{svg_text(subtitle)}</text>',
    ]

    for tick in range(5):
        value = y_low + (y_high - y_low) * tick / 4
        y = top + plot_h - tick / 4 * plot_h
        lines.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e7e7e7"/>')
        lines.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{value:,.0f}</text>')

    years = sorted(pd.to_numeric(data[x_col], errors="coerce").dropna().astype(int).unique())
    shown_years = years[::2] if len(years) > 10 else years
    for year in shown_years:
        x = scale(year, x_low, x_high, left, width - right)
        lines.append(f'<text x="{x:.1f}" y="{height-bottom+28}" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">{year}</text>')

    lines.append(f'<line x1="{left}" x2="{width-right}" y1="{height-bottom}" y2="{height-bottom}" stroke="#222"/>')
    lines.append(f'<line x1="{left}" x2="{left}" y1="{top}" y2="{height-bottom}" stroke="#222"/>')
    lines.append(
        f'<text x="22" y="{top + plot_h / 2:.1f}" transform="rotate(-90 22 {top + plot_h / 2:.1f})" '
        f'font-family="Arial" font-size="12" text-anchor="middle" fill="#333">{svg_text(y_label)}</text>'
    )

    for idx, (group, rows) in enumerate(data.groupby(group_col, sort=False)):
        rows = rows.sort_values(x_col)
        color = PALETTE[idx % len(PALETTE)]
        points = [
            f"{scale(float(row[x_col]), x_low, x_high, left, width - right):.1f},"
            f"{scale(float(row[y_col]), y_low, y_high, height - bottom, top):.1f}"
            for row in rows.to_dict("records")
            if pd.notna(row[x_col]) and pd.notna(row[y_col])
        ]
        if points:
            lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        legend_y = top + 24 + idx * 24
        lines.append(f'<line x1="{width-right+28}" x2="{width-right+54}" y1="{legend_y}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<text x="{width-right+62}" y="{legend_y+4}" font-family="Arial" font-size="12" fill="#333">{svg_text(group)}</text>')

    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_forest_svg(path: Path, data: pd.DataFrame, title: str, subtitle: str) -> None:
    width = 980
    row_h = 42
    top = 82
    bottom = 70
    left = 360
    right = 60
    height = top + bottom + max(1, len(data)) * row_h
    x_low, x_high = value_range(pd.concat([data["ci_low"], data["ci_high"]]), include_zero=True)
    axis_y = height - bottom
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{svg_text(title)}</title>",
        f"<desc>{svg_text(subtitle)}</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="28" y="34" font-family="Arial" font-size="20" font-weight="700">{svg_text(title)}</text>',
        f'<text x="28" y="58" font-family="Arial" font-size="13" fill="#444">{svg_text(subtitle)}</text>',
        f'<line x1="{left}" x2="{width-right}" y1="{axis_y}" y2="{axis_y}" stroke="#222"/>',
    ]
    zero_x = scale(0.0, x_low, x_high, left, width - right)
    lines.append(f'<line x1="{zero_x:.1f}" x2="{zero_x:.1f}" y1="{top-14}" y2="{axis_y}" stroke="#888" stroke-dasharray="4 4"/>')

    for tick in range(5):
        value = x_low + (x_high - x_low) * tick / 4
        x = scale(value, x_low, x_high, left, width - right)
        lines.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{axis_y}" y2="{axis_y+6}" stroke="#222"/>')
        lines.append(f'<text x="{x:.1f}" y="{axis_y+24}" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">{value:.2f}</text>')

    for idx, row in enumerate(data.to_dict("records")):
        y = top + idx * row_h
        low_x = scale(float(row["ci_low"]), x_low, x_high, left, width - right)
        high_x = scale(float(row["ci_high"]), x_low, x_high, left, width - right)
        est_x = scale(float(row["estimate"]), x_low, x_high, left, width - right)
        lines.append(f'<text x="28" y="{y+5}" font-family="Arial" font-size="12" fill="#222">{svg_text(row["label"])}</text>')
        lines.append(f'<line x1="{low_x:.1f}" x2="{high_x:.1f}" y1="{y}" y2="{y}" stroke="#1f4e79" stroke-width="2"/>')
        lines.append(f'<circle cx="{est_x:.1f}" cy="{y}" r="5" fill="#1f4e79"/>')
        lines.append(f'<text x="{width-right}" y="{y+5}" text-anchor="end" font-family="Arial" font-size="11" fill="#333">{float(row["estimate"]):.3f}</text>')

    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def sample_count_figure(analysis_dir: Path, output_dir: Path) -> dict[str, Path]:
    source = analysis_dir / "analysis_institution_years_by_sector_year.csv"
    data = pd.read_csv(source)
    data = data[data["sector"].isin(["public", "private_nonprofit"])].copy()
    data["sector"] = data["sector"].replace({"private_nonprofit": "private nonprofit"})
    csv_path = output_dir / "figure_sample_counts_by_sector_year.csv"
    svg_path = output_dir / "figure_sample_counts_by_sector_year.svg"
    data.to_csv(csv_path, index=False)
    write_line_svg(
        svg_path,
        data,
        "Institution-years by sector",
        "Prepared public and private nonprofit analysis panel, 2009-2023.",
        "year",
        "institution_years",
        "sector",
        "Institution-years",
    )
    return {"sample_counts_csv": csv_path, "sample_counts_svg": svg_path}


def headroom_trend_figure(headroom_dir: Path, output_dir: Path) -> dict[str, Path]:
    source = headroom_dir / "headroom_measure_by_sector_year.csv"
    data = pd.read_csv(source)
    data = data[
        data["scope"].eq("public_private_nonprofit")
        & data["measure_id"].eq("main_dollars")
        & data["sector"].isin(["public", "private_nonprofit"])
    ].copy()
    data["sector"] = data["sector"].replace({"private_nonprofit": "private nonprofit"})
    csv_path = output_dir / "figure_headroom_trends_by_sector.csv"
    svg_path = output_dir / "figure_headroom_trends_by_sector.svg"
    data.to_csv(csv_path, index=False)
    write_line_svg(
        svg_path,
        data,
        "COA headroom by sector",
        "FTFT-weighted mean of the main non-tuition COA headroom measure.",
        "year",
        "ftft_weighted_mean",
        "sector",
        "Dollars",
    )
    return {"headroom_trends_csv": csv_path, "headroom_trends_svg": svg_path}


def estimate_forest_figure(fixed_effects_dir: Path, output_dir: Path) -> dict[str, Path]:
    coefficients = pd.read_csv(fixed_effects_dir / "fixed_effects_coefficients.csv")
    diagnostics = pd.read_csv(fixed_effects_dir / "fixed_effects_model_diagnostics.csv")
    merged = merge_estimate_metadata(coefficients, diagnostics)
    rows = merged[
        merged["model_id"].isin(MAIN_MODELS)
        & merged["term"].isin(["HEADROOM_MAIN", "HEADROOM_MAIN_X_PRIVATE_NONPROFIT"])
    ].copy()
    order = {model_id: idx for idx, model_id in enumerate(MAIN_MODELS)}
    rows["order"] = rows["model_id"].map(order).fillna(len(order)).astype(int)
    rows = rows.sort_values(["order", "term_order", "model_id", "term"]).reset_index(drop=True)
    rows["ci_low"] = rows["estimate"] - 1.96 * rows["std_error"]
    rows["ci_high"] = rows["estimate"] + 1.96 * rows["std_error"]
    rows["label"] = rows.apply(lambda row: f"{outcome_label(row.to_dict())}: {TERM_LABELS.get(row['term'], row['term'])}", axis=1)
    data = rows[["model_id", "label", "term", "estimate", "std_error", "ci_low", "ci_high", "p_value_normal", "nobs", "clusters"]]
    csv_path = output_dir / "figure_main_estimate_forest.csv"
    svg_path = output_dir / "figure_main_estimate_forest.svg"
    data.to_csv(csv_path, index=False)
    write_forest_svg(
        svg_path,
        data,
        "Main institutional-grant estimates",
        "Points show coefficient estimates; horizontal bars show 95 percent normal-reference intervals.",
    )
    return {"main_estimate_forest_csv": csv_path, "main_estimate_forest_svg": svg_path}


def build_report_figures(
    analysis_dir: Path = DEFAULT_ANALYSIS_DIR,
    headroom_dir: Path = DEFAULT_HEADROOM_DIR,
    fixed_effects_dir: Path = DEFAULT_FIXED_EFFECTS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    paths.update(sample_count_figure(analysis_dir, output_dir))
    paths.update(headroom_trend_figure(headroom_dir, output_dir))
    paths.update(estimate_forest_figure(fixed_effects_dir, output_dir))
    summary_path = output_dir / "figures_summary.json"
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_dir": str(analysis_dir),
        "headroom_dir": str(headroom_dir),
        "fixed_effects_dir": str(fixed_effects_dir),
        "outputs": {key: str(value) for key, value in paths.items()},
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    paths["summary"] = summary_path
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Build paper-ready SVG figures and figure-data CSVs.")
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--headroom-dir", type=Path, default=DEFAULT_HEADROOM_DIR)
    parser.add_argument("--fixed-effects-dir", type=Path, default=DEFAULT_FIXED_EFFECTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = build_report_figures(
        analysis_dir=args.analysis_dir,
        headroom_dir=args.headroom_dir,
        fixed_effects_dir=args.fixed_effects_dir,
        output_dir=args.output_dir,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
