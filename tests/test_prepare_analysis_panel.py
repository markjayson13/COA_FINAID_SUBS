from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from coa_finaid_subs.audit_variable_config import audit_variable_config
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
        "IMP_IC": 1,
        "IMP_SFA": 1,
        "IMP_F": 1,
        "IMP_EF": 1,
        "IMP_E12": 1,
        "IMP_ADM": 1,
        "LOCK_IC": 1,
        "LOCK_SFA": 1,
        "LOCK_F": 1,
        "LOCK_EF": 1,
        "LOCK_E12": 1,
        "LOCK_ADM": 1,
        "REV_IC": 0,
        "REV_SFA": 0,
        "REV_F": 0,
        "REV_EF": 0,
        "REV_E12": 0,
        "REV_ADM": 0,
        "IDX_SFA": -2,
        "IDX_F": -2,
        "IDX_EF": -2,
        "IDX_E12": -2,
        "IDX_ADM": -2,
        "PRCH_SFA": -2,
        "PRCH_F": -2,
        "PRCH_EF": -2,
        "PRCH_E12": -2,
        "PRCH_ADM": -2,
        "PCSFA_F": 0,
        "PCF_F": 0,
        "PCF_F_RV": 0,
        "PCEF_F": 0,
        "PCE12_F": 0,
        "PCADM_F": 0,
        "STABBR": "NV",
        "FIPS": 32,
        "OBEREG": 6,
        "LOCALE": 11,
        "INSTSIZE": 3,
        "CCBASIC": 18,
        "DEGGRANT": 1,
        "UGOFFER": 1,
        "HBCU": 2,
        "TRIBAL": 2,
        "LANDGRNT": 2,
        "OPENADMP": 2,
        "APPLCN": 1_000,
        "ADMSSN": 600,
        "ENRLT": 300,
        "SATVR25": 500,
        "SATVR75": 620,
        "SATMT25": 510,
        "SATMT75": 630,
        "ACTCM25": 20,
        "ACTCM75": 28,
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
        "SGRNT_A": 2_000,
        "SGRNT_N": 20,
        "SGRNT_P": 20.0,
        "SGRNT_T": 40_000,
        "OFGRT_A": 500,
        "OFGRT_N": 10,
        "OFGRT_P": 10.0,
        "OFGRT_T": 5_000,
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
        "OLOAN_A": 1_000,
        "OLOAN_N": 5,
        "OLOAN_P": 5.0,
        "OLOAN_T": 5_000,
        "SCFA2": 100,
        "SCFA1N": 90,
        "SCFA1P": 90.0,
        "ANYAIDN": 80,
        "ANYAIDP": 80.0,
        "SCUGRAD": 120,
        "SCUGFFN": 90,
        "SCUGFFP": 75.0,
        "UAGRNTA": 4_400,
        "UAGRNTN": 110,
        "UAGRNTP": 91.7,
        "UAGRNTT": 528_000,
        "UFLOANA": 5_500,
        "UFLOANN": 60,
        "UFLOANP": 50.0,
        "UFLOANT": 330_000,
        "UPGRNTA": 3_300,
        "UPGRNTN": 100,
        "UPGRNTP": 50.0,
        "UPGRNTT": 330_000,
        "NPIS410": 900,
        "NPIS420": 1_900,
        "NPIS430": 2_900,
        "NPIS440": 3_900,
        "NPIS450": 4_900,
        "NPT410": 1_200,
        "NPT420": 2_200,
        "NPT430": 3_200,
        "NPT440": 4_200,
        "NPT450": 5_200,
        "F1A06": 10_000_000,
        "F1B01": 3_000_000,
        "F1B11": 1_000_000,
        "F1B12": 200_000,
        "F1B14": 300_000,
        "F1B15": 100_000,
        "F1D01": 12_000_000,
        "F1D02": 11_000_000,
        "F1H01": 2_000_000,
        "F1C011": 4_000_000,
        "F1C051": 1_500_000,
        "F1C061": 1_000_000,
        "F1C071": 900_000,
        "F2A02": 20_000_000,
        "F2B01": 15_000_000,
        "F2B02": 14_000_000,
        "F2D01": 6_000_000,
        "F2H01": 5_000_000,
        "F2E011": 5_000_000,
        "F2E041": 2_000_000,
        "F2E051": 1_100_000,
        "F2E061": 1_200_000,
        "EXTRA_DROP": "not selected",
    }
    return [
        {"year": 2008, "UNITID": 1, "PSET4FLG": 1, "SECTOR": 1, **base},
        {
            "year": 2009,
            "UNITID": 1,
            "PSET4FLG": 1,
            "SECTOR": 1,
            **base,
            "NPIS410": -20,
            "NPT410": -10,
            "IMP_SFA": 2,
            "REV_F": 1,
            "IDX_SFA": 99_999,
            "PCSFA_F": 50,
        },
        {"year": 2009, "UNITID": 2, "PSET4FLG": 1, "SECTOR": 2, **base, "CONTROL": 2, "CHG2AY0": 12_000},
        {"year": 2009, "UNITID": 3, "PSET4FLG": 2, "SECTOR": 1, **base},
        {"year": 2009, "UNITID": 4, "PSET4FLG": 1, "SECTOR": 4, **base},
        {"year": 2009, "UNITID": 6, "PSET4FLG": 1, "SECTOR": 3, **base, "CONTROL": 3, "CHG2AY0": 13_000},
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
            ("IGRNT_T", "Total amount of institutional grant aid received", "SFA"),
            ("NPIS410", "Public average net price income 0-30000", "SFA"),
            ("NPT410", "Average net price income 0-30000", "SFA"),
            ("STABBR", "State abbreviation", "HD"),
            ("OPENADMP", "Open admission policy", "IC"),
            ("F1D01", "Total revenues and other additions", "F"),
            ("F2B01", "Total revenues and investment return", "F"),
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
    assert "SGRNT_T" in names
    assert "OFGRT_T" in names
    assert "OLOAN_T" in names
    assert "UPGRNTA" in names
    assert "UPGRNTT" in names
    assert "STABBR" in names
    assert "LOCALE" in names
    assert "OPENADMP" in names
    assert "F1D01" in names
    assert "F2B01" in names
    assert "F3B01" in names
    assert "NPIS410" in names
    assert "NPT410" in names
    assert "IMP_SFA" in names
    assert "REV_F" in names
    assert "PCSFA_F" in names


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
    assert summary["sector_scope"] == "public_private_nonprofit"
    analysis_path = output_dir / "analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet"
    out = pd.read_parquet(analysis_path)
    assert out["UNITID"].tolist() == [1, 2]
    assert "EXTRA_DROP" not in out.columns

    first = out[out["UNITID"] == 1].iloc[0]
    assert first["COA_ON"] == 19_000
    assert first["HEADROOM_ON"] == 9_000
    assert first["COA_OFF_NF"] == 21_000
    assert first["HEADROOM_OFF_NF"] == 11_000
    assert first["PGRNT_PER_FTFT_COHORT"] == pytest.approx(150_000 / 90)
    assert first["IGRNT_PER_FTFT_COHORT"] == pytest.approx(225_000 / 90)
    assert first["PELL_SHARE_OF_TOTAL_GRANT_FTFT"] == pytest.approx(150_000 / 320_000)
    assert first["ADMIT_RATE"] == pytest.approx(0.6)
    assert first["YIELD_RATE"] == pytest.approx(0.5)
    assert first["SAT_TOTAL_MIDPOINT"] == 1_130
    assert first["ACT_COMPOSITE_MIDPOINT"] == 24
    assert first["FIN_TOTAL_REVENUE"] == 12_000_000
    assert first["FIN_TUITION_REVENUE"] == 3_000_000
    assert first["FIN_STATE_LOCAL_APPROPS_PUBLIC"] == 1_600_000

    second = out[out["UNITID"] == 2].iloc[0]
    assert second["FIN_TOTAL_REVENUE"] == 15_000_000
    assert second["FIN_TUITION_REVENUE"] == 6_000_000
    assert pd.isna(second["FIN_STATE_LOCAL_APPROPS_PUBLIC"])
    assert first["NPT410"] == -10
    assert pd.isna(first["NPT410_CLEAN"])
    assert bool(first["FLAG_NEGATIVE_NPT410"]) is True
    assert first["NET_PRICE_0_30000"] == -20
    assert pd.isna(first["NET_PRICE_0_30000_CLEAN"])
    assert bool(first["FLAG_NEGATIVE_NET_PRICE_0_30000"]) is True
    assert bool(first["FLAG_IPEDS_SFA_IMPUTED"]) is True
    assert bool(first["FLAG_IPEDS_SFA_PARENT_LINK"]) is True
    assert bool(first["FLAG_IPEDS_F_REVISED"]) is True
    assert bool(first["FLAG_IPEDS_ANY_METADATA_EXPOSURE"]) is True
    assert second["NET_PRICE_0_30000"] == 1_200
    assert second["NET_PRICE_0_30000_CLEAN"] == 1_200
    assert bool(second["FLAG_IPEDS_SFA_IMPUTED"]) is False
    assert bool(second["FLAG_IPEDS_SFA_PARENT_LINK"]) is False
    assert bool(second["FLAG_IPEDS_F_REVISED"]) is False
    assert bool(second["FLAG_IPEDS_ANY_METADATA_EXPOSURE"]) is False

    manifest = pd.read_csv(output_dir / "analysis_variable_manifest.csv")
    assert manifest.loc[manifest["varname"] == "PGRNT_A", "group"].iloc[0] == "ftft_pell"
    assert manifest.loc[manifest["varname"] == "NET_PRICE_0_30000", "group"].iloc[0] == "derived_net_price"
    assert manifest.loc[manifest["varname"] == "FLAG_IPEDS_SFA_IMPUTED", "group"].iloc[0] == "derived_metadata_flag"
    sample = pd.read_csv(output_dir / "analysis_sample_counts.csv")
    assert int(sample.loc[sample["sample"] == "analysis_four_year_titleiv_public_private_nonprofit", "rows"].iloc[0]) == 2
    metadata = pd.read_csv(output_dir / "analysis_metadata_flag_summary.csv")
    flagged = metadata[
        (metadata["scope"] == "overall")
        & (metadata["flag"] == "FLAG_IPEDS_SFA_IMPUTED")
    ]["flagged_rows"].iloc[0]
    assert int(flagged) == 1
    metadata_codes = pd.read_csv(output_dir / "analysis_metadata_code_summary.csv")
    assert "LOCK_SFA" in set(metadata_codes["varname"])


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


def test_prepare_analysis_panel_can_build_forprofit_diagnostic_sample(tmp_path: Path) -> None:
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
        sectors_spec="3",
    )

    assert summary["analysis_rows"] == 1
    assert summary["sector_scope"] == "private_forprofit_diagnostic"
    analysis_path = output_dir / "analysis_panel_coa_headroom_2009_2023_private_forprofit_diagnostic.parquet"
    out = pd.read_parquet(analysis_path)
    assert out["UNITID"].tolist() == [6]


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


def test_audit_variable_config_writes_coverage_outputs(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.parquet"
    output_dir = tmp_path / "audit"
    write_parquet(panel_path, panel_rows())

    outputs = audit_variable_config(
        input_panel=panel_path,
        output_dir=output_dir,
        variable_config=VARIABLE_CONFIG,
    )

    coverage = pd.read_csv(outputs["coverage"])
    complete_cases = pd.read_csv(outputs["complete_cases"])
    metadata_flags = pd.read_csv(outputs["metadata_flags"])
    metadata_codes = pd.read_csv(outputs["metadata_codes"])
    assert {"coverage", "groups", "complete_cases", "metadata_flags", "metadata_codes"} == set(outputs)
    assert coverage.loc[coverage["varname"] == "PGRNT_A", "coverage"].iloc[0] == 1.0
    primary_rows = complete_cases.loc[
        complete_cases["scenario"] == "primary_headroom_pell_institutional_avg", "rows"
    ].iloc[0]
    assert int(primary_rows) == 2
    assert "net_price_current_income_bands_sector_appropriate" in set(complete_cases["scenario"])
    assert "FLAG_IPEDS_SFA_IMPUTED" in set(metadata_flags["flag"])
    assert "LOCK_SFA" in set(metadata_codes["varname"])
