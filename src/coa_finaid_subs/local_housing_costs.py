from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


HUD_FMR_2BR_URL = "https://www.huduser.gov/portal/datasets/FMR/FMR_2Bed_1983_2026.csv"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = Path("data/external/hud_fmr")
DEFAULT_OUTPUT_DIR = Path("outputs/local_housing_controls")
DEFAULT_ANALYSIS_PANEL = (
    Path("outputs")
    / "analysis_panel"
    / "public_private_nonprofit"
    / "analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet"
)
DEFAULT_RAW_FMR = DEFAULT_RAW_DIR / "FMR_2Bed_1983_2026.csv"
DEFAULT_MIN_MATCH_RATE = 0.99
DEFAULT_MIN_YEAR_SECTOR_MATCH_RATE = 0.95


def public_path_label(path: Path | str) -> str:
    """Return a shareable path label without embedding personal absolute paths."""
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate)
    try:
        return str(candidate.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return candidate.name


STATE_FIPS_TO_ABBR = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "60": "AS",
    "66": "GU",
    "69": "MP",
    "72": "PR",
    "78": "VI",
}
STATE_ABBR_TO_FIPS = {abbr: fips for fips, abbr in STATE_FIPS_TO_ABBR.items()}
STATE_NAME_TO_ABBR = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
    "AMERICAN SAMOA": "AS",
    "GUAM": "GU",
    "NORTHERN MARIANA ISLANDS": "MP",
    "PUERTO RICO": "PR",
    "VIRGIN ISLANDS": "VI",
}


def canonical_column(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


def first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    canon_to_original = {canonical_column(col): col for col in columns}
    for candidate in candidates:
        match = canon_to_original.get(canonical_column(candidate))
        if match is not None:
            return match
    return None


def normalize_county_name(value: object) -> str:
    raw = "" if pd.isna(value) else str(value).strip()
    state_suffixes = "|".join(sorted(STATE_ABBR_TO_FIPS))
    raw = re.sub(rf",\s*(?:{state_suffixes})\s*$", "", raw, flags=re.IGNORECASE)
    text = raw.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(
        r"\b(county|parish|borough|municipio|municipality|census area|city and borough|city)\b",
        " ",
        text,
    )
    text = re.sub(r"\bst\b", "saint", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_state_abbr(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if text.isdigit():
        return STATE_FIPS_TO_ABBR.get(text.zfill(2), "")
    if len(text) == 2:
        return text
    if text in STATE_NAME_TO_ABBR:
        return STATE_NAME_TO_ABBR[text]
    return ""


def clean_state_fips(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if text.isdigit():
        return text.zfill(2)[-2:]
    return STATE_ABBR_TO_FIPS.get(text.upper(), "")


def clean_county_fips(value: object, state: object | None = None) -> str:
    if pd.isna(value):
        return ""
    text = re.sub(r"\D", "", str(value))
    if len(text) in {9, 10}:
        # HUD annual files use a 10-digit code: state + county + county subdivision.
        # The first five digits identify the county; leading zeroes are often lost
        # when Excel stores the code as a number.
        return text.zfill(10)[:5]
    if len(text) == 5:
        return text
    if len(text) in {1, 2, 3} and state is not None:
        state_fips = clean_state_fips(state)
        if state_fips:
            return f"{state_fips}{text.zfill(3)}"
    return ""


def detect_year_columns(columns: Iterable[str]) -> dict[str, int]:
    matches: dict[str, int] = {}
    for col in columns:
        canon = canonical_column(col)
        year_match = re.fullmatch(r"(?:x|fmr|fmr2|fmr2br|fmr2bed|twobed)?(19[8-9][0-9]|20[0-9][0-9])", canon)
        if year_match:
            matches[col] = int(year_match.group(1))
    return matches


def metadata_columns(frame: pd.DataFrame) -> dict[str, str | None]:
    columns = list(frame.columns)
    return {
        "state": first_existing(columns, ["state", "st", "stusps", "state_alpha", "state_abbr"]),
        "state_fips": first_existing(columns, ["state_fips", "statefips", "state_code", "stfips"]),
        "county_name": first_existing(columns, ["county_name", "countyname", "countynm", "cntyname", "county"]),
        "county_fips": first_existing(columns, ["county_fips", "countyfips", "fips", "fips2010", "fips2000", "cnty", "fipscode"]),
        "area_code": first_existing(columns, ["fmr_area_code", "fmrarea", "hud_area_code", "metro_code", "cbsa", "msa"]),
        "area_name": first_existing(columns, ["fmr_area_name", "area_name", "areaname", "hud_area_name", "metro_name"]),
    }


def long_form_fmr(frame: pd.DataFrame) -> pd.DataFrame | None:
    year_col = first_existing(frame.columns, ["year", "yr", "fiscal_year", "fiscalyear"])
    fmr_col = first_existing(
        frame.columns,
        [
            "hud_fmr_2br",
            "fmr_2br",
            "fmr2br",
            "fmr2",
            "fmr_2",
            "two_bedroom",
            "twobedroom",
            "2br",
            "fmr",
        ],
    )
    if year_col is None or fmr_col is None:
        return None
    meta = metadata_columns(frame)
    keep = list(dict.fromkeys(col for col in meta.values() if col is not None))
    out = frame[[*keep, year_col, fmr_col]].copy()
    out = out.rename(columns={year_col: "year", fmr_col: "hud_fmr_2br"})
    return attach_metadata(out, meta)


def wide_form_fmr(frame: pd.DataFrame) -> pd.DataFrame | None:
    year_cols = detect_year_columns(frame.columns)
    if not year_cols:
        return None
    meta = metadata_columns(frame)
    keep = list(dict.fromkeys(col for col in meta.values() if col is not None))
    out = frame[[*keep, *year_cols.keys()]].melt(
        id_vars=keep,
        value_vars=list(year_cols.keys()),
        var_name="year_source",
        value_name="hud_fmr_2br",
    )
    out["year"] = out["year_source"].map(year_cols)
    out = out.drop(columns=["year_source"])
    return attach_metadata(out, meta)


def fmr_year_from_filename(path: Path) -> int | None:
    fy_match = re.search(r"FY[_-]?(20\d{2}|\d{2})", path.stem, flags=re.IGNORECASE)
    if fy_match:
        token = fy_match.group(1)
        return int(token) if len(token) == 4 else 2000 + int(token)
    year_match = re.search(r"(20\d{2})", path.stem)
    if year_match:
        return int(year_match.group(1))
    return None


def excel_engine_for(path: Path) -> str | None:
    if path.suffix.lower() in {".xls", ".xlsx"}:
        return "calamine"
    return None


def read_fmr_workbook(path: Path) -> pd.DataFrame:
    engine = excel_engine_for(path)
    try:
        workbook = pd.ExcelFile(path, engine=engine)
        sheet_name = next(
            (sheet for sheet in workbook.sheet_names if "field" not in sheet.lower() and "description" not in sheet.lower()),
            workbook.sheet_names[0],
        )
        return pd.read_excel(path, sheet_name=sheet_name, engine=engine).dropna(how="all")
    except ImportError as exc:
        raise RuntimeError(
            "Reading annual HUD Excel files requires python-calamine. Install dependencies with `pip install -r requirements.txt`."
        ) from exc


def annual_workbook_paths(raw_dir: Path, start_year: int, end_year: int) -> list[tuple[Path, int]]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"HUD FMR directory not found: {raw_dir}")
    candidates: list[tuple[Path, int]] = []
    for path in sorted(raw_dir.iterdir()):
        if path.suffix.lower() not in {".xls", ".xlsx"}:
            continue
        year = fmr_year_from_filename(path)
        if year is not None and start_year <= year <= end_year:
            candidates.append((path, year))
    if not candidates:
        raise FileNotFoundError(f"No HUD annual FMR Excel files for {start_year}-{end_year} found in {raw_dir}")

    expected_years = set(range(start_year, end_year + 1))
    found_years = [year for _, year in candidates]
    missing_years = sorted(expected_years - set(found_years))
    if missing_years:
        raise ValueError(f"Missing HUD annual FMR files for years: {missing_years}")
    duplicate_years = sorted({year for year in found_years if found_years.count(year) > 1})
    if duplicate_years:
        files = {year: [public_path_label(path) for path, file_year in candidates if file_year == year] for year in duplicate_years}
        raise ValueError(f"Multiple HUD annual FMR files found for the same year: {files}")
    return candidates


def write_normalized_hud_fmr(
    normalized: pd.DataFrame,
    output_dir: Path,
    start_year: int,
    end_year: int,
    source_label: str,
    source_files: list[dict[str, object]] | None = None,
) -> dict[str, Path]:
    normalized = normalized[
        normalized["year"].between(start_year, end_year)
        & normalized["hud_fmr_2br"].notna()
        & normalized["state"].ne("")
    ].copy()
    output_dir.mkdir(parents=True, exist_ok=True)
    panel_path = output_dir / f"hud_fmr_2br_{start_year}_{end_year}.csv"
    summary_path = output_dir / "hud_fmr_summary.json"
    duplicate_keys = normalized.duplicated(["year", "state", "county_name_norm"], keep=False)
    duplicate_path = output_dir / f"hud_fmr_duplicate_county_year_rows_{start_year}_{end_year}.csv"
    normalized.loc[duplicate_keys].sort_values(["state", "county_name_norm", "year"]).to_csv(duplicate_path, index=False)
    normalized.to_csv(panel_path, index=False)

    outputs: dict[str, str] = {
        "panel": public_path_label(panel_path),
        "duplicates": public_path_label(duplicate_path),
    }
    result: dict[str, Path] = {"panel": panel_path, "duplicates": duplicate_path, "summary": summary_path}
    if source_files is not None:
        source_path = output_dir / f"hud_fmr_source_files_{start_year}_{end_year}.csv"
        pd.DataFrame(source_files).to_csv(source_path, index=False)
        outputs["source_files"] = public_path_label(source_path)
        result["source_files"] = source_path

    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": HUD_FMR_2BR_URL,
        "source_label": source_label,
        "year_min": int(normalized["year"].min()) if not normalized.empty else None,
        "year_max": int(normalized["year"].max()) if not normalized.empty else None,
        "rows": int(len(normalized)),
        "states": int(normalized["state"].nunique(dropna=True)),
        "county_year_keys": int(normalized[["year", "state", "county_name_norm"]].drop_duplicates().shape[0]),
        "duplicate_county_year_rows": int(duplicate_keys.sum()),
        "outputs": outputs,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return result


def normalize_hud_fmr_directory(raw_dir: Path, output_dir: Path, start_year: int = 2009, end_year: int = 2023) -> dict[str, Path]:
    frames: list[pd.DataFrame] = []
    source_rows: list[dict[str, object]] = []
    for workbook_path, year in annual_workbook_paths(raw_dir, start_year, end_year):
        raw = read_fmr_workbook(workbook_path)
        raw["year"] = year
        normalized = long_form_fmr(raw)
        if normalized is None:
            raise ValueError(f"Could not identify year/FMR columns in {workbook_path}")
        normalized["hud_fmr_source"] = workbook_path.name
        frames.append(normalized)
        source_rows.append({"year": year, "source_file": public_path_label(workbook_path), "raw_rows": int(len(raw)), "normalized_rows": int(len(normalized))})

    all_years = pd.concat(frames, ignore_index=True)
    return write_normalized_hud_fmr(
        all_years,
        output_dir,
        start_year,
        end_year,
        source_label=public_path_label(raw_dir),
        source_files=source_rows,
    )


def attach_metadata(frame: pd.DataFrame, meta: dict[str, str | None]) -> pd.DataFrame:
    out = frame.copy()
    rename = {source: target for target, source in meta.items() if source is not None and source in out.columns}
    out = out.rename(columns=rename)
    for col in ["state", "state_fips", "county_name", "county_fips", "area_code", "area_name"]:
        if col not in out.columns:
            out[col] = ""

    out["state"] = out["state"].map(clean_state_abbr)
    state_from_fips = out["state_fips"].map(lambda value: STATE_FIPS_TO_ABBR.get(clean_state_fips(value), ""))
    out["state"] = out["state"].where(out["state"].ne(""), state_from_fips)
    out["state_fips"] = out.apply(
        lambda row: clean_state_fips(row["state_fips"]) or STATE_ABBR_TO_FIPS.get(str(row["state"]).upper(), ""),
        axis=1,
    )
    out["county_fips"] = out.apply(lambda row: clean_county_fips(row["county_fips"], row["state"]), axis=1)
    out["county_name_norm"] = out["county_name"].map(normalize_county_name)
    out["hud_fmr_2br"] = pd.to_numeric(out["hud_fmr_2br"], errors="coerce")
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    return out[
        [
            "year",
            "state",
            "state_fips",
            "county_name",
            "county_name_norm",
            "county_fips",
            "area_code",
            "area_name",
            "hud_fmr_2br",
        ]
    ].copy()


def normalize_hud_fmr(raw_csv: Path, output_dir: Path, start_year: int = 2009, end_year: int = 2023) -> dict[str, Path]:
    if not raw_csv.exists():
        raise FileNotFoundError(
            f"HUD FMR file not found: {raw_csv}. Download it from {HUD_FMR_2BR_URL} or run scripts/download_hud_fmr.py."
        )
    raw = pd.read_csv(raw_csv)
    normalized = long_form_fmr(raw)
    if normalized is None:
        normalized = wide_form_fmr(raw)
    if normalized is None:
        raise ValueError(
            "Could not identify HUD FMR year/value columns. Expected either long columns like year and fmr_2br, "
            "or wide year columns such as 2009, fmr2009, or fmr2br2009."
        )

    normalized["hud_fmr_source"] = raw_csv.name
    return write_normalized_hud_fmr(
        normalized,
        output_dir,
        start_year,
        end_year,
        source_label=public_path_label(raw_csv),
        source_files=[{"year": "wide_or_long", "source_file": public_path_label(raw_csv), "raw_rows": int(len(raw)), "normalized_rows": int(len(normalized))}],
    )


def county_year_fmr(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        frame.groupby(["year", "state", "county_name_norm"], as_index=False)
        .agg(
            hud_fmr_2br=("hud_fmr_2br", "mean"),
            hud_fmr_county_matches=("hud_fmr_2br", "size"),
            hud_fmr_area_name=("area_name", lambda values: "; ".join(sorted({str(v) for v in values if str(v) and str(v) != "nan"}))[:500]),
            hud_fmr_county_fips=("county_fips", lambda values: ";".join(sorted({str(v) for v in values if str(v)}))),
        )
        .copy()
    )
    grouped["ln_hud_fmr_2br"] = np.log(grouped["hud_fmr_2br"].where(grouped["hud_fmr_2br"].gt(0)))
    return grouped


def build_local_housing_controls(
    analysis_panel: Path = DEFAULT_ANALYSIS_PANEL,
    fmr_panel: Path = DEFAULT_OUTPUT_DIR / "hud_fmr_2br_2009_2023.csv",
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    scope: str = "public_private_nonprofit",
    min_match_rate: float = DEFAULT_MIN_MATCH_RATE,
    min_year_sector_match_rate: float = DEFAULT_MIN_YEAR_SECTOR_MATCH_RATE,
) -> dict[str, Path]:
    if not analysis_panel.exists():
        raise FileNotFoundError(f"Analysis panel not found: {analysis_panel}")
    if not fmr_panel.exists():
        raise FileNotFoundError(f"Normalized HUD FMR panel not found: {fmr_panel}")

    panel = pd.read_parquet(analysis_panel)
    required = {"UNITID", "year", "STABBR", "COUNTYNM"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Analysis panel is missing required merge columns: {', '.join(sorted(missing))}")

    fmr = pd.read_csv(fmr_panel)
    county_fmr = county_year_fmr(fmr)
    merge_frame = panel[["UNITID", "year", "STABBR", "COUNTYNM", "SECTOR"]].copy()
    merge_frame["state"] = merge_frame["STABBR"].map(clean_state_abbr)
    merge_frame["county_name_norm"] = merge_frame["COUNTYNM"].map(normalize_county_name)
    merged = merge_frame.merge(county_fmr, on=["year", "state", "county_name_norm"], how="left")

    controls = merged[
        [
            "UNITID",
            "year",
            "STABBR",
            "COUNTYNM",
            "SECTOR",
            "hud_fmr_2br",
            "ln_hud_fmr_2br",
            "hud_fmr_county_matches",
            "hud_fmr_area_name",
            "hud_fmr_county_fips",
        ]
    ].copy()
    controls["hud_fmr_match_status"] = np.select(
        [
            controls["hud_fmr_2br"].isna(),
            controls["hud_fmr_county_matches"].gt(1),
        ],
        ["unmatched", "multi_match"],
        default="single_match",
    )
    augmented = panel.merge(
        controls[
            [
                "UNITID",
                "year",
                "hud_fmr_2br",
                "ln_hud_fmr_2br",
                "hud_fmr_county_matches",
                "hud_fmr_area_name",
                "hud_fmr_county_fips",
                "hud_fmr_match_status",
            ]
        ],
        on=["UNITID", "year"],
        how="left",
        validate="one_to_one",
    )

    audit = (
        controls.assign(matched=controls["hud_fmr_2br"].notna())
        .groupby(["year", "SECTOR"], dropna=False)
        .agg(
            rows=("UNITID", "size"),
            institutions=("UNITID", "nunique"),
            matched_rows=("matched", "sum"),
            mean_hud_fmr_2br=("hud_fmr_2br", "mean"),
            median_hud_fmr_2br=("hud_fmr_2br", "median"),
        )
        .reset_index()
    )
    audit["match_rate"] = audit["matched_rows"] / audit["rows"]
    unmatched = controls[controls["hud_fmr_2br"].isna()].copy()
    multi_match = controls[controls["hud_fmr_county_matches"].gt(1)].copy()
    overall_match_rate = float(controls["hud_fmr_2br"].notna().mean()) if len(controls) else 0.0
    min_observed_year_sector_match_rate = float(audit["match_rate"].min()) if len(audit) else 0.0
    low_match_cells = audit[audit["match_rate"].lt(min_year_sector_match_rate)].copy()
    validation_errors: list[str] = []
    if overall_match_rate < min_match_rate:
        validation_errors.append(f"overall match rate {overall_match_rate:.6f} is below required {min_match_rate:.6f}")
    if not low_match_cells.empty:
        validation_errors.append(
            "year-sector match rates below required "
            f"{min_year_sector_match_rate:.6f}: "
            + ", ".join(f"{int(row.year)}/sector {row.SECTOR}: {row.match_rate:.6f}" for row in low_match_cells.itertuples())
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    controls_path = output_dir / f"local_housing_controls_hud_fmr_2br_2009_2023_{scope}.parquet"
    augmented_path = output_dir / f"analysis_panel_with_hud_fmr_2br_2009_2023_{scope}.parquet"
    audit_path = output_dir / f"hud_fmr_merge_audit_{scope}.csv"
    unmatched_path = output_dir / f"hud_fmr_unmatched_rows_{scope}.csv"
    multi_match_path = output_dir / f"hud_fmr_multi_match_rows_{scope}.csv"
    summary_path = output_dir / f"hud_fmr_merge_summary_{scope}.json"
    controls.to_parquet(controls_path, index=False)
    augmented.to_parquet(augmented_path, index=False)
    audit.to_csv(audit_path, index=False)
    unmatched.to_csv(unmatched_path, index=False)
    multi_match.to_csv(multi_match_path, index=False)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "analysis_panel": public_path_label(analysis_panel),
        "fmr_panel": public_path_label(fmr_panel),
        "rows": int(len(controls)),
        "matched_rows": int(controls["hud_fmr_2br"].notna().sum()),
        "match_rate": overall_match_rate,
        "min_match_rate_required": min_match_rate,
        "min_year_sector_match_rate": min_observed_year_sector_match_rate,
        "min_year_sector_match_rate_required": min_year_sector_match_rate,
        "low_match_year_sector_cells": int(len(low_match_cells)),
        "unmatched_rows": int(controls["hud_fmr_2br"].isna().sum()),
        "multi_match_rows": int(len(multi_match)),
        "multi_match_share_of_matched": float(len(multi_match) / controls["hud_fmr_2br"].notna().sum()) if controls["hud_fmr_2br"].notna().sum() else None,
        "validation_status": "pass" if not validation_errors else "fail",
        "validation_errors": validation_errors,
        "outputs": {
            "controls": public_path_label(controls_path),
            "augmented_panel": public_path_label(augmented_path),
            "audit": public_path_label(audit_path),
            "unmatched": public_path_label(unmatched_path),
            "multi_match": public_path_label(multi_match_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if validation_errors:
        raise ValueError("HUD FMR merge validation failed: " + "; ".join(validation_errors))
    return {
        "controls": controls_path,
        "augmented_panel": augmented_path,
        "audit": audit_path,
        "unmatched": unmatched_path,
        "multi_match": multi_match_path,
        "summary": summary_path,
    }


def download_hud_fmr(output_path: Path = DEFAULT_RAW_FMR, url: str = HUD_FMR_2BR_URL, force: bool = False) -> Path:
    if output_path.exists() and not force:
        return output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "COA_FINAID_SUBS research replication script; contact: markjayson.com",
            "Accept": "text/csv,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status = getattr(response, "status", None)
            headers = dict(response.headers.items())
            content = response.read()
    except Exception as exc:  # pragma: no cover - network depends on HUD availability
        raise RuntimeError(f"Could not download HUD FMR file from {url}: {exc}") from exc

    if status == 202 or headers.get("x-amzn-waf-action", "").lower() == "challenge" or len(content) == 0:
        raise RuntimeError(
            "HUD returned an access challenge instead of the CSV. Download the file manually from "
            f"{url} and place it at {output_path}."
        )
    output_path.write_bytes(content)
    return output_path


def download_main() -> None:
    parser = argparse.ArgumentParser(description="Download HUD Fair Market Rent 2-bedroom historical CSV.")
    parser.add_argument("--url", default=HUD_FMR_2BR_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_RAW_FMR)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        path = download_hud_fmr(args.output, args.url, args.force)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(path)


def build_main() -> None:
    parser = argparse.ArgumentParser(description="Normalize HUD FMR data and merge local housing-cost controls to the analysis panel.")
    parser.add_argument("--raw-fmr", type=Path, default=DEFAULT_RAW_FMR)
    parser.add_argument("--raw-fmr-dir", type=Path, default=None)
    parser.add_argument("--analysis-panel", type=Path, default=DEFAULT_ANALYSIS_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--scope", default="public_private_nonprofit")
    parser.add_argument("--min-match-rate", type=float, default=DEFAULT_MIN_MATCH_RATE)
    parser.add_argument("--min-year-sector-match-rate", type=float, default=DEFAULT_MIN_YEAR_SECTOR_MATCH_RATE)
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--skip-merge", action="store_true")
    args = parser.parse_args()
    raw_fmr_dir = args.raw_fmr_dir or args.raw_fmr.parent
    if args.raw_fmr.exists():
        normalized = normalize_hud_fmr(args.raw_fmr, args.output_dir, args.start_year, args.end_year)
    else:
        normalized = normalize_hud_fmr_directory(raw_fmr_dir, args.output_dir, args.start_year, args.end_year)
    print(f"Normalized HUD FMR panel: {normalized['panel']}")
    if not args.skip_merge:
        merged = build_local_housing_controls(
            args.analysis_panel,
            normalized["panel"],
            args.output_dir,
            args.scope,
            min_match_rate=args.min_match_rate,
            min_year_sector_match_rate=args.min_year_sector_match_rate,
        )
        print(f"Local housing controls: {merged['controls']}")
