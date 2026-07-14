from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from coa_finaid_subs.manuscript_exhibits import (
    DEFAULT_ANALYSIS_ROOT,
    DEFAULT_FMR_COMPARISON,
    DEFAULT_MODEL_SAMPLE_DIR,
    build_manuscript_exhibit_data,
)


DEFAULT_ANALYSIS_DIR = Path("outputs/analysis_panel/public_private_nonprofit")
DEFAULT_HEADROOM_DIR = Path("outputs/headroom_measures")
DEFAULT_FIXED_EFFECTS_DIR = Path("outputs/fixed_effects")
DEFAULT_DECOMPOSITION_DIR = Path("outputs/descriptive_decomposition")
DEFAULT_MANUSCRIPT_DIR = Path("outputs/manuscript")
DEFAULT_OUTPUT_DIR = Path("outputs/figures")

PRIVATE_COLOR = "#1f4e79"
PUBLIC_COLOR = "#a6402d"
TUITION_COLOR = "#1f4e79"
HEADROOM_COLOR = "#b58b2a"
GRID_COLOR = "#e5e7eb"
TEXT_COLOR = "#252525"
MUTED_COLOR = "#5f6368"

SECTOR_LABELS = {"public": "Public", "private_nonprofit": "Private nonprofit"}
SECTOR_COLORS = {"Public": PUBLIC_COLOR, "Private nonprofit": PRIVATE_COLOR}
ROBUSTNESS_ORDER = ["Baseline", "FTFT-weighted", "Selective-admissions sample", "HUD FMR local rent control"]
AID_OUTCOME_ORDER = ["Institutional grants", "Pell grants", "Federal loans"]
COMPONENT_ORDER = ["Tuition and fees", "Books and supplies", "Off-campus room and board", "Other expenses"]
COMPONENT_TERMS = {
    "CHG2AY0": "Tuition and fees",
    "CHG4AY0": "Books and supplies",
    "CHG7AY0": "Off-campus room and board",
    "CHG8AY0": "Other expenses",
}
COMPONENT_MODELS = {
    "public_component_horse_race_inst_grant": "Public",
    "private_np_component_horse_race_inst_grant": "Private nonprofit",
}


def svg_text(text: object) -> str:
    return html.escape("" if pd.isna(text) else str(text))


def require_columns(data: pd.DataFrame, columns: set[str], source: Path) -> None:
    missing = sorted(columns - set(data.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {', '.join(missing)}")


def value_range(values: pd.Series, include_zero: bool = False, pad_share: float = 0.10) -> tuple[float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return (0.0, 1.0)
    low = float(clean.min())
    high = float(clean.max())
    if include_zero:
        low = min(low, 0.0)
        high = max(high, 0.0)
    if low == high:
        pad = abs(low) * pad_share if low else 1.0
        return low - pad, high + pad
    pad = (high - low) * pad_share
    return low - pad, high + pad


def scale(value: float, low: float, high: float, start: float, end: float) -> float:
    if high == low:
        return (start + end) / 2
    return start + (value - low) / (high - low) * (end - start)


def signed_dollar(value: float) -> str:
    rounded = int(round(value))
    if rounded > 0:
        return f"+${rounded:,}"
    if rounded < 0:
        return f"-${abs(rounded):,}"
    return "$0"


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
    # These trend figures are appendix diagnostics; the main text uses denser comparisons.
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
        f'<text x="{left}" y="34" font-family="Arial" font-size="20" font-weight="700" fill="{TEXT_COLOR}">{svg_text(title)}</text>',
        f'<text x="{left}" y="58" font-family="Arial" font-size="13" fill="{MUTED_COLOR}">{svg_text(subtitle)}</text>',
    ]

    for tick in range(5):
        value = y_low + (y_high - y_low) * tick / 4
        y = top + plot_h - tick / 4 * plot_h
        lines.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID_COLOR}"/>')
        lines.append(
            f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="{MUTED_COLOR}">{value:,.0f}</text>'
        )

    years = sorted(pd.to_numeric(data[x_col], errors="coerce").dropna().astype(int).unique())
    shown_years = years[::2] if len(years) > 10 else years
    for year in shown_years:
        x = scale(year, x_low, x_high, left, width - right)
        lines.append(
            f'<text x="{x:.1f}" y="{height-bottom+28}" text-anchor="middle" font-family="Arial" font-size="11" fill="{MUTED_COLOR}">{year}</text>'
        )

    lines.append(f'<line x1="{left}" x2="{width-right}" y1="{height-bottom}" y2="{height-bottom}" stroke="{TEXT_COLOR}"/>')
    lines.append(f'<line x1="{left}" x2="{left}" y1="{top}" y2="{height-bottom}" stroke="{TEXT_COLOR}"/>')
    lines.append(
        f'<text x="22" y="{top + plot_h / 2:.1f}" transform="rotate(-90 22 {top + plot_h / 2:.1f})" '
        f'font-family="Arial" font-size="12" text-anchor="middle" fill="{TEXT_COLOR}">{svg_text(y_label)}</text>'
    )

    for group, rows in data.groupby(group_col, sort=False):
        rows = rows.sort_values(x_col)
        label = SECTOR_LABELS.get(str(group), str(group).replace("_", " ").title())
        color = SECTOR_COLORS.get(label, PRIVATE_COLOR)
        points = [
            f"{scale(float(row[x_col]), x_low, x_high, left, width - right):.1f},"
            f"{scale(float(row[y_col]), y_low, y_high, height - bottom, top):.1f}"
            for row in rows.to_dict("records")
            if pd.notna(row[x_col]) and pd.notna(row[y_col])
        ]
        if points:
            lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.8"/>')
            last = rows.dropna(subset=[x_col, y_col]).iloc[-1]
            last_x = scale(float(last[x_col]), x_low, x_high, left, width - right)
            last_y = scale(float(last[y_col]), y_low, y_high, height - bottom, top)
            lines.append(f'<text x="{last_x+12:.1f}" y="{last_y+4:.1f}" font-family="Arial" font-size="12" fill="{color}">{svg_text(label)}</text>')

    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_decomposition_svg(path: Path, data: pd.DataFrame) -> None:
    width, height = 980, 610
    left, right, top, bottom = 120, 70, 120, 105
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_max = float(data["total_change"].max()) * 1.18
    y_min = 0.0
    bar_width = 175
    centers = [left + plot_w * 0.32, left + plot_w * 0.72]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<title>Same-institution change in published cost of attendance</title>",
        "<desc>Stacked bars decompose mean 2009-2023 cost-of-attendance changes into tuition and fees and non-tuition headroom for public and private nonprofit institutions.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="38" font-family="Arial" font-size="21" font-weight="700" fill="{TEXT_COLOR}">Same-institution change in published cost of attendance</text>',
        f'<text x="{left}" y="64" font-family="Arial" font-size="13" fill="{MUTED_COLOR}">Mean nominal-dollar change, 2009-2023; institutions observed with complete components in both years</text>',
        f'<rect x="{left}" y="82" width="14" height="14" fill="{TUITION_COLOR}"/>',
        f'<text x="{left+22}" y="94" font-family="Arial" font-size="12" fill="{TEXT_COLOR}">Tuition and fees</text>',
        f'<rect x="{left+170}" y="82" width="14" height="14" fill="{HEADROOM_COLOR}"/>',
        f'<text x="{left+192}" y="94" font-family="Arial" font-size="12" fill="{TEXT_COLOR}">Non-tuition headroom</text>',
    ]

    for tick in range(5):
        value = y_max * tick / 4
        y = scale(value, y_min, y_max, top + plot_h, top)
        lines.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID_COLOR}"/>')
        lines.append(
            f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="{MUTED_COLOR}">${value/1000:.0f}k</text>'
        )

    for center, row in zip(centers, data.to_dict("records"), strict=True):
        tuition = float(row["tuition_change"])
        headroom = float(row["headroom_change"])
        total = float(row["total_change"])
        baseline = top + plot_h
        tuition_top = scale(tuition, y_min, y_max, baseline, top)
        total_top = scale(total, y_min, y_max, baseline, top)
        x = center - bar_width / 2
        lines.append(
            f'<rect x="{x:.1f}" y="{tuition_top:.1f}" width="{bar_width}" height="{baseline-tuition_top:.1f}" fill="{TUITION_COLOR}"/>'
        )
        lines.append(
            f'<rect x="{x:.1f}" y="{total_top:.1f}" width="{bar_width}" height="{tuition_top-total_top:.1f}" fill="{HEADROOM_COLOR}"/>'
        )
        tuition_mid = (tuition_top + baseline) / 2
        headroom_mid = (total_top + tuition_top) / 2
        lines.append(
            f'<text x="{center:.1f}" y="{tuition_mid+5:.1f}" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="white">{signed_dollar(tuition)}</text>'
        )
        lines.append(
            f'<text x="{center:.1f}" y="{headroom_mid+5:.1f}" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="white">{signed_dollar(headroom)}</text>'
        )
        lines.append(
            f'<text x="{center:.1f}" y="{total_top-14:.1f}" text-anchor="middle" font-family="Arial" font-size="15" font-weight="700" fill="{TEXT_COLOR}">{signed_dollar(total)} total</text>'
        )
        lines.append(
            f'<text x="{center:.1f}" y="{baseline+33:.1f}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700" fill="{TEXT_COLOR}">{svg_text(row["sector_label"])}</text>'
        )
        lines.append(
            f'<text x="{center:.1f}" y="{baseline+54:.1f}" text-anchor="middle" font-family="Arial" font-size="11" fill="{MUTED_COLOR}">Paired institutions: {int(row["paired_institutions"]):,}</text>'
        )

    lines.append(f'<line x1="{left}" x2="{width-right}" y1="{top+plot_h}" y2="{top+plot_h}" stroke="{TEXT_COLOR}"/>')
    lines.append(
        f'<text x="28" y="{top+plot_h/2:.1f}" transform="rotate(-90 28 {top+plot_h/2:.1f})" font-family="Arial" font-size="12" text-anchor="middle" fill="{TEXT_COLOR}">Mean change in nominal dollars</text>'
    )
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_interval_svg(
    path: Path,
    data: pd.DataFrame,
    title: str,
    subtitle: str,
    x_label: str = "Dollars per $1,000 of headroom",
) -> None:
    labels = list(dict.fromkeys(data["label"].astype(str).tolist()))
    groups = [group for group in ["Public", "Private nonprofit"] if group in set(data["group"])]
    width = 1080
    left, right, top, bottom = 340, 175, 118, 88
    row_h = 76
    height = top + bottom + max(1, len(labels)) * row_h
    plot_right = width - right
    x_low, x_high = value_range(pd.concat([data["ci_low_dollars"], data["ci_high_dollars"]]), include_zero=True, pad_share=0.12)
    axis_y = height - bottom

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{svg_text(title)}</title>",
        f"<desc>{svg_text(subtitle)}</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="32" y="38" font-family="Arial" font-size="21" font-weight="700" fill="{TEXT_COLOR}">{svg_text(title)}</text>',
        f'<text x="32" y="64" font-family="Arial" font-size="13" fill="{MUTED_COLOR}">{svg_text(subtitle)}</text>',
    ]
    legend_x = left
    for idx, group in enumerate(groups):
        color = SECTOR_COLORS[group]
        x = legend_x + idx * 175
        if group == "Public":
            lines.append(f'<rect x="{x}" y="82" width="12" height="12" fill="white" stroke="{color}" stroke-width="2"/>')
        else:
            lines.append(f'<circle cx="{x+6}" cy="88" r="6" fill="{color}"/>')
        lines.append(f'<text x="{x+20}" y="93" font-family="Arial" font-size="12" fill="{TEXT_COLOR}">{svg_text(group)}</text>')

    zero_x = scale(0.0, x_low, x_high, left, plot_right)
    lines.append(f'<line x1="{zero_x:.1f}" x2="{zero_x:.1f}" y1="{top-14}" y2="{axis_y}" stroke="#777" stroke-dasharray="4 4"/>')
    lines.append(f'<line x1="{left}" x2="{plot_right}" y1="{axis_y}" y2="{axis_y}" stroke="{TEXT_COLOR}"/>')
    for tick in range(5):
        value = x_low + (x_high - x_low) * tick / 4
        x = scale(value, x_low, x_high, left, plot_right)
        tick_anchor = "start" if tick == 0 else "end" if tick == 4 else "middle"
        lines.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{axis_y}" y2="{axis_y+6}" stroke="{TEXT_COLOR}"/>')
        lines.append(
            f'<text x="{x:.1f}" y="{axis_y+25}" text-anchor="{tick_anchor}" font-family="Arial" font-size="11" fill="{MUTED_COLOR}">{signed_dollar(value)}</text>'
        )
    lines.append(
        f'<text x="{left+(plot_right-left)/2:.1f}" y="{height-22}" text-anchor="middle" font-family="Arial" font-size="12" fill="{TEXT_COLOR}">{svg_text(x_label)}</text>'
    )

    offsets = {"Public": -10, "Private nonprofit": 10}
    for label_idx, label in enumerate(labels):
        center_y = top + label_idx * row_h + row_h / 2
        lines.append(f'<line x1="{left}" x2="{plot_right}" y1="{center_y+row_h/2:.1f}" y2="{center_y+row_h/2:.1f}" stroke="#f1f2f3"/>')
        lines.append(
            f'<text x="32" y="{center_y+5:.1f}" font-family="Arial" font-size="13" fill="{TEXT_COLOR}">{svg_text(label)}</text>'
        )
        subset = data[data["label"].eq(label)]
        for group in groups:
            match = subset[subset["group"].eq(group)]
            if match.empty:
                continue
            row = match.iloc[0]
            y = center_y + offsets[group]
            color = SECTOR_COLORS[group]
            low_x = scale(float(row["ci_low_dollars"]), x_low, x_high, left, plot_right)
            high_x = scale(float(row["ci_high_dollars"]), x_low, x_high, left, plot_right)
            est_x = scale(float(row["estimate_dollars"]), x_low, x_high, left, plot_right)
            lines.append(f'<line x1="{low_x:.1f}" x2="{high_x:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="2.4"/>')
            lines.append(f'<line x1="{low_x:.1f}" x2="{low_x:.1f}" y1="{y-4:.1f}" y2="{y+4:.1f}" stroke="{color}" stroke-width="1.5"/>')
            lines.append(f'<line x1="{high_x:.1f}" x2="{high_x:.1f}" y1="{y-4:.1f}" y2="{y+4:.1f}" stroke="{color}" stroke-width="1.5"/>')
            if group == "Public":
                lines.append(f'<rect x="{est_x-5:.1f}" y="{y-5:.1f}" width="10" height="10" fill="white" stroke="{color}" stroke-width="2"/>')
            else:
                lines.append(f'<circle cx="{est_x:.1f}" cy="{y:.1f}" r="5.5" fill="{color}"/>')
            lines.append(
                f'<text x="{plot_right-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11" font-weight="700" fill="{color}">{signed_dollar(float(row["estimate_dollars"]))}</text>'
            )

    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def sample_count_figure(analysis_dir: Path, output_dir: Path) -> dict[str, Path]:
    source = analysis_dir / "analysis_institution_years_by_sector_year.csv"
    data = pd.read_csv(source)
    require_columns(data, {"year", "sector", "institution_years"}, source)
    data = data[data["sector"].isin(["public", "private_nonprofit"])].copy()
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
    require_columns(data, {"scope", "measure_id", "sector", "year", "ftft_weighted_mean"}, source)
    data = data[
        data["scope"].eq("public_private_nonprofit")
        & data["measure_id"].eq("main_dollars")
        & data["sector"].isin(["public", "private_nonprofit"])
    ].copy()
    csv_path = output_dir / "figure_headroom_trends_by_sector.csv"
    svg_path = output_dir / "figure_headroom_trends_by_sector.svg"
    data.to_csv(csv_path, index=False)
    write_line_svg(
        svg_path,
        data,
        "COA headroom by sector",
        "FTFT-weighted mean of the published non-tuition COA headroom measure.",
        "year",
        "ftft_weighted_mean",
        "sector",
        "Nominal dollars",
    )
    return {"headroom_trends_csv": csv_path, "headroom_trends_svg": svg_path}


def coa_change_decomposition_figure(decomposition_dir: Path, output_dir: Path) -> dict[str, Path]:
    source = decomposition_dir / "coa_full_window_component_changes.csv"
    data = pd.read_csv(source)
    require_columns(
        data,
        {
            "scope",
            "sector",
            "from_year",
            "to_year",
            "paired_institutions",
            "mean_coa_main_change",
            "mean_headroom_main_change",
            "mean_tuition_fees_change",
        },
        source,
    )
    data = data[
        data["scope"].eq("public_private_nonprofit") & data["sector"].isin(["public", "private_nonprofit"])
    ].copy()
    sector_counts = data["sector"].value_counts().to_dict()
    if sector_counts != {"public": 1, "private_nonprofit": 1}:
        raise ValueError(
            f"{source} must contain exactly one public row and one private_nonprofit row for the combined scope"
        )
    if len(data[["from_year", "to_year"]].drop_duplicates()) != 1:
        raise ValueError(f"{source} must use one common comparison period across sectors")
    data["sector_order"] = data["sector"].map({"public": 0, "private_nonprofit": 1})
    data = data.sort_values("sector_order")
    chart = pd.DataFrame(
        {
            "sector": data["sector"],
            "sector_label": data["sector"].map(SECTOR_LABELS),
            "from_year": data["from_year"].astype(int),
            "to_year": data["to_year"].astype(int),
            "paired_institutions": data["paired_institutions"].astype(int),
            "tuition_change": data["mean_tuition_fees_change"].astype(float),
            "headroom_change": data["mean_headroom_main_change"].astype(float),
            "total_change": data["mean_coa_main_change"].astype(float),
        }
    )
    closure_error = (chart["tuition_change"] + chart["headroom_change"] - chart["total_change"]).abs()
    if (closure_error > 0.01).any():
        raise ValueError(f"{source} does not close: tuition change plus headroom change must equal COA change")
    csv_path = output_dir / "figure_coa_change_decomposition.csv"
    svg_path = output_dir / "figure_coa_change_decomposition.svg"
    chart.to_csv(csv_path, index=False)
    write_decomposition_svg(svg_path, chart)
    return {"coa_decomposition_csv": csv_path, "coa_decomposition_svg": svg_path}


def sector_estimate_stability_figure(manuscript_dir: Path, output_dir: Path) -> dict[str, Path]:
    source = manuscript_dir / "sector_robustness_for_manuscript.csv"
    data = pd.read_csv(source)
    required = {"check"}
    for prefix in ("public", "private_nonprofit"):
        required.update({f"{prefix}_estimate", f"{prefix}_std_error", f"{prefix}_nobs", f"{prefix}_institutions"})
    require_columns(data, required, source)
    data = data[data["check"].isin(ROBUSTNESS_ORDER)].copy()
    check_counts = data["check"].value_counts().to_dict()
    if set(check_counts) != set(ROBUSTNESS_ORDER) or any(count != 1 for count in check_counts.values()):
        raise ValueError(f"{source} must contain exactly one row for each required main-text check")
    order = {label: idx for idx, label in enumerate(ROBUSTNESS_ORDER)}
    data["order"] = data["check"].map(order)
    rows: list[dict[str, object]] = []
    for row in data.sort_values("order").to_dict("records"):
        for prefix, group in (("public", "Public"), ("private_nonprofit", "Private nonprofit")):
            estimate = float(row[f"{prefix}_estimate"])
            std_error = float(row[f"{prefix}_std_error"])
            rows.append(
                {
                    "label": row["check"],
                    "group": group,
                    "estimate": estimate,
                    "std_error": std_error,
                    "ci_low": estimate - 1.96 * std_error,
                    "ci_high": estimate + 1.96 * std_error,
                    "estimate_dollars": estimate * 1000,
                    "ci_low_dollars": (estimate - 1.96 * std_error) * 1000,
                    "ci_high_dollars": (estimate + 1.96 * std_error) * 1000,
                    "institution_years": int(row[f"{prefix}_nobs"]),
                    "institutions": int(row[f"{prefix}_institutions"]),
                }
            )
    chart = pd.DataFrame(rows)
    csv_path = output_dir / "figure_main_estimate_forest.csv"
    svg_path = output_dir / "figure_main_estimate_forest.svg"
    chart.to_csv(csv_path, index=False)
    write_interval_svg(
        svg_path,
        chart,
        "Sector-specific institutional-grant estimates",
        "Coefficient and 95% confidence interval; dollars per FTFT aid-cohort student per $1,000 of headroom",
    )
    return {"main_estimate_forest_csv": csv_path, "main_estimate_forest_svg": svg_path}


def aid_outcome_figure(manuscript_dir: Path, output_dir: Path) -> dict[str, Path]:
    source = manuscript_dir / "sector_aid_outcomes_for_manuscript.csv"
    data = pd.read_csv(source)
    required = {"outcome"}
    for prefix in ("public", "private_nonprofit"):
        required.update({f"{prefix}_estimate", f"{prefix}_std_error", f"{prefix}_nobs", f"{prefix}_institutions"})
    require_columns(data, required, source)
    data = data[data["outcome"].isin(AID_OUTCOME_ORDER)].copy()
    outcome_counts = data["outcome"].value_counts().to_dict()
    if set(outcome_counts) != set(AID_OUTCOME_ORDER) or any(count != 1 for count in outcome_counts.values()):
        raise ValueError(f"{source} must contain exactly one row for each required aid outcome")
    order = {label: idx for idx, label in enumerate(AID_OUTCOME_ORDER)}
    data["order"] = data["outcome"].map(order)
    rows: list[dict[str, object]] = []
    for row in data.sort_values("order").to_dict("records"):
        for prefix, group in (("public", "Public"), ("private_nonprofit", "Private nonprofit")):
            estimate = float(row[f"{prefix}_estimate"])
            std_error = float(row[f"{prefix}_std_error"])
            rows.append(
                {
                    "label": row["outcome"],
                    "group": group,
                    "estimate": estimate,
                    "std_error": std_error,
                    "ci_low": estimate - 1.96 * std_error,
                    "ci_high": estimate + 1.96 * std_error,
                    "estimate_dollars": estimate * 1000,
                    "ci_low_dollars": (estimate - 1.96 * std_error) * 1000,
                    "ci_high_dollars": (estimate + 1.96 * std_error) * 1000,
                    "institution_years": int(row[f"{prefix}_nobs"]),
                    "institutions": int(row[f"{prefix}_institutions"]),
                }
            )
    chart = pd.DataFrame(rows)
    csv_path = output_dir / "figure_aid_outcome_dollars.csv"
    svg_path = output_dir / "figure_aid_outcome_dollars.svg"
    chart.to_csv(csv_path, index=False)
    write_interval_svg(
        svg_path,
        chart,
        "Aid-dollar outcomes by sector",
        "Coefficient and 95% confidence interval; dollars per FTFT aid-cohort student per $1,000 of headroom",
    )
    return {"aid_outcomes_csv": csv_path, "aid_outcomes_svg": svg_path}


def component_check_figure(fixed_effects_dir: Path, output_dir: Path) -> dict[str, Path]:
    source = fixed_effects_dir / "fixed_effects_coefficients.csv"
    data = pd.read_csv(source)
    require_columns(data, {"model_id", "term", "estimate", "std_error", "nobs", "clusters"}, source)
    data = data[data["model_id"].isin(COMPONENT_MODELS) & data["term"].isin(COMPONENT_TERMS)].copy()
    expected_keys = {(model_id, term) for model_id in COMPONENT_MODELS for term in COMPONENT_TERMS}
    observed_keys = set(zip(data["model_id"], data["term"], strict=False))
    if observed_keys != expected_keys or data.duplicated(["model_id", "term"]).any():
        raise ValueError(f"{source} must contain exactly one coefficient for every sector and COA component")
    data["label"] = data["term"].map(COMPONENT_TERMS)
    data["group"] = data["model_id"].map(COMPONENT_MODELS)
    order = {label: idx for idx, label in enumerate(COMPONENT_ORDER)}
    data["order"] = data["label"].map(order)
    data = data.sort_values(["order", "group"])
    data["ci_low"] = data["estimate"] - 1.96 * data["std_error"]
    data["ci_high"] = data["estimate"] + 1.96 * data["std_error"]
    data["estimate_dollars"] = data["estimate"] * 1000
    data["ci_low_dollars"] = data["ci_low"] * 1000
    data["ci_high_dollars"] = data["ci_high"] * 1000
    chart = data[
        [
            "label",
            "group",
            "estimate",
            "std_error",
            "ci_low",
            "ci_high",
            "estimate_dollars",
            "ci_low_dollars",
            "ci_high_dollars",
            "nobs",
            "clusters",
        ]
    ].rename(columns={"nobs": "institution_years", "clusters": "institutions"})
    csv_path = output_dir / "figure_component_checks.csv"
    svg_path = output_dir / "figure_component_checks.svg"
    chart.to_csv(csv_path, index=False)
    write_interval_svg(
        svg_path,
        chart,
        "Cost-of-attendance component checks",
        "Joint component model; institutional-grant dollars per FTFT aid-cohort student per $1,000 of each component",
        x_label="Institutional-grant dollars per $1,000 of each COA component",
    )
    return {"component_checks_csv": csv_path, "component_checks_svg": svg_path}


def build_report_figures(
    analysis_dir: Path = DEFAULT_ANALYSIS_DIR,
    headroom_dir: Path = DEFAULT_HEADROOM_DIR,
    fixed_effects_dir: Path = DEFAULT_FIXED_EFFECTS_DIR,
    decomposition_dir: Path = DEFAULT_DECOMPOSITION_DIR,
    manuscript_dir: Path = DEFAULT_MANUSCRIPT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    # Sample counts and raw trends remain available for appendix and diagnostic use.
    paths.update(sample_count_figure(analysis_dir, output_dir))
    paths.update(headroom_trend_figure(headroom_dir, output_dir))
    # Main-facing exhibits answer decomposition, sector contrast, and aid-package questions.
    paths.update(coa_change_decomposition_figure(decomposition_dir, output_dir))
    paths.update(sector_estimate_stability_figure(manuscript_dir, output_dir))
    paths.update(aid_outcome_figure(manuscript_dir, output_dir))
    # The joint component model is retained as an appendix or presentation-backup exhibit.
    paths.update(component_check_figure(fixed_effects_dir, output_dir))
    summary_path = output_dir / "figures_summary.json"
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_dir": str(analysis_dir),
        "headroom_dir": str(headroom_dir),
        "fixed_effects_dir": str(fixed_effects_dir),
        "decomposition_dir": str(decomposition_dir),
        "manuscript_dir": str(manuscript_dir),
        "outputs": {key: str(value) for key, value in paths.items()},
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    paths["summary"] = summary_path
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Build paper-ready SVG figures and their auditable source-data CSVs.")
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    parser.add_argument("--headroom-dir", type=Path, default=DEFAULT_HEADROOM_DIR)
    parser.add_argument("--fixed-effects-dir", type=Path, default=DEFAULT_FIXED_EFFECTS_DIR)
    parser.add_argument("--decomposition-dir", type=Path, default=DEFAULT_DECOMPOSITION_DIR)
    parser.add_argument("--model-sample-dir", type=Path, default=DEFAULT_MODEL_SAMPLE_DIR)
    parser.add_argument("--fmr-comparison", type=Path, default=DEFAULT_FMR_COMPARISON)
    parser.add_argument("--manuscript-dir", type=Path, default=DEFAULT_MANUSCRIPT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--use-existing-exhibit-data",
        action="store_true",
        help="Do not refresh the sector-specific audit CSVs before drawing figures.",
    )
    args = parser.parse_args()
    if not args.use_existing_exhibit_data:
        build_manuscript_exhibit_data(
            analysis_root=args.analysis_root,
            model_sample_dir=args.model_sample_dir,
            fmr_comparison=args.fmr_comparison,
            output_dir=args.manuscript_dir,
        )
    paths = build_report_figures(
        analysis_dir=args.analysis_dir,
        headroom_dir=args.headroom_dir,
        fixed_effects_dir=args.fixed_effects_dir,
        decomposition_dir=args.decomposition_dir,
        manuscript_dir=args.manuscript_dir,
        output_dir=args.output_dir,
    )
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
