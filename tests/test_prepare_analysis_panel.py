from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from coa_finaid_subs.prepare_analysis_panel import load_variable_specs, prepare_analysis_panel


REPO_ROOT = Path(__file__).resolve().parents[1]
VARIABLE_CONFIG = REPO_ROOT / "config" / "analysis_variables.csv"


def write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = {key: [row.get(key) for row in rows] for key in rows[0]}
    pq.write_table(pa.table(columns), path)


def panel_rows() -> list[dict]:
    base = {
        "INSTNM": "Example University",
        "OPEID": "00123400",
        "PSEFLAG": 1,
        "CONTROL": 1,
        "ICLEVEL": 1,
        "HLOFFER": 5,
        "F2PELL": 1,
        "F3PELL": None,
        "CHG2AY0": 10_000,
        "CHG3AY0": 20_000,
        "CHG4AY0": 1_000,
        "CHG5AY0": 6_000,
        "CHG6AY0": 2_000,
        "CHG7AY0": 7_000,
        "CHG8AY0": 3_000,
        "CHG9AY0": 2_500,
        "AGRNT_A": 4_000,
        "AGRNT_N": 80,
        "AGRNT_P": 80.0,
        "AGRNT_T": 320_000,
        "FGRNT_A": 3_500,
        "FGRNT_N": 70,
        "FGRNT_P": 70.0,
        "FGRNT_T": 245_000,
        "PGRNT_A": 3_000,
        "PGRNT_N": 50,
        "PGRNT_P": 50.0,
        "PGRNT_T": 150_000,
        "IGRNT_A": 5_000,
        "IGRNT_N": 45,
        "IGRNT_P": 45.0,
        "IGRNT_T": 225_000,
        "LOAN_A": 6_000,
        "LOAN_N": 40,
        "LOAN_P": 40.0,
        "LOAN_T": 240_000,
        "FLOAN_A": 5_000,
        "FLOAN_N": 35,
        "FLOAN_P": 35.0,
        "FLOAN_T": 175_000,
        "SCFA2": 100,
        "SCFA1N": 90,
        "SCFA1P": 90.0,
        "ANYAIDN": 80,
        "ANYAIDP": 80.0,
        "UAGRNTA": 4_400,
        "UFLOANA": 5_500,
        "UPGRNTA": 3_300,
        "UPGRNTN": 100,
        "UPGRNTP": 50.0,
        "UPGRNTT": 330_000,
        "NPT410": 1_200,
        "NPT420": 2_200,
        "NPT430": 3_200,
        "NPT440": 4_200,
        "NPT450": 5_200,
        "EXTRA_DROP": "not selected",
    }
    return [
        {"year": 2008, "UNITID": 1, "PSET4FLG": 1, "SECTOR": 1, **base},
        {"year": 2009, "UNITID": 1, "PSET4FLG": 1, "SECTOR": 1, **base, "NPT410": -10},
        {"year": 2009, "UNITID": 2, "PSET4FLG": 1, "SECTOR": 2, **base, "CHG2AY0": 12_000},
        {"year": 2009, "UNITID": 3, "PSET4FLG": 2, "SECTOR": 1, **base},
        {"year": 2009, "UNITID": 4, "PSET4FLG": 1, "SECTOR": 4, **base},
        {"year": 2010, "UNITID": 5, "PSET4FLG": None, "SECTOR": None, **base},
    ]


def dictionary_rows() -> list[dict]:
    rows = []
    for year in [2009, 2010]:
        for var, title, source in [
            ("UNITID", "Unit identifier", "HD"),
            ("PSET4FLG", "Postsecondary and Title IV institution indicator", "HD"),
            ("SECTOR", "Sector of institution", "HD"),
            ("CHG2AY0", "Published in-state tuition and fees", "IC"),
            ("CHG4AY0", "Books and supplies", "IC"),
            ("CHG7AY0", "Off-campus room and board", "IC"),
            ("CHG8AY0", "Off-campus other expenses", "IC"),
            ("PGRNT_A", "Average amount of Pell grant aid received", "SFA"),
            ("PGRNT_T", "Total amount of Pell grant aid received", "SFA"),
            ("IGRNT_A", "Average amount of institutional grant aid received", "SFA"),
            ("NPT410", "Average net price income 0-30000", "SFA"),
        ]:
            rows.append(
                {
                    "year": year,
                    "varname": var,
                    "varTitle": title,
                    "longDescription": f"{title} description",
                    "DataType": "N",
                    "source_file": source,
                    "access_table_name": f"{source}{year}",
                }
            )
    return rows


def test_variable_config_contains_core_inputs() -> None:
    names = [spec.varname for spec in load_variable_specs(VARIABLE_CONFIG)]

    assert names[:2] == ["year", "UNITID"]
    assert "PSET4FLG" in names
    assert "SECTOR" in names
    assert "CHG2AY0" in names
    assert "CHG9AY0" in names
    assert "PGRNT_A" in names
    assert "PGRNT_T" in names
    assert "UPGRNTA" in names
    assert "UPGRNTT" in names


def test_prepare_analysis_panel_filters_constructs_and_writes_audit_outputs(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.parquet"
    dictionary_path = tmp_path / "dictionary.parquet"
    output_dir = tmp_path / "outputs"
    write_parquet(panel_path, panel_rows())
    write_parquet(dictionary_path, dictionary_rows())

    summary = prepare_analysis_panel(
        input_panel=panel_path,
        dictionary=dictionary_path,
        output_dir=output_dir,
        variable_config=VARIABLE_CONFIG,
    )

    assert summary["analysis_rows"] == 2
    analysis_path = output_dir / "analysis_panel_coa_headroom_2009_2023.parquet"
    out = pd.read_parquet(analysis_path)
    assert out["UNITID"].tolist() == [1, 2]
    assert "EXTRA_DROP" not in out.columns

    first = out[out["UNITID"] == 1].iloc[0]
    assert first["COA_ON"] == 19_000
    assert first["HEADROOM_ON"] == 9_000
    assert first["COA_OFF_NF"] == 21_000
    assert first["HEADROOM_OFF_NF"] == 11_000
    assert first["NPT410"] == -10
    assert pd.isna(first["NPT410_CLEAN"])
    assert bool(first["FLAG_NEGATIVE_NPT410"]) is True

    manifest = pd.read_csv(output_dir / "analysis_variable_manifest.csv")
    assert manifest.loc[manifest["varname"] == "PGRNT_A", "group"].iloc[0] == "ftft_pell"
    sample = pd.read_csv(output_dir / "analysis_sample_counts.csv")
    assert int(sample.loc[sample["sample"] == "primary_four_year_titleiv", "rows"].iloc[0]) == 2


def test_prepare_analysis_panel_fails_on_duplicate_unitid_year(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.parquet"
    dictionary_path = tmp_path / "dictionary.parquet"
    write_parquet(panel_path, [panel_rows()[1], panel_rows()[1]])
    write_parquet(dictionary_path, dictionary_rows())

    with pytest.raises(SystemExit, match="duplicate UNITID-year rows"):
        prepare_analysis_panel(
            input_panel=panel_path,
            dictionary=dictionary_path,
            output_dir=tmp_path / "outputs",
            variable_config=VARIABLE_CONFIG,
        )


def test_prepare_analysis_panel_accepts_string_coded_sample_fields(tmp_path: Path) -> None:
    rows = panel_rows()
    for idx, row in enumerate(rows):
        rows[idx] = {
            **row,
            "PSET4FLG": None if row["PSET4FLG"] is None else str(row["PSET4FLG"]),
            "SECTOR": None if row["SECTOR"] is None else str(row["SECTOR"]),
            "CONTROL": str(row["CONTROL"]),
            "ICLEVEL": str(row["ICLEVEL"]),
        }
    panel_path = tmp_path / "panel.parquet"
    dictionary_path = tmp_path / "dictionary.parquet"
    write_parquet(panel_path, rows)
    write_parquet(dictionary_path, dictionary_rows())

    summary = prepare_analysis_panel(
        input_panel=panel_path,
        dictionary=dictionary_path,
        output_dir=tmp_path / "outputs",
        variable_config=VARIABLE_CONFIG,
    )

    assert summary["analysis_rows"] == 2

