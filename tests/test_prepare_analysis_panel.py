from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from coa_finaid_subs.audit_extremes import audit_extremes
from coa_finaid_subs.audit_variable_config import audit_variable_config, audit_variable_outputs
from coa_finaid_subs.descriptive_decomposition import build_descriptive_decomposition
from coa_finaid_subs.descstat_tables import build_descstat_tables
from coa_finaid_subs.headroom_measures import audit_headroom_measures, load_headroom_specs
from coa_finaid_subs.model_plan import audit_model_plan
from coa_finaid_subs.model_samples import build_model_samples
from coa_finaid_subs.prepare_analysis_panel import load_variable_specs, prepare_analysis_outputs, prepare_analysis_panel


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
        "SATPCT": 60,
        "ACTCM25": 20,
        "ACTCM75": 28,
        "ACTPCT": 40,
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
        {
            "year": 2009,
            "UNITID": 2,
            "PSET4FLG": 1,
            "SECTOR": 2,
            **base,
            "CONTROL": 2,
            "CHG2AY0": 12_000,
            "ADMSSN": 900,
            "SATVR25": 430,
            "SATVR75": 530,
            "SATMT25": 440,
            "SATMT75": 540,
            "ACTCM25": 17,
            "ACTCM75": 23,
            "PGRNT_T": 0,
            "OLOAN_A": 0,
            "OLOAN_N": 0,
            "OLOAN_P": 0,
            "OLOAN_T": 0,
        },
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
    scoped_output_dir = output_dir / "public_private_nonprofit"
    analysis_path = scoped_output_dir / "analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet"
    out = pd.read_parquet(analysis_path)
    assert out["UNITID"].tolist() == [1, 2]
    assert "EXTRA_DROP" not in out.columns

    first = out[out["UNITID"] == 1].iloc[0]
    assert first["COA_ON"] == 19_000
    assert first["HEADROOM_ON"] == 9_000
    assert first["COA_OFF_NF"] == 21_000
    assert first["HEADROOM_OFF_NF"] == 11_000
    assert first["COA_MAIN"] == 21_000
    assert first["HEADROOM_MAIN"] == 11_000
    assert first["HEADROOM_MAIN_SHARE_COA"] == pytest.approx(11_000 / 21_000)
    assert first["HEADROOM_MAIN_SHARE_TUITION"] == pytest.approx(1.1)
    assert first["PGRNT_PER_FTFT_COHORT"] == pytest.approx(150_000 / 90)
    assert first["IGRNT_PER_FTFT_COHORT"] == pytest.approx(225_000 / 90)
    assert first["PELL_SHARE_OF_TOTAL_GRANT_FTFT"] == pytest.approx(150_000 / 320_000)
    assert first["ADMIT_RATE"] == pytest.approx(0.6)
    assert first["YIELD_RATE"] == pytest.approx(0.5)
    assert first["SAT_TOTAL_MIDPOINT"] == 1_130
    assert first["ACT_COMPOSITE_MIDPOINT"] == 24
    assert bool(first["OPEN_ADMISSIONS_FLAG"]) is False
    assert bool(first["SELECTIVE_ADMISSIONS_FLAG"]) is True
    assert bool(first["VALID_ADMIT_RATE_FLAG"]) is True
    assert bool(first["SELECTIVE_ADMISSIONS_ROBUSTNESS_SAMPLE"]) is True
    assert first["TEST_SCORE_REPORTING_SHARE"] == 60
    assert first["SELECTIVITY_INDEX"] == pytest.approx(1.0)
    assert first["SELECTIVITY_PERCENTILE_WITHIN_YEAR"] == pytest.approx(1.0)
    assert first["SELECTIVITY_CATEGORY"] == "highly_selective"
    assert first["FIN_TOTAL_REVENUE"] == 12_000_000
    assert first["FIN_TUITION_REVENUE"] == 3_000_000
    assert first["FIN_STATE_LOCAL_APPROPS_PUBLIC"] == 1_600_000

    second = out[out["UNITID"] == 2].iloc[0]
    assert second["FIN_TOTAL_REVENUE"] == 15_000_000
    assert second["FIN_TUITION_REVENUE"] == 6_000_000
    assert pd.isna(second["FIN_STATE_LOCAL_APPROPS_PUBLIC"])
    assert second["ADMIT_RATE"] == pytest.approx(0.9)
    assert second["SAT_TOTAL_MIDPOINT"] == 970
    assert second["ACT_COMPOSITE_MIDPOINT"] == 20
    assert second["SELECTIVITY_INDEX"] == pytest.approx(-1.0)
    assert second["SELECTIVITY_CATEGORY"] == "moderately_selective"
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

    manifest = pd.read_csv(scoped_output_dir / "analysis_variable_manifest.csv")
    assert manifest.loc[manifest["varname"] == "PGRNT_A", "group"].iloc[0] == "ftft_pell"
    assert manifest.loc[manifest["varname"] == "NET_PRICE_0_30000", "group"].iloc[0] == "derived_net_price"
    assert manifest.loc[manifest["varname"] == "FLAG_IPEDS_SFA_IMPUTED", "group"].iloc[0] == "derived_metadata_flag"
    sample = pd.read_csv(scoped_output_dir / "analysis_sample_counts.csv")
    assert int(sample.loc[sample["sample"] == "analysis_four_year_titleiv_public_private_nonprofit", "rows"].iloc[0]) == 2
    balance = pd.read_csv(scoped_output_dir / "analysis_panel_balance_by_institution.csv")
    assert set(balance["UNITID"]) == {1, 2}
    assert set(balance["years_observed"]) == {1}
    assert bool(balance.loc[balance["UNITID"] == 1, "balanced_full_window"].iloc[0]) is False
    assert bool(balance.loc[balance["UNITID"] == 1, "last_observed_before_end"].iloc[0]) is True
    balance_summary = pd.read_csv(scoped_output_dir / "analysis_panel_balance_summary.csv")
    overall_balance = balance_summary[balance_summary["scope"] == "overall"].iloc[0]
    assert int(overall_balance["institutions"]) == 2
    assert int(overall_balance["balanced_institutions"]) == 0
    entry_exit = pd.read_csv(scoped_output_dir / "analysis_entry_exit_by_sector_year.csv")
    entry_2009 = entry_exit[(entry_exit["sector"] == "all") & (entry_exit["year"] == 2009)].iloc[0]
    assert int(entry_2009["first_observed_in_window"]) == 2
    assert int(entry_2009["first_observed_after_window_start"]) == 0
    assert int(entry_2009["last_observed_before_window_end"]) == 2
    sector_year = pd.read_csv(scoped_output_dir / "analysis_institution_years_by_sector_year.csv")
    assert int(sector_year[(sector_year["sector"] == "public") & (sector_year["year"] == 2009)]["institution_years"].iloc[0]) == 1
    assert int(
        sector_year[(sector_year["sector"] == "private_nonprofit") & (sector_year["year"] == 2009)]["institution_years"].iloc[0]
    ) == 1
    min_years = pd.read_csv(scoped_output_dir / "analysis_min_years_sensitivity.csv")
    assert int(min_years[(min_years["sector"] == "all") & (min_years["min_years_required"] == 1)]["institutions_retained"].iloc[0]) == 2
    assert int(min_years[(min_years["sector"] == "all") & (min_years["min_years_required"] == 2)]["institutions_retained"].iloc[0]) == 0
    metadata = pd.read_csv(scoped_output_dir / "analysis_metadata_flag_summary.csv")
    flagged = metadata[
        (metadata["scope"] == "overall")
        & (metadata["flag"] == "FLAG_IPEDS_SFA_IMPUTED")
    ]["flagged_rows"].iloc[0]
    assert int(flagged) == 1
    metadata_codes = pd.read_csv(scoped_output_dir / "analysis_metadata_code_summary.csv")
    assert "LOCK_SFA" in set(metadata_codes["varname"])
    selective_panel = pd.read_parquet(scoped_output_dir / "analysis_panel_selective_admissions_robustness_2009_2023_public_private_nonprofit.parquet")
    assert selective_panel["UNITID"].tolist() == [1, 2]
    selectivity_summary = pd.read_csv(scoped_output_dir / "analysis_selectivity_summary.csv")
    assert {"highly_selective", "moderately_selective"} <= set(selectivity_summary["selectivity_category"])
    aid_zero = pd.read_csv(scoped_output_dir / "analysis_aid_zero_consistency.csv")
    pgrnt_zero = aid_zero[(aid_zero["scope"] == "overall") & (aid_zero["aid_family"] == "PGRNT")].iloc[0]
    assert int(pgrnt_zero["suspect_zero_rows"]) == 1
    assert int(pgrnt_zero["suspect_zero_total_rows"]) == 1
    oloan_zero = aid_zero[(aid_zero["scope"] == "overall") & (aid_zero["aid_family"] == "OLOAN")].iloc[0]
    assert int(oloan_zero["true_zero_rows"]) == 1
    suspect_rows = pd.read_csv(scoped_output_dir / "analysis_aid_zero_suspect_rows.csv")
    suspect_pgrnt = suspect_rows[(suspect_rows["UNITID"] == 2) & (suspect_rows["aid_family"] == "PGRNT")].iloc[0]
    assert bool(suspect_pgrnt["suspect_zero_total"]) is True
    assert "suspect_zero_total" in suspect_pgrnt["issue_reason"]
    assert summary["selective_admissions_robustness_rows"] == 2
    assert {
        "panel_balance_by_institution",
        "panel_balance_summary",
        "entry_exit_by_sector_year",
        "entry_exit_reason_audit",
        "institution_years_by_sector_year",
        "min_years_sensitivity",
        "selectivity_summary",
        "aid_zero_consistency",
        "aid_zero_suspect_rows",
    } <= set(summary["artifacts"])


def test_entry_exit_reason_audit_classifies_sample_transitions(tmp_path: Path) -> None:
    template = panel_rows()[1]

    def row(unitid: int, year: int, pset4flg: int, sector: int) -> dict:
        control = 3 if sector == 3 else sector
        return {
            **template,
            "UNITID": unitid,
            "year": year,
            "PSET4FLG": pset4flg,
            "SECTOR": sector,
            "CONTROL": control,
        }

    rows = [
        row(101, 2009, 2, 1),
        row(101, 2010, 1, 1),
        row(102, 2009, 1, 3),
        row(102, 2010, 1, 1),
        row(103, 2009, 2, 3),
        row(103, 2010, 1, 2),
        row(104, 2010, 1, 1),
        row(201, 2009, 1, 1),
        row(201, 2010, 2, 1),
        row(202, 2009, 1, 1),
        row(202, 2010, 1, 3),
        row(203, 2009, 1, 2),
        row(203, 2010, 2, 3),
        row(204, 2009, 1, 1),
        row(301, 2009, 1, 1),
        row(301, 2010, 1, 1),
    ]
    panel_path = tmp_path / "panel.parquet"
    dictionary_path = tmp_path / "dictionary.parquet"
    output_dir = tmp_path / "outputs"
    write_parquet(panel_path, rows)
    write_parquet(dictionary_path, dictionary_rows())

    prepare_analysis_panel(
        input_panel=panel_path,
        dictionary=dictionary_path,
        output_dir=output_dir,
        variable_config=VARIABLE_CONFIG,
        years_spec="2009:2010",
    )

    audit = pd.read_csv(output_dir / "public_private_nonprofit" / "analysis_entry_exit_reason_audit.csv")
    reasons = {
        (row["event_type"], int(row["UNITID"])): row["reason_category"]
        for row in audit.to_dict("records")
    }
    assert reasons == {
        ("entry", 101): "pset4flg_transition",
        ("entry", 102): "sector_transition",
        ("entry", 103): "pset4flg_and_sector_transition",
        ("entry", 104): "full_panel_first_appearance",
        ("exit", 201): "pset4flg_transition",
        ("exit", 202): "sector_transition",
        ("exit", 203): "pset4flg_and_sector_transition",
        ("exit", 204): "full_panel_disappearance",
    }
    both = audit[(audit["event_type"] == "entry") & (audit["UNITID"] == 103)].iloc[0]
    assert bool(both["pset4flg_transition"]) is True
    assert bool(both["sector_transition"]) is True
    first = audit[(audit["event_type"] == "entry") & (audit["UNITID"] == 104)].iloc[0]
    assert bool(first["full_panel_first_appearance"]) is True
    disappeared = audit[(audit["event_type"] == "exit") & (audit["UNITID"] == 204)].iloc[0]
    assert bool(disappeared["full_panel_disappearance"]) is True


def test_prepare_analysis_outputs_writes_baseline_and_sector_splits(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.parquet"
    dictionary_path = tmp_path / "dictionary.parquet"
    output_dir = tmp_path / "outputs"
    write_parquet(panel_path, panel_rows())
    write_parquet(dictionary_path, dictionary_rows())

    summaries = prepare_analysis_outputs(
        input_panel=panel_path,
        dictionary=dictionary_path,
        output_dir=output_dir,
        variable_config=VARIABLE_CONFIG,
    )

    labels = [summary["sector_scope"] for summary in summaries]
    assert labels == ["public_private_nonprofit", "public", "private_nonprofit"]
    assert not (output_dir / "private_forprofit_diagnostic").exists()

    public = pd.read_parquet(output_dir / "public" / "analysis_panel_coa_headroom_2009_2023_public.parquet")
    private_np = pd.read_parquet(
        output_dir / "private_nonprofit" / "analysis_panel_coa_headroom_2009_2023_private_nonprofit.parquet"
    )
    assert public["UNITID"].tolist() == [1]
    assert private_np["UNITID"].tolist() == [2]


def test_prepare_analysis_outputs_can_include_forprofit_diagnostic(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.parquet"
    dictionary_path = tmp_path / "dictionary.parquet"
    output_dir = tmp_path / "outputs"
    write_parquet(panel_path, panel_rows())
    write_parquet(dictionary_path, dictionary_rows())

    summaries = prepare_analysis_outputs(
        input_panel=panel_path,
        dictionary=dictionary_path,
        output_dir=output_dir,
        variable_config=VARIABLE_CONFIG,
        include_forprofit_diagnostic=True,
    )

    labels = [summary["sector_scope"] for summary in summaries]
    assert labels == ["public_private_nonprofit", "public", "private_nonprofit", "private_forprofit_diagnostic"]
    diagnostic = pd.read_parquet(
        output_dir
        / "private_forprofit_diagnostic"
        / "analysis_panel_coa_headroom_2009_2023_private_forprofit_diagnostic.parquet"
    )
    assert diagnostic["UNITID"].tolist() == [6]


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
    analysis_path = output_dir / "private_forprofit_diagnostic" / "analysis_panel_coa_headroom_2009_2023_private_forprofit_diagnostic.parquet"
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


def test_audit_extremes_profiles_shape_types_and_extreme_rows(tmp_path: Path) -> None:
    panel_path = tmp_path / "analysis.parquet"
    rows = [
        {"year": 2009, "UNITID": 1, "INSTNM": "A", "SECTOR": 1, "CONTROL": 1, "PGRNT_T": 100, "HEADROOM_ON": 9_000, "FLAG": True},
        {"year": 2009, "UNITID": 2, "INSTNM": "B", "SECTOR": 1, "CONTROL": 1, "PGRNT_T": 200, "HEADROOM_ON": 10_000, "FLAG": False},
        {"year": 2010, "UNITID": 1, "INSTNM": "A", "SECTOR": 1, "CONTROL": 1, "PGRNT_T": 300, "HEADROOM_ON": 11_000, "FLAG": True},
        {"year": 2010, "UNITID": 3, "INSTNM": "C", "SECTOR": 2, "CONTROL": 2, "PGRNT_T": 99_999, "HEADROOM_ON": -10, "FLAG": False},
    ]
    write_parquet(panel_path, rows)

    paths = audit_extremes(panel_path, tmp_path / "extreme_audit", scope_label="test_scope", top_n=2)

    shape = pd.read_csv(paths["dataset_shape"])
    assert int(shape["rows"].iloc[0]) == 4
    assert int(shape["columns"].iloc[0]) == 8
    assert int(shape["duplicate_unitid_year_rows"].iloc[0]) == 0

    profile = pd.read_csv(paths["variable_profile"])
    pgrnt = profile[profile["varname"] == "PGRNT_T"].iloc[0]
    assert pgrnt["logical_type"] == "numeric"
    assert pgrnt["variable_group"] == "ftft_aid"
    assert int(pgrnt["max"]) == 99_999
    headroom = profile[profile["varname"] == "HEADROOM_ON"].iloc[0]
    assert int(headroom["negative_count"]) == 1

    candidates = pd.read_csv(paths["review_candidates"])
    assert "HEADROOM_ON" in set(candidates["varname"])
    extremes = pd.read_csv(paths["extreme_rows"])
    high_pgrnt = extremes[(extremes["varname"] == "PGRNT_T") & (extremes["direction"] == "high")].iloc[0]
    assert int(high_pgrnt["UNITID"]) == 3
    by_year = pd.read_csv(paths["year_distribution"])
    assert {2009, 2010} <= set(by_year["year"])
    categorical = pd.read_csv(paths["categorical_profile"])
    assert "INSTNM" in set(categorical["varname"])


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
    assert outputs["coverage"].parent == output_dir / "public_private_nonprofit"
    assert coverage.loc[coverage["varname"] == "PGRNT_A", "coverage"].iloc[0] == 1.0
    primary_rows = complete_cases.loc[
        complete_cases["scenario"] == "primary_headroom_pell_institutional_avg", "rows"
    ].iloc[0]
    assert int(primary_rows) == 2
    assert "net_price_current_income_bands_sector_appropriate" in set(complete_cases["scenario"])
    assert "FLAG_IPEDS_SFA_IMPUTED" in set(metadata_flags["flag"])
    assert "LOCK_SFA" in set(metadata_codes["varname"])


def test_audit_variable_outputs_writes_default_sector_audits(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.parquet"
    output_dir = tmp_path / "audit"
    write_parquet(panel_path, panel_rows())

    outputs = audit_variable_outputs(
        input_panel=panel_path,
        output_dir=output_dir,
        variable_config=VARIABLE_CONFIG,
    )

    assert set(outputs) == {"public_private_nonprofit", "public", "private_nonprofit"}
    assert not (output_dir / "private_forprofit_diagnostic").exists()
    public_cases = pd.read_csv(outputs["public"]["complete_cases"])
    private_cases = pd.read_csv(outputs["private_nonprofit"]["complete_cases"])
    assert int(public_cases.loc[public_cases["scenario"] == "primary_headroom_pell_institutional_avg", "rows"].iloc[0]) == 1
    assert int(private_cases.loc[private_cases["scenario"] == "primary_headroom_pell_institutional_avg", "rows"].iloc[0]) == 1


def test_descstat_tables_write_paper_and_appendix_outputs(tmp_path: Path) -> None:
    panel_path = tmp_path / "analysis.parquet"
    config_path = tmp_path / "descstat_variables.csv"
    output_dir = tmp_path / "descstats"
    rows = [
        {"year": 2009, "UNITID": 1, "COA_OFF_NF": 10_000, "HEADROOM_SHARE_OFF_NF": 0.40},
        {"year": 2009, "UNITID": 2, "COA_OFF_NF": 12_000, "HEADROOM_SHARE_OFF_NF": 0.45},
        {"year": 2010, "UNITID": 1, "COA_OFF_NF": 13_000, "HEADROOM_SHARE_OFF_NF": 0.50},
        {"year": 2010, "UNITID": 2, "COA_OFF_NF": 1_000_000, "HEADROOM_SHARE_OFF_NF": 0.55},
    ]
    write_parquet(panel_path, rows)
    config_path.write_text(
        "\n".join(
            [
                "varname,label,section,units,winsorize,winsor_lower,winsor_upper,include_paper,include_appendix",
                "COA_OFF_NF,Cost of attendance,Cost of attendance,dollars,true,0.25,0.75,true,true",
                "HEADROOM_SHARE_OFF_NF,Headroom share,Cost of attendance,share,false,,,true,true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    paths = build_descstat_tables(
        input_panel=panel_path,
        output_dir=output_dir,
        config=config_path,
        scope_label="test_scope",
    )

    assert set(paths) == {
        "full_descstat",
        "paper_csv",
        "paper_tex",
        "paper_docx",
        "appendix_csv",
        "appendix_tex",
        "appendix_docx",
        "summary",
    }
    for path in paths.values():
        assert path.exists()

    full = pd.read_csv(paths["full_descstat"])
    coa = full[full["varname"] == "COA_OFF_NF"].iloc[0]
    assert bool(coa["present"]) is True
    assert int(coa["n"]) == 4
    assert int(coa["capped_high"]) == 1
    assert int(coa["capped_low"]) == 1
    assert coa["winsor_mean"] < coa["raw_mean"]

    paper = pd.read_csv(paths["paper_csv"])
    appendix = pd.read_csv(paths["appendix_csv"])
    assert paper["Variable"].tolist() == ["Cost of attendance", "Headroom share"]
    assert "Rows capped" in paper.columns
    assert {"p1", "p99", "Lower cap", "Upper cap"} <= set(appendix.columns)
    assert paths["paper_docx"].stat().st_size > 0
    assert paths["appendix_docx"].stat().st_size > 0


def test_model_plan_audit_reports_complete_case_counts(tmp_path: Path) -> None:
    panel_dir = tmp_path / "analysis_panel"
    panel_path = panel_dir / "public_private_nonprofit" / "analysis.parquet"
    config_path = tmp_path / "model_specifications.csv"
    output_dir = tmp_path / "model_plan"
    rows = [
        {
            "year": 2009,
            "UNITID": 1,
            "IGRNT_PER_FTFT_COHORT": 100.0,
            "HEADROOM_MAIN": 10_000.0,
            "OPEN_ADMISSIONS_FLAG": False,
            "LN_SCFA1N": 4.0,
            "SCFA1N": 50,
        },
        {
            "year": 2010,
            "UNITID": 1,
            "IGRNT_PER_FTFT_COHORT": 110.0,
            "HEADROOM_MAIN": 11_000.0,
            "OPEN_ADMISSIONS_FLAG": False,
            "LN_SCFA1N": 4.1,
            "SCFA1N": 55,
        },
        {
            "year": 2010,
            "UNITID": 2,
            "IGRNT_PER_FTFT_COHORT": None,
            "HEADROOM_MAIN": 12_000.0,
            "OPEN_ADMISSIONS_FLAG": True,
            "LN_SCFA1N": 4.2,
            "SCFA1N": 60,
        },
    ]
    write_parquet(panel_path, rows)
    config_path.write_text(
        "\n".join(
            [
                "model_id,stage,sample_scope,analysis_panel,dependent_variable,focal_variable,controls,weight_variable,fixed_effects,cluster_level,role,notes",
                "test_model,baseline_fe,public_private_nonprofit,analysis.parquet,IGRNT_PER_FTFT_COHORT,HEADROOM_MAIN,OPEN_ADMISSIONS_FLAG;LN_SCFA1N,SCFA1N,UNITID;year,UNITID,main,Test model.",
                "missing_var_model,baseline_fe,public_private_nonprofit,analysis.parquet,NOT_PRESENT,HEADROOM_MAIN,OPEN_ADMISSIONS_FLAG,,UNITID;year,UNITID,check,Missing variable check.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    paths = audit_model_plan(panel_dir=panel_dir, output_dir=output_dir, config=config_path)

    coverage = pd.read_csv(paths["coverage"])
    main = coverage[coverage["model_id"] == "test_model"].iloc[0]
    assert bool(main["panel_exists"]) is True
    assert pd.isna(main["missing_variables"]) or main["missing_variables"] == ""
    assert int(main["complete_case_rows"]) == 2
    assert int(main["complete_case_institutions"]) == 1

    missing = coverage[coverage["model_id"] == "missing_var_model"].iloc[0]
    assert missing["missing_variables"] == "NOT_PRESENT"
    assert int(missing["complete_case_rows"]) == 0


def test_headroom_measure_audit_reports_weighted_coverage_and_share_flags(tmp_path: Path) -> None:
    panel_dir = tmp_path / "analysis_panel"
    panel_path = panel_dir / "public_private_nonprofit" / "analysis_panel_coa_headroom_2009_2023_public_private_nonprofit.parquet"
    output_dir = tmp_path / "headroom_measures"
    rows = [
        {
            "year": 2009,
            "UNITID": 1,
            "SECTOR": 1,
            "COA_MAIN": 20_000.0,
            "HEADROOM_MAIN": 10_000.0,
            "HEADROOM_MAIN_SHARE_COA": 0.50,
            "HEADROOM_MAIN_SHARE_TUITION": 1.00,
            "LN_HEADROOM_MAIN": 9.21,
            "CHG2AY0": 10_000.0,
            "CHG4AY0": 1_000.0,
            "CHG7AY0": 7_000.0,
            "CHG8AY0": 2_000.0,
            "SCFA1N": 100,
        },
        {
            "year": 2009,
            "UNITID": 2,
            "SECTOR": 2,
            "COA_MAIN": 30_000.0,
            "HEADROOM_MAIN": 20_000.0,
            "HEADROOM_MAIN_SHARE_COA": 1.20,
            "HEADROOM_MAIN_SHARE_TUITION": 2.00,
            "LN_HEADROOM_MAIN": 9.90,
            "CHG2AY0": 10_000.0,
            "CHG4AY0": 2_000.0,
            "CHG7AY0": 14_000.0,
            "CHG8AY0": 4_000.0,
            "SCFA1N": 300,
        },
    ]
    write_parquet(panel_path, rows)

    specs = load_headroom_specs()
    assert "HEADROOM_MAIN" in {spec.varname for spec in specs}

    paths = audit_headroom_measures(panel_dir=panel_dir, output_dir=output_dir)

    coverage = pd.read_csv(paths["coverage"])
    main = coverage[coverage["varname"] == "HEADROOM_MAIN"].iloc[0]
    assert bool(main["present"]) is True
    assert int(main["nonnull_rows"]) == 2
    assert main["mean"] == pytest.approx(15_000.0)
    assert main["ftft_weighted_mean"] == pytest.approx(17_500.0)

    share = coverage[coverage["varname"] == "HEADROOM_MAIN_SHARE_COA"].iloc[0]
    assert int(share["invalid_share_count"]) == 1

    tuition_ratio = coverage[coverage["varname"] == "HEADROOM_MAIN_SHARE_TUITION"].iloc[0]
    assert int(tuition_ratio["invalid_share_count"]) == 0

    by_sector_year = pd.read_csv(paths["by_sector_year"])
    assert {"public", "private_nonprofit"} <= set(by_sector_year["sector"])


def test_descriptive_decomposition_pairs_same_institutions_and_components(tmp_path: Path) -> None:
    panel_dir = tmp_path / "analysis_panel"
    panel_path = panel_dir / "public_private_nonprofit" / "analysis_panel_coa_headroom_2009_2010_public_private_nonprofit.parquet"
    output_dir = tmp_path / "descriptive_decomposition"
    rows = [
        {
            "year": 2009,
            "UNITID": 1,
            "SECTOR": 1,
            "SCFA1N": 100,
            "CHG2AY0": 10_000.0,
            "CHG4AY0": 1_000.0,
            "CHG7AY0": 7_000.0,
            "CHG8AY0": 2_000.0,
            "COA_MAIN": 20_000.0,
            "HEADROOM_MAIN": 10_000.0,
            "HEADROOM_MAIN_SHARE_COA": 0.50,
            "HEADROOM_MAIN_SHARE_TUITION": 1.00,
            "IGRNT_PER_FTFT_COHORT": 100.0,
            "PGRNT_PER_FTFT_COHORT": 200.0,
        },
        {
            "year": 2010,
            "UNITID": 1,
            "SECTOR": 1,
            "SCFA1N": 100,
            "CHG2AY0": 10_500.0,
            "CHG4AY0": 1_100.0,
            "CHG7AY0": 8_000.0,
            "CHG8AY0": 2_400.0,
            "COA_MAIN": 22_000.0,
            "HEADROOM_MAIN": 11_500.0,
            "HEADROOM_MAIN_SHARE_COA": 11_500.0 / 22_000.0,
            "HEADROOM_MAIN_SHARE_TUITION": 11_500.0 / 10_500.0,
            "IGRNT_PER_FTFT_COHORT": 110.0,
            "PGRNT_PER_FTFT_COHORT": 210.0,
        },
        {
            "year": 2009,
            "UNITID": 2,
            "SECTOR": 2,
            "SCFA1N": 300,
            "CHG2AY0": 20_000.0,
            "CHG4AY0": 1_500.0,
            "CHG7AY0": 9_000.0,
            "CHG8AY0": 3_000.0,
            "COA_MAIN": 33_500.0,
            "HEADROOM_MAIN": 13_500.0,
            "HEADROOM_MAIN_SHARE_COA": 13_500.0 / 33_500.0,
            "HEADROOM_MAIN_SHARE_TUITION": 13_500.0 / 20_000.0,
            "IGRNT_PER_FTFT_COHORT": 300.0,
            "PGRNT_PER_FTFT_COHORT": 400.0,
        },
        {
            "year": 2010,
            "UNITID": 2,
            "SECTOR": 2,
            "SCFA1N": 300,
            "CHG2AY0": 22_000.0,
            "CHG4AY0": 1_600.0,
            "CHG7AY0": 9_300.0,
            "CHG8AY0": 3_300.0,
            "COA_MAIN": 36_200.0,
            "HEADROOM_MAIN": 14_200.0,
            "HEADROOM_MAIN_SHARE_COA": 14_200.0 / 36_200.0,
            "HEADROOM_MAIN_SHARE_TUITION": 14_200.0 / 22_000.0,
            "IGRNT_PER_FTFT_COHORT": 320.0,
            "PGRNT_PER_FTFT_COHORT": 420.0,
        },
    ]
    write_parquet(panel_path, rows)

    paths = build_descriptive_decomposition(panel_dir=panel_dir, output_dir=output_dir)

    trends = pd.read_csv(paths["trends"])
    public_2010 = trends[
        trends["scope"].eq("public_private_nonprofit")
        & trends["sector"].eq("public")
        & trends["year"].eq(2010)
        & trends["varname"].eq("COA_MAIN")
    ].iloc[0]
    assert int(public_2010["nonnull_rows"]) == 1
    assert public_2010["mean"] == pytest.approx(22_000.0)

    adjacent = pd.read_csv(paths["adjacent_changes"])
    public = adjacent[adjacent["sector"].eq("public")].iloc[0]
    assert int(public["paired_institutions"]) == 1
    assert public["mean_coa_main_change"] == pytest.approx(2_000.0)
    assert public["mean_headroom_main_change"] == pytest.approx(1_500.0)
    assert public["mean_tuition_fees_change"] == pytest.approx(500.0)
    assert public["mean_books_supplies_change"] == pytest.approx(100.0)
    assert public["mean_off_nf_room_board_change"] == pytest.approx(1_000.0)
    assert public["mean_off_nf_other_expenses_change"] == pytest.approx(400.0)
    assert public["mean_coa_change_minus_component_sum"] == pytest.approx(0.0)
    assert public["mean_headroom_change_minus_allowance_sum"] == pytest.approx(0.0)

    all_rows = adjacent[adjacent["sector"].eq("all")].iloc[0]
    assert int(all_rows["paired_institutions"]) == 2
    assert all_rows["ftft_weighted_coa_main_change"] == pytest.approx((2_000.0 * 100 + 2_700.0 * 300) / 400)


def test_model_sample_builder_materializes_complete_case_samples(tmp_path: Path) -> None:
    panel_dir = tmp_path / "analysis_panel"
    panel_path = panel_dir / "public_private_nonprofit" / "analysis.parquet"
    config_path = tmp_path / "model_specifications.csv"
    output_dir = tmp_path / "model_samples"
    rows = [
        {
            "year": 2009,
            "UNITID": 1,
            "SECTOR": 1,
            "CONTROL": 1,
            "STABBR": "NV",
            "IGRNT_PER_FTFT_COHORT": 100.0,
            "HEADROOM_MAIN": 10_000.0,
            "OPEN_ADMISSIONS_FLAG": False,
            "LN_SCFA1N": 4.0,
            "SCFA1N": 50,
        },
        {
            "year": 2010,
            "UNITID": 1,
            "SECTOR": 1,
            "CONTROL": 1,
            "STABBR": "NV",
            "IGRNT_PER_FTFT_COHORT": 110.0,
            "HEADROOM_MAIN": 10_000.0,
            "OPEN_ADMISSIONS_FLAG": False,
            "LN_SCFA1N": 4.1,
            "SCFA1N": 55,
        },
        {
            "year": 2010,
            "UNITID": 2,
            "SECTOR": 2,
            "CONTROL": 2,
            "STABBR": "CA",
            "IGRNT_PER_FTFT_COHORT": 200.0,
            "HEADROOM_MAIN": 12_000.0,
            "OPEN_ADMISSIONS_FLAG": True,
            "LN_SCFA1N": 4.2,
            "SCFA1N": 0,
        },
        {
            "year": 2010,
            "UNITID": 3,
            "SECTOR": 2,
            "CONTROL": 2,
            "STABBR": "AZ",
            "IGRNT_PER_FTFT_COHORT": None,
            "HEADROOM_MAIN": 13_000.0,
            "OPEN_ADMISSIONS_FLAG": True,
            "LN_SCFA1N": 4.3,
            "SCFA1N": 60,
        },
    ]
    write_parquet(panel_path, rows)
    config_path.write_text(
        "\n".join(
            [
                "model_id,stage,sample_scope,analysis_panel,dependent_variable,focal_variable,controls,weight_variable,fixed_effects,cluster_level,role,notes",
                "test_model,weighted_fe,public_private_nonprofit,analysis.parquet,IGRNT_PER_FTFT_COHORT,HEADROOM_MAIN,OPEN_ADMISSIONS_FLAG;LN_SCFA1N,SCFA1N,UNITID;year,UNITID,main,Test sample.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    paths = build_model_samples(panel_dir=panel_dir, output_dir=output_dir, config=config_path)

    manifest = pd.read_csv(paths["manifest"])
    row = manifest.iloc[0]
    assert int(row["sample_rows"]) == 2
    assert int(row["sample_institutions"]) == 1
    assert int(row["singleton_institutions"]) == 0
    assert int(row["institutions_without_focal_within_variation"]) == 1
    assert int(row["nonpositive_weight_rows"]) == 0
    assert row["missing_variables"] == "" or pd.isna(row["missing_variables"])

    sample = pd.read_parquet(paths["sample_dir"] / "test_model.parquet")
    assert sample["UNITID"].tolist() == [1, 1]
    assert set(sample["model_id"]) == {"test_model"}

    missingness = pd.read_csv(paths["missingness"])
    outcome = missingness[missingness["varname"].eq("IGRNT_PER_FTFT_COHORT")].iloc[0]
    assert int(outcome["missing_rows"]) == 1
