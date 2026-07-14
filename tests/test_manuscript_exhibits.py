from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from coa_finaid_subs import manuscript_exhibits


def fake_fit(
    sample: pd.DataFrame,
    model_id: str,
    dependent_variable: str,
    focal_variable: str,
    controls: tuple[str, ...] = manuscript_exhibits.BASELINE_CONTROLS,
    weight_variable: str = "",
) -> tuple[pd.Series, dict[str, object]]:
    del dependent_variable, focal_variable, controls, weight_variable
    private = "private_nonprofit" in model_id
    estimate = 0.18 if private else -0.01
    coefficient = pd.Series(
        {
            "estimate": estimate,
            "std_error": 0.04 if private else 0.02,
            "p_value_normal": 0.001 if private else 0.62,
        }
    )
    diagnostics = {
        "estimation_rows": len(sample),
        "institutions": int(sample["UNITID"].nunique()),
    }
    return coefficient, diagnostics


def write_sector_panels(analysis_root: Path) -> None:
    for sector, code in (("public", 1), ("private_nonprofit", 2)):
        output = analysis_root / sector
        output.mkdir(parents=True)
        pd.DataFrame(
            {
                "UNITID": [code * 10 + 1, code * 10 + 1, code * 10 + 2],
                "year": [2021, 2022, 2022],
                "SECTOR": [code, code, code],
            }
        ).to_parquet(output / f"analysis_panel_coa_headroom_2009_2023_{sector}.parquet", index=False)


def write_robustness_samples(sample_dir: Path) -> None:
    sample_dir.mkdir(parents=True)
    files = {sample_file for _, sample_file, _, _ in manuscript_exhibits.ROBUSTNESS_CHECKS}
    sample = pd.DataFrame(
        {
            "UNITID": [11, 11, 21, 21, 22],
            "year": [2021, 2022, 2021, 2022, 2022],
            "SECTOR": [1, 1, 2, 2, 2],
        }
    )
    for sample_file in files:
        sample.to_parquet(sample_dir / sample_file, index=False)


def write_fmr_comparison(path: Path) -> None:
    path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "model_id": "public_inst_grant",
                "estimate_hud_fmr": -0.006,
                "std_error_hud_fmr": 0.014,
                "p_value_normal_hud_fmr": 0.67,
                "nobs_hud_fmr": 100,
                "clusters_hud_fmr": 10,
                "estimate_delta": -0.001,
            },
            {
                "model_id": "private_np_inst_grant",
                "estimate_hud_fmr": 0.170,
                "std_error_hud_fmr": 0.028,
                "p_value_normal_hud_fmr": 0.001,
                "nobs_hud_fmr": 200,
                "clusters_hud_fmr": 20,
                "estimate_delta": -0.004,
            },
        ]
    ).to_csv(path, index=False)


def test_sector_exhibit_builder_keeps_sector_split_and_selected_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analysis_root = tmp_path / "analysis_panel"
    sample_dir = tmp_path / "model_samples"
    fmr_path = tmp_path / "fmr" / "comparison.csv"
    output_dir = tmp_path / "sector_exhibits"
    write_sector_panels(analysis_root)
    write_robustness_samples(sample_dir)
    write_fmr_comparison(fmr_path)
    monkeypatch.setattr(manuscript_exhibits, "fit_transient_fe_model", fake_fit)

    paths = manuscript_exhibits.build_manuscript_exhibit_data(
        analysis_root=analysis_root,
        model_sample_dir=sample_dir,
        fmr_comparison=fmr_path,
        output_dir=output_dir,
    )

    aid = pd.read_csv(paths["aid_outcomes"])
    assert list(aid["outcome"]) == [outcome[0] for outcome in manuscript_exhibits.AID_OUTCOMES]
    assert aid["public_estimate"].eq(-0.01).all()
    assert aid["private_nonprofit_estimate"].eq(0.18).all()
    assert not any(column.startswith("pooled") for column in aid.columns)

    selected = pd.read_csv(paths["robustness_selected"])
    assert list(selected["check"]) == [
        "Baseline",
        "FTFT-weighted",
        "Selective-admissions sample",
        "HUD FMR local rent control",
    ]
    assert selected.loc[selected["check"].eq("HUD FMR local rent control"), "private_nonprofit_estimate"].iloc[0] == pytest.approx(0.170)

    full = pd.read_csv(paths["robustness_full"])
    assert len(full) == len(manuscript_exhibits.ROBUSTNESS_CHECKS) + 1
    assert set(selected["check"]).issubset(set(full["check"]))


def test_hud_fmr_record_fails_when_source_is_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError, match="build_fmr_control_estimates.py"):
        manuscript_exhibits.hud_fmr_robustness_record(missing)
