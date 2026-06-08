from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from coa_finaid_subs.prepare_analysis_panel import (
    DEFAULT_MAIN_SECTORS_SPEC,
    DEFAULT_VARIABLE_CONFIG,
    HARMONIZED_NET_PRICE_DEFS,
    derive_metadata_flags,
    load_variable_specs,
    metadata_code_summary,
    metadata_flag_summary,
    parse_int_list,
    parse_years,
    resolve_columns,
    sector_output_specs,
    sector_scope_label,
)


def year_coverage(sample: pd.DataFrame, column: str) -> tuple[int | None, int | None, float | None]:
    nonnull = sample[column].notna()
    by_year = sample.assign(_nonnull=nonnull).groupby("year")["_nonnull"].mean()
    years = by_year[by_year > 0]
    if years.empty:
        return None, None, None
    first = int(years.index.min())
    last = int(years.index.max())
    return first, last, float(by_year.loc[first:].min())


def variable_coverage(sample: pd.DataFrame, specs: list, missing_requested: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    missing_upper = {name.upper() for name in missing_requested}
    name_map = {name.upper(): name for name in sample.columns}
    for spec in specs:
        actual = name_map.get(spec.varname.upper())
        if actual is None:
            rows.append(
                {
                    "varname": spec.varname,
                    "group": spec.group,
                    "role": spec.role,
                    "required": spec.required,
                    "present_in_input": spec.varname.upper() not in missing_upper,
                    "nonnull": 0,
                    "coverage": 0.0,
                    "first_nonnull_year": None,
                    "last_nonnull_year": None,
                    "min_year_coverage_after_first": None,
                    "unique_nonnull": 0,
                }
            )
            continue
        first, last, min_after_first = year_coverage(sample, actual)
        nonnull = int(sample[actual].notna().sum())
        rows.append(
            {
                "varname": spec.varname,
                "group": spec.group,
                "role": spec.role,
                "required": spec.required,
                "present_in_input": True,
                "nonnull": nonnull,
                "coverage": nonnull / len(sample) if len(sample) else 0.0,
                "first_nonnull_year": first,
                "last_nonnull_year": last,
                "min_year_coverage_after_first": min_after_first,
                "unique_nonnull": int(sample[actual].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)


def group_coverage(coverage: pd.DataFrame) -> pd.DataFrame:
    return (
        coverage.groupby("group", dropna=False)
        .agg(
            variables=("varname", "count"),
            required_variables=("required", "sum"),
            mean_coverage=("coverage", "mean"),
            min_coverage=("coverage", "min"),
            missing_from_input=("present_in_input", lambda s: int((~s).sum())),
        )
        .reset_index()
        .sort_values("group")
    )


def complete_case_scenarios(sample: pd.DataFrame) -> pd.DataFrame:
    scenarios = {
        "primary_headroom_pell_institutional_avg": [
            "year",
            "UNITID",
            "PSET4FLG",
            "SECTOR",
            "CONTROL",
            "OPENADMP",
            "CHG2AY0",
            "CHG4AY0",
            "CHG7AY0",
            "CHG8AY0",
            "PGRNT_A",
            "IGRNT_A",
        ],
        "primary_plus_ftft_totals_and_denominator": [
            "year",
            "UNITID",
            "PSET4FLG",
            "SECTOR",
            "CONTROL",
            "OPENADMP",
            "CHG2AY0",
            "CHG4AY0",
            "CHG7AY0",
            "CHG8AY0",
            "PGRNT_T",
            "IGRNT_T",
            "AGRNT_T",
            "SCFA1N",
        ],
        "undergraduate_aid_family": [
            "year",
            "UNITID",
            "PSET4FLG",
            "SECTOR",
            "CONTROL",
            "SCUGRAD",
            "UPGRNTA",
            "UPGRNTT",
            "UAGRNTA",
            "UAGRNTT",
            "UFLOANA",
            "UFLOANT",
        ],
        "net_price_private_current_income_bands_npt_raw": [
            "year",
            "UNITID",
            "PSET4FLG",
            "SECTOR",
            "CONTROL",
            "NPT410",
            "NPT420",
            "NPT430",
            "NPT440",
            "NPT450",
        ],
    }
    name_map = {name.upper(): name for name in sample.columns}
    rows: list[dict[str, object]] = []
    for name, requested in scenarios.items():
        cols = [name_map[col.upper()] for col in requested if col.upper() in name_map]
        missing = [col for col in requested if col.upper() not in name_map]
        complete = sample.dropna(subset=cols) if cols else sample.iloc[0:0]
        rows.append(
            {
                "scenario": name,
                "rows": int(len(complete)),
                "unitids": int(complete["UNITID"].nunique(dropna=True)) if "UNITID" in complete else 0,
                "row_share": len(complete) / len(sample) if len(sample) else 0.0,
                "missing_columns": "|".join(missing),
            }
        )
    selective_base = ["year", "UNITID", "PSET4FLG", "SECTOR", "CONTROL", "OPENADMP", "APPLCN", "ADMSSN", "ENRLT"]
    selective_base_missing = [col for col in selective_base if col.upper() not in name_map]
    if selective_base_missing:
        selective_admit = sample.iloc[0:0]
        selective_index = sample.iloc[0:0]
    else:
        actual = {col: name_map[col.upper()] for col in selective_base}
        openadmp = pd.to_numeric(sample[actual["OPENADMP"]], errors="coerce")
        applicants = pd.to_numeric(sample[actual["APPLCN"]], errors="coerce")
        admissions = pd.to_numeric(sample[actual["ADMSSN"]], errors="coerce")
        enrolled = pd.to_numeric(sample[actual["ENRLT"]], errors="coerce")
        selective_mask = openadmp.eq(2)
        valid_admit = selective_mask & applicants.gt(0) & admissions.ge(0) & admissions.le(applicants)
        valid_yield = admissions.gt(0) & enrolled.ge(0) & enrolled.le(admissions)
        selective_admit = sample[valid_admit & valid_yield]
        sat_cols = ["SATVR25", "SATVR75", "SATMT25", "SATMT75"]
        act_cols = ["ACTCM25", "ACTCM75"]
        sat_missing = [col for col in sat_cols if col.upper() not in name_map]
        act_missing = [col for col in act_cols if col.upper() not in name_map]
        sat_ok = pd.Series(False, index=sample.index) if sat_missing else sample[[name_map[col.upper()] for col in sat_cols]].notna().all(axis=1)
        act_ok = pd.Series(False, index=sample.index) if act_missing else sample[[name_map[col.upper()] for col in act_cols]].notna().all(axis=1)
        selective_index = sample[valid_admit & (sat_ok | act_ok)]
    rows.append(
        {
            "scenario": "selective_admissions_robustness_admit_rate_yield",
            "rows": int(len(selective_admit)),
            "unitids": int(selective_admit["UNITID"].nunique(dropna=True)) if "UNITID" in selective_admit else 0,
            "row_share": len(selective_admit) / len(sample) if len(sample) else 0.0,
            "missing_columns": "|".join(selective_base_missing),
        }
    )
    index_missing_cols = selective_base_missing + [
        col for col in ["SATVR25", "SATVR75", "SATMT25", "SATMT75", "ACTCM25", "ACTCM75"] if col.upper() not in name_map
    ]
    rows.append(
        {
            "scenario": "selective_admissions_robustness_index_inputs",
            "rows": int(len(selective_index)),
            "unitids": int(selective_index["UNITID"].nunique(dropna=True)) if "UNITID" in selective_index else 0,
            "row_share": len(selective_index) / len(sample) if len(sample) else 0.0,
            "missing_columns": "|".join(index_missing_cols),
        }
    )
    finance_required = ["year", "UNITID", "PSET4FLG", "SECTOR", "CONTROL"]
    finance_cols = {
        1: ["F1D01", "F1D02", "F1A06"],
        2: ["F2B01", "F2B02", "F2A02"],
        3: ["F3B01", "F3B02", "F3A01"],
    }
    missing_finance_cols = [
        col
        for col in finance_required + [item for cols in finance_cols.values() for item in cols]
        if col.upper() not in name_map
    ]
    if missing_finance_cols or "CONTROL" not in name_map:
        finance_complete = sample.iloc[0:0]
    else:
        base_mask = sample[[name_map[col.upper()] for col in finance_required]].notna().all(axis=1)
        sector_mask = pd.Series(False, index=sample.index)
        control = pd.to_numeric(sample[name_map["CONTROL"]], errors="coerce")
        for control_value, cols in finance_cols.items():
            actual_cols = [name_map[col.upper()] for col in cols]
            sector_mask = sector_mask | (control.eq(control_value) & sample[actual_cols].notna().all(axis=1))
        finance_complete = sample[base_mask & sector_mask]
    rows.append(
        {
            "scenario": "finance_common_controls_sector_appropriate",
            "rows": int(len(finance_complete)),
            "unitids": int(finance_complete["UNITID"].nunique(dropna=True)) if "UNITID" in finance_complete else 0,
            "row_share": len(finance_complete) / len(sample) if len(sample) else 0.0,
            "missing_columns": "|".join(missing_finance_cols),
        }
    )
    net_price_required = ["year", "UNITID", "PSET4FLG", "SECTOR", "CONTROL"]
    net_price_cols = [col for pair in HARMONIZED_NET_PRICE_DEFS.values() for col in pair]
    missing_net_price_cols = [col for col in net_price_required + net_price_cols if col.upper() not in name_map]
    if missing_net_price_cols or "CONTROL" not in name_map:
        net_price_complete = sample.iloc[0:0]
    else:
        base_mask = sample[[name_map[col.upper()] for col in net_price_required]].notna().all(axis=1)
        control = pd.to_numeric(sample[name_map["CONTROL"]], errors="coerce")
        public_cols = [name_map[public_col.upper()] for public_col, _ in HARMONIZED_NET_PRICE_DEFS.values()]
        private_cols = [name_map[private_col.upper()] for _, private_col in HARMONIZED_NET_PRICE_DEFS.values()]
        public_mask = control.eq(1) & sample[public_cols].notna().all(axis=1)
        private_mask = control.isin([2, 3]) & sample[private_cols].notna().all(axis=1)
        net_price_complete = sample[base_mask & (public_mask | private_mask)]
    rows.append(
        {
            "scenario": "net_price_current_income_bands_sector_appropriate",
            "rows": int(len(net_price_complete)),
            "unitids": int(net_price_complete["UNITID"].nunique(dropna=True)) if "UNITID" in net_price_complete else 0,
            "row_share": len(net_price_complete) / len(sample) if len(sample) else 0.0,
            "missing_columns": "|".join(missing_net_price_cols),
        }
    )
    return pd.DataFrame(rows)


def audit_variable_config(
    input_panel: Path,
    output_dir: Path,
    variable_config: Path = DEFAULT_VARIABLE_CONFIG,
    years_spec: str = "2009:2023",
    sectors_spec: str = DEFAULT_MAIN_SECTORS_SPEC,
    title_iv_flag: int = 1,
) -> dict[str, Path]:
    specs = load_variable_specs(variable_config)
    years = parse_years(years_spec)
    sectors = parse_int_list(sectors_spec)
    sector_label = sector_scope_label(sectors)
    output_dir = output_dir / sector_label
    output_dir.mkdir(parents=True, exist_ok=True)

    schema_cols = pq.read_schema(input_panel).names
    requested_cols, missing_requested = resolve_columns(schema_cols, [spec.varname for spec in specs])
    df = pd.read_parquet(input_panel, columns=requested_cols)
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    for col in ("PSET4FLG", "SECTOR", "CONTROL"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    sample = df[df["year"].isin(years)].copy()
    sample = sample[(sample["PSET4FLG"] == title_iv_flag) & (sample["SECTOR"].isin(sectors))].copy()

    coverage = variable_coverage(sample, specs, missing_requested)
    groups = group_coverage(coverage)
    complete_cases = complete_case_scenarios(sample)
    metadata_flags = derive_metadata_flags(sample)
    metadata_sample = pd.concat([sample, metadata_flags], axis=1)
    metadata_summary = metadata_flag_summary(metadata_sample)
    metadata_codes = metadata_code_summary(sample)

    coverage_path = output_dir / "variable_config_coverage.csv"
    group_path = output_dir / "variable_group_coverage.csv"
    complete_path = output_dir / "complete_case_scenarios.csv"
    metadata_path = output_dir / "metadata_flag_summary.csv"
    metadata_code_path = output_dir / "metadata_code_summary.csv"
    coverage.to_csv(coverage_path, index=False)
    groups.to_csv(group_path, index=False)
    complete_cases.to_csv(complete_path, index=False)
    metadata_summary.to_csv(metadata_path, index=False)
    metadata_codes.to_csv(metadata_code_path, index=False)
    return {
        "coverage": coverage_path,
        "groups": group_path,
        "complete_cases": complete_path,
        "metadata_flags": metadata_path,
        "metadata_codes": metadata_code_path,
    }


def audit_variable_outputs(
    input_panel: Path,
    output_dir: Path,
    variable_config: Path = DEFAULT_VARIABLE_CONFIG,
    years_spec: str = "2009:2023",
    sectors_spec: str | None = None,
    title_iv_flag: int = 1,
    include_forprofit_diagnostic: bool = False,
) -> dict[str, dict[str, Path]]:
    outputs: dict[str, dict[str, Path]] = {}
    for sector_spec in sector_output_specs(sectors_spec, include_forprofit_diagnostic):
        paths = audit_variable_config(
            input_panel=input_panel,
            output_dir=output_dir,
            variable_config=variable_config,
            years_spec=years_spec,
            sectors_spec=sector_spec,
            title_iv_flag=title_iv_flag,
        )
        label = sector_scope_label(parse_int_list(sector_spec))
        outputs[label] = paths
    return outputs


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit the COA/headroom variable configuration against a clean IPEDS panel.")
    p.add_argument("--input-panel", required=True, help="Input clean IPEDS panel parquet")
    p.add_argument("--variable-config", default=str(DEFAULT_VARIABLE_CONFIG), help="Variable-selection CSV")
    p.add_argument("--output-dir", default="outputs/variable_audit", help="Output directory")
    p.add_argument("--years", default="2009:2023", help='Analysis years, for example "2009:2023"')
    p.add_argument(
        "--sectors",
        default=None,
        help="Comma-separated SECTOR codes. When omitted, writes baseline, public, and private nonprofit audits.",
    )
    p.add_argument(
        "--include-forprofit-diagnostic",
        action="store_true",
        help="Also write the private for-profit diagnostic audit.",
    )
    p.add_argument("--title-iv-flag", type=int, default=1, help="Required PSET4FLG value")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outputs = audit_variable_outputs(
        input_panel=Path(args.input_panel),
        output_dir=Path(args.output_dir),
        variable_config=Path(args.variable_config),
        years_spec=args.years,
        sectors_spec=args.sectors,
        title_iv_flag=args.title_iv_flag,
        include_forprofit_diagnostic=args.include_forprofit_diagnostic,
    )
    for sector_label, paths in outputs.items():
        print(f"Wrote {sector_label}: " + ", ".join(str(path) for path in paths.values()))


if __name__ == "__main__":
    main()
