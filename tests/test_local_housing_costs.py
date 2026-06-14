from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from coa_finaid_subs.local_housing_costs import (
    build_local_housing_controls,
    clean_county_fips,
    clean_state_abbr,
    normalize_county_name,
    normalize_hud_fmr,
    normalize_hud_fmr_directory,
)


def test_normalize_county_and_state_values() -> None:
    assert normalize_county_name("St. Louis County") == "saint louis"
    assert normalize_county_name("Clark County") == "clark"
    assert normalize_county_name("Madison County, AL") == "madison"
    assert clean_state_abbr("Nevada") == "NV"
    assert clean_state_abbr("32") == "NV"
    assert clean_county_fips(100199999) == "01001"
    assert clean_county_fips("32003") == "32003"


def test_normalize_hud_fmr_accepts_wide_year_columns(tmp_path: Path) -> None:
    raw = tmp_path / "FMR_2Bed_1983_2026.csv"
    pd.DataFrame(
        {
            "state": ["Nevada", "NV"],
            "county_name": ["Clark County", "Washoe County"],
            "county_fips": [32003, 32031],
            "area_name": ["Las Vegas-Henderson-Paradise, NV", "Reno, NV"],
            "2009": [900, 850],
            "2010": [925, 875],
            "2023": [1650, 1500],
        }
    ).to_csv(raw, index=False)

    paths = normalize_hud_fmr(raw, tmp_path, start_year=2009, end_year=2023)
    normalized = pd.read_csv(paths["panel"])

    assert len(normalized) == 6
    assert set(normalized["state"]) == {"NV"}
    assert set(normalized["county_name_norm"]) == {"clark", "washoe"}
    assert normalized.loc[normalized["year"].eq(2023), "hud_fmr_2br"].sum() == 3150


def test_build_local_housing_controls_merges_by_state_county_year(tmp_path: Path) -> None:
    analysis_panel = tmp_path / "analysis.parquet"
    pd.DataFrame(
        {
            "UNITID": [1, 1, 2, 3],
            "year": [2009, 2010, 2009, 2009],
            "STABBR": ["NV", "NV", "NV", "CA"],
            "COUNTYNM": ["Clark County", "Clark County", "Washoe County", "Missing County"],
            "SECTOR": [1, 1, 2, 2],
            "HEADROOM_MAIN": [1000, 1100, 1200, 1300],
        }
    ).to_parquet(analysis_panel, index=False)

    fmr_panel = tmp_path / "hud_fmr_2br_2009_2023.csv"
    pd.DataFrame(
        {
            "year": [2009, 2010, 2009],
            "state": ["NV", "NV", "NV"],
            "state_fips": ["32", "32", "32"],
            "county_name": ["Clark County", "Clark County", "Washoe County"],
            "county_name_norm": ["clark", "clark", "washoe"],
            "county_fips": ["32003", "32003", "32031"],
            "area_code": ["x", "x", "y"],
            "area_name": ["Las Vegas-Henderson-Paradise, NV", "Las Vegas-Henderson-Paradise, NV", "Reno, NV"],
            "hud_fmr_2br": [900, 925, 850],
        }
    ).to_csv(fmr_panel, index=False)

    paths = build_local_housing_controls(
        analysis_panel=analysis_panel,
        fmr_panel=fmr_panel,
        output_dir=tmp_path / "out",
        scope="test",
        min_match_rate=0.0,
        min_year_sector_match_rate=0.0,
    )
    controls = pd.read_parquet(paths["controls"])
    audit = pd.read_csv(paths["audit"])
    unmatched = pd.read_csv(paths["unmatched"])

    assert controls["hud_fmr_2br"].notna().sum() == 3
    assert controls.loc[controls["UNITID"].eq(1) & controls["year"].eq(2010), "hud_fmr_2br"].iloc[0] == 925
    assert len(unmatched) == 1
    assert audit["matched_rows"].sum() == 3
    assert "multi_match" in paths
    summary_text = paths["summary"].read_text(encoding="utf-8")
    assert str(tmp_path) not in summary_text


def test_normalize_hud_fmr_directory_accepts_annual_excel_files(tmp_path: Path) -> None:
    raw_dir = tmp_path / "annual"
    raw_dir.mkdir()
    pd.DataFrame(
        {
            "stusps": ["NV", "NV"],
            "fips": [3200399999, 3203199999],
            "countyname": ["Clark County", "Washoe County"],
            "hud_area_name": ["Las Vegas-Henderson-Paradise, NV", "Reno, NV"],
            "hud_area_code": ["a", "b"],
            "fmr_2": [1100, 950],
        }
    ).to_excel(raw_dir / "FY23_FMRs_revised.xlsx", index=False)

    paths = normalize_hud_fmr_directory(raw_dir, tmp_path / "out", start_year=2023, end_year=2023)
    normalized = pd.read_csv(paths["panel"])
    sources = pd.read_csv(paths["source_files"])

    assert len(normalized) == 2
    assert set(normalized["county_fips"].astype(str).str.zfill(5)) == {"32003", "32031"}
    assert normalized["hud_fmr_2br"].sum() == 2050
    assert sources.loc[0, "year"] == 2023
    assert sources.loc[0, "source_file"] == "FY23_FMRs_revised.xlsx"
    assert str(tmp_path) not in sources.to_csv(index=False)


def test_build_local_housing_controls_fails_below_match_threshold(tmp_path: Path) -> None:
    analysis_panel = tmp_path / "analysis.parquet"
    pd.DataFrame(
        {
            "UNITID": [1, 2],
            "year": [2009, 2009],
            "STABBR": ["NV", "NV"],
            "COUNTYNM": ["Clark County", "Missing County"],
            "SECTOR": [1, 1],
        }
    ).to_parquet(analysis_panel, index=False)
    fmr_panel = tmp_path / "hud_fmr_2br_2009_2023.csv"
    pd.DataFrame(
        {
            "year": [2009],
            "state": ["NV"],
            "county_name": ["Clark County"],
            "county_name_norm": ["clark"],
            "county_fips": ["32003"],
            "area_name": ["Las Vegas-Henderson-Paradise, NV"],
            "hud_fmr_2br": [900],
        }
    ).to_csv(fmr_panel, index=False)

    with pytest.raises(ValueError, match="match rate"):
        build_local_housing_controls(
            analysis_panel=analysis_panel,
            fmr_panel=fmr_panel,
            output_dir=tmp_path / "out",
            scope="test",
            min_match_rate=0.99,
            min_year_sector_match_rate=0.99,
        )


def test_normalize_hud_fmr_directory_requires_all_requested_years(tmp_path: Path) -> None:
    raw_dir = tmp_path / "annual"
    raw_dir.mkdir()
    pd.DataFrame(
        {
            "stusps": ["NV"],
            "fips": [3200399999],
            "countyname": ["Clark County"],
            "hud_area_name": ["Las Vegas-Henderson-Paradise, NV"],
            "hud_area_code": ["a"],
            "fmr_2": [1100],
        }
    ).to_excel(raw_dir / "FY23_FMRs_revised.xlsx", index=False)

    with pytest.raises(ValueError, match="Missing HUD annual FMR files"):
        normalize_hud_fmr_directory(raw_dir, tmp_path / "out", start_year=2022, end_year=2023)
