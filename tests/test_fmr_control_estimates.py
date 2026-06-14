from __future__ import annotations

from pathlib import Path

import pandas as pd

from coa_finaid_subs.fixed_effects import run_fixed_effects
from coa_finaid_subs.fmr_control_estimates import run_fmr_control_group


def test_run_fmr_control_group_writes_comparison(tmp_path: Path) -> None:
    config = tmp_path / "model_specifications.csv"
    config.write_text(
        "\n".join(
            [
                "model_id,stage,sample_scope,analysis_panel,dependent_variable,focal_variable,controls,weight_variable,fixed_effects,cluster_level,role,notes,sample_filter,filter_notes",
                "demo_model,test_scope,test_scope,demo.parquet,Y,X,C,,UNITID;year,UNITID,main,synthetic test,,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = []
    for unitid in range(1, 5):
        for year in range(2009, 2013):
            x = unitid * 10 + (year - 2008) * 3
            c = unitid + year - 2008
            rent = 6.0 + unitid * 0.08 + (year - 2009) * 0.05
            rows.append(
                {
                    "UNITID": unitid,
                    "year": year,
                    "Y": 1.5 * x + 0.7 * c + 0.2 * rent + unitid + year * 0.01,
                    "X": x,
                    "C": c,
                }
            )
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    pd.DataFrame(rows).to_parquet(sample_dir / "demo_model.parquet", index=False)

    original_dir = tmp_path / "original"
    run_fixed_effects(sample_dir=sample_dir, output_dir=original_dir, config=config)

    controls = pd.DataFrame(
        [
            {"UNITID": row["UNITID"], "year": row["year"], "ln_hud_fmr_2br": 6.0 + row["UNITID"] * 0.08 + (row["year"] - 2009) * 0.05}
            for row in rows
        ]
    )
    output_dir = tmp_path / "fmr"
    summary = run_fmr_control_group(
        config=config,
        sample_dir=sample_dir,
        original_focal=original_dir / "fixed_effects_focal_coefficients.csv",
        fmr_controls=controls,
        output_dir=output_dir,
        prefix="fixed_effects",
    )

    comparison = pd.read_csv(output_dir / "fixed_effects_hud_fmr_comparison.csv")
    diagnostics = pd.read_csv(output_dir / "fixed_effects_hud_fmr_diagnostics.csv")

    assert summary["models_estimated"] == 1
    assert summary["models_with_errors"] == 0
    assert comparison.loc[0, "model_id"] == "demo_model"
    assert "estimate_delta" in comparison.columns
    assert diagnostics.loc[0, "fmr_match_rate_in_model_sample"] == 1.0
    assert str(tmp_path) not in diagnostics.to_csv(index=False)
    summary_text = (output_dir / "fixed_effects_hud_fmr_comparison.csv").read_text(encoding="utf-8")
    assert str(tmp_path) not in summary_text
