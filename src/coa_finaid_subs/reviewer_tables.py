from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from coa_finaid_subs.model_plan import ModelSpec, load_model_specs


DEFAULT_OUTPUT_DIR = Path("outputs/reviewer_tables")


@dataclass(frozen=True)
class ModelBlock:
    block: str
    config: Path
    model_plan_dir: Path
    sample_dir: Path
    fixed_effects_dir: Path


DEFAULT_BLOCKS = (
    ModelBlock(
        block="baseline",
        config=Path("config/model_specifications.csv"),
        model_plan_dir=Path("outputs/model_plan"),
        sample_dir=Path("outputs/model_samples"),
        fixed_effects_dir=Path("outputs/fixed_effects"),
    ),
    ModelBlock(
        block="policy",
        config=Path("config/policy_exposure_model_specifications.csv"),
        model_plan_dir=Path("outputs/policy_model_plan"),
        sample_dir=Path("outputs/policy_model_samples"),
        fixed_effects_dir=Path("outputs/policy_fixed_effects"),
    ),
)


METADATA_GLOSSARY_ROWS = [
    {
        "field_family": "IMP_*",
        "plain_name": "imputation code",
        "how_used": "Retained as the raw IPEDS imputation/status code for each component where available.",
        "paper_boundary": "Use for row-exposure description and sensitivity checks; do not treat as a replacement for the raw IPEDS field.",
    },
    {
        "field_family": "REV_*",
        "plain_name": "revision flag",
        "how_used": "Rows are flagged when IPEDS reports a revised component value.",
        "paper_boundary": "Use to test whether results depend on revised records.",
    },
    {
        "field_family": "LOCK_*",
        "plain_name": "collection lock or status code",
        "how_used": "Retained as raw collection-status information where present.",
        "paper_boundary": "Report as metadata exposure; do not infer substantive institutional behavior from the code alone.",
    },
    {
        "field_family": "IDX_*",
        "plain_name": "parent-linked reporting identifier",
        "how_used": "Rows are flagged when a component reports a parent `UNITID` linkage.",
        "paper_boundary": "Use to detect component-level parent-child reporting exposure.",
    },
    {
        "field_family": "PRCH_*",
        "plain_name": "parent-child reporting code",
        "how_used": "Retained as raw parent-child reporting information from IPEDS where present.",
        "paper_boundary": "Use with upstream parent-child cleaning notes; do not collapse institutions in this repo.",
    },
    {
        "field_family": "PC*_F",
        "plain_name": "parent-child allocation factor",
        "how_used": "Rows are flagged when the allocation factor indicates parent-linked component reporting.",
        "paper_boundary": "Use as an exposure flag for sensitivity samples.",
    },
    {
        "field_family": "FLAG_IPEDS_ANY_METADATA_EXPOSURE",
        "plain_name": "any metadata exposure",
        "how_used": "Derived row flag equal to one when any retained imputation, revision, or parent-linked component exposure is detected.",
        "paper_boundary": "Use only as a conservative sensitivity filter; the raw metadata fields remain the source record.",
    },
]


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def spec_rows(block: ModelBlock) -> pd.DataFrame:
    specs = load_model_specs(block.config)
    rows = []
    for spec in specs:
        rows.append(
            {
                "block": block.block,
                "model_id": spec.model_id,
                "stage": spec.stage,
                "role": spec.role,
                "sample_scope": spec.sample_scope,
                "analysis_panel": spec.analysis_panel,
                "dependent_variable": spec.dependent_variable,
                "focal_variable": spec.focal_variable,
                "controls": ";".join(spec.controls),
                "weight_variable": spec.weight_variable,
                "fixed_effects": ";".join(spec.fixed_effects),
                "cluster_level": spec.cluster_level,
                "sample_filter": spec.sample_filter,
                "filter_notes": spec.filter_notes,
                "notes": spec.notes,
            }
        )
    return pd.DataFrame(rows)


def attrition_note(stage: str, role: str, sample_filter: str, dependent_variable: str) -> str:
    text = " ".join([stage, role, sample_filter, dependent_variable]).lower()
    if "net_price" in text:
        return "Net-price rows are thinner because net-price fields use a separate income-band reporting surface."
    if "selectivity" in text:
        return "Selective-admissions rows are thinner because open-admissions institutions are not required to report admit-rate and test-score fields."
    if sample_filter == "metadata_clean":
        return "Rows with derived IPEDS metadata exposure are excluded."
    if sample_filter == "no_suspect_aid_zero":
        return "Rows listed in the aid-zero suspect-row audit are excluded."
    if sample_filter == "balanced_full_window":
        return "Only institutions observed in every year of the 2009-2023 window are retained."
    if sample_filter == "min_years_10":
        return "Only institutions observed for at least ten years are retained."
    if "policy" in text or sample_filter.startswith("yrp_") or sample_filter == "placebo_2016_window":
        return "Rows are restricted to the policy window and require the configured pre-period exposure information."
    return "Rows are complete cases for the dependent variable, focal term, controls, fixed effects, cluster, and weight where applicable."


def top_missing_sources(missingness: pd.DataFrame, model_id: str, limit: int = 3) -> str:
    if missingness.empty or "model_id" not in missingness.columns:
        return ""
    subset = missingness[missingness["model_id"].eq(model_id)].copy()
    if subset.empty or "missing_rows" not in subset.columns:
        return ""
    subset["missing_rows"] = pd.to_numeric(subset["missing_rows"], errors="coerce").fillna(0)
    subset = subset[subset["missing_rows"].gt(0)].sort_values(["missing_rows", "varname"], ascending=[False, True])
    parts = []
    for row in subset.head(limit).to_dict("records"):
        parts.append(f"{row.get('varname')} ({int(row.get('missing_rows', 0))})")
    return "; ".join(parts)


def build_block_tables(block: ModelBlock) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = spec_rows(block)
    manifest = read_csv_or_empty(block.sample_dir / "model_sample_manifest.csv")
    missingness = read_csv_or_empty(block.sample_dir / "model_sample_variable_missingness.csv")
    diagnostics = read_csv_or_empty(block.fixed_effects_dir / "fixed_effects_model_diagnostics.csv")
    focal = read_csv_or_empty(block.fixed_effects_dir / "fixed_effects_focal_coefficients.csv")
    coverage = read_csv_or_empty(block.model_plan_dir / "model_specification_coverage.csv")

    cards = specs.copy()
    for frame, columns in (
        (
            manifest,
            [
                "model_id",
                "source_rows",
                "sample_rows",
                "sample_institutions",
                "singleton_institutions",
                "institutions_without_focal_within_variation",
            ],
        ),
        (
            diagnostics,
            [
                "model_id",
                "estimation_rows",
                "institutions",
                "clusters",
                "singleton_clusters",
                "within_r_squared",
                "rank_deficient",
                "absorbed_iterations",
                "absorbed_last_change",
            ],
        ),
        (
            focal,
            ["model_id", "term", "estimate", "std_error", "t_stat", "p_value_normal", "nobs"],
        ),
    ):
        available = [col for col in columns if col in frame.columns]
        if available:
            cards = cards.merge(frame[available], how="left", on="model_id")

    cards = cards.rename(
        columns={
            "term": "focal_term_reported",
            "estimate": "focal_estimate",
            "std_error": "focal_std_error",
            "t_stat": "focal_t_stat",
            "p_value_normal": "focal_p_value_normal",
            "nobs": "focal_nobs",
        }
    )
    cards["main_attrition_source"] = [
        top_missing_sources(missingness, model_id) for model_id in cards["model_id"].fillna("").astype(str)
    ]

    attrition = specs[
        ["block", "model_id", "stage", "role", "sample_scope", "dependent_variable", "focal_variable", "sample_filter"]
    ].copy()
    if not manifest.empty:
        manifest_cols = [
            col
            for col in [
                "model_id",
                "source_rows",
                "sample_rows",
                "sample_institutions",
                "singleton_institutions",
                "institutions_without_focal_within_variation",
            ]
            if col in manifest.columns
        ]
        attrition = attrition.merge(manifest[manifest_cols], how="left", on="model_id")
    if not diagnostics.empty:
        diag_cols = [col for col in ["model_id", "clusters", "rank_deficient", "within_r_squared"] if col in diagnostics.columns]
        attrition = attrition.merge(diagnostics[diag_cols], how="left", on="model_id")
    if not coverage.empty:
        coverage_cols = [col for col in ["model_id", "total_rows", "complete_case_rows"] if col in coverage.columns]
        attrition = attrition.merge(coverage[coverage_cols], how="left", on="model_id")

    source = pd.to_numeric(attrition.get("source_rows"), errors="coerce")
    sample = pd.to_numeric(attrition.get("sample_rows"), errors="coerce")
    attrition["rows_dropped"] = source - sample
    attrition["retained_share"] = sample / source.replace(0, pd.NA)
    attrition["main_attrition_source"] = [
        top_missing_sources(missingness, model_id) for model_id in attrition["model_id"].fillna("").astype(str)
    ]
    attrition["attrition_note"] = [
        attrition_note(row.stage, row.role, row.sample_filter if pd.notna(row.sample_filter) else "", row.dependent_variable)
        for row in attrition.itertuples(index=False)
    ]
    return cards, attrition


def build_reviewer_tables(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    blocks: tuple[ModelBlock, ...] = DEFAULT_BLOCKS,
) -> dict[str, Path]:
    card_frames: list[pd.DataFrame] = []
    attrition_frames: list[pd.DataFrame] = []
    for block in blocks:
        cards, attrition = build_block_tables(block)
        card_frames.append(cards)
        attrition_frames.append(attrition)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_cards = pd.concat(card_frames, ignore_index=True) if card_frames else pd.DataFrame()
    sample_attrition = pd.concat(attrition_frames, ignore_index=True) if attrition_frames else pd.DataFrame()
    metadata_glossary = pd.DataFrame(METADATA_GLOSSARY_ROWS)

    paths = {
        "model_cards": output_dir / "model_cards.csv",
        "sample_attrition": output_dir / "model_sample_attrition.csv",
        "metadata_glossary": output_dir / "metadata_flag_glossary.csv",
        "summary": output_dir / "reviewer_tables_summary.json",
    }
    model_cards.to_csv(paths["model_cards"], index=False)
    sample_attrition.to_csv(paths["sample_attrition"], index=False)
    metadata_glossary.to_csv(paths["metadata_glossary"], index=False)
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "blocks": [block.block for block in blocks],
        "model_cards": int(len(model_cards)),
        "sample_attrition_rows": int(len(sample_attrition)),
        "metadata_glossary_rows": int(len(metadata_glossary)),
        "outputs": {key: str(value) for key, value in paths.items() if key != "summary"},
    }
    paths["summary"].write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reviewer-facing model-card, attrition, and metadata tables.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = build_reviewer_tables(output_dir=args.output_dir)
    print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
