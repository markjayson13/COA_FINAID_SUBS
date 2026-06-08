from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VARIABLE_CONFIG = REPO_ROOT / "config" / "analysis_variables.csv"
KEY_VARS = ("year", "UNITID")
CLASSIFICATION_VARS = ("PSET4FLG", "PSEFLAG", "SECTOR", "CONTROL", "ICLEVEL", "HLOFFER", "F2PELL", "F3PELL")
NET_PRICE_VARS = ("NPT410", "NPT420", "NPT430", "NPT440", "NPT450")
CORE_MONEY_VARS = (
    "CHG2AY0",
    "CHG3AY0",
    "CHG4AY0",
    "CHG5AY0",
    "CHG6AY0",
    "CHG7AY0",
    "CHG8AY0",
    "CHG9AY0",
    "AGRNT_A",
    "FGRNT_A",
    "FGRNT_T",
    "PGRNT_A",
    "PGRNT_T",
    "IGRNT_A",
    "IGRNT_T",
    "LOAN_A",
    "LOAN_T",
    "FLOAN_A",
    "FLOAN_T",
    "UAGRNTA",
    "UFLOANA",
    "UPGRNTA",
    "UPGRNTT",
)


@dataclass(frozen=True)
class VariableSpec:
    varname: str
    group: str
    role: str
    required: bool = False


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def load_variable_specs(path: Path = DEFAULT_VARIABLE_CONFIG) -> list[VariableSpec]:
    if not path.exists():
        raise FileNotFoundError(f"Variable config not found: {path}")
    df = pd.read_csv(path)
    required = {"varname", "group", "role", "required"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Variable config is missing columns: {', '.join(sorted(missing))}")
    specs: list[VariableSpec] = []
    seen: set[str] = set()
    for row in df.to_dict("records"):
        varname = str(row["varname"]).strip()
        if not varname:
            continue
        key = varname.upper()
        if key in seen:
            raise ValueError(f"Duplicate variable in config: {varname}")
        seen.add(key)
        specs.append(
            VariableSpec(
                varname=varname,
                group=str(row["group"]).strip(),
                role=str(row["role"]).strip(),
                required=parse_bool(row["required"]),
            )
        )
    return specs


def parse_years(spec: str) -> list[int]:
    if ":" in spec:
        start, end = spec.split(":", 1)
        return list(range(int(start), int(end) + 1))
    return [int(part.strip()) for part in spec.split(",") if part.strip()]


def parse_int_list(spec: str) -> list[int]:
    return [int(part.strip()) for part in spec.split(",") if part.strip()]


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def default_input_panel() -> Path | None:
    explicit = os.environ.get("IPEDS_ANALYSIS_PANEL")
    if explicit:
        return Path(explicit)
    root = os.environ.get("IPEDSDB_ROOT")
    if root:
        return Path(root) / "Panels" / "panel_clean_analysis_2004_2023.parquet"
    return None


def default_dictionary() -> Path | None:
    explicit = os.environ.get("IPEDS_DICTIONARY")
    if explicit:
        return Path(explicit)
    root = os.environ.get("IPEDSDB_ROOT")
    if root:
        return Path(root) / "Dictionary" / "dictionary_lake.parquet"
    return None


def resolve_columns(schema_names: Iterable[str], requested: Iterable[str]) -> tuple[list[str], list[str]]:
    name_map = {name.upper(): name for name in schema_names}
    resolved: list[str] = []
    missing: list[str] = []
    for name in requested:
        actual = name_map.get(name.upper())
        if actual is None:
            missing.append(name)
        else:
            resolved.append(actual)
    seen: set[str] = set()
    resolved = [col for col in resolved if not (col in seen or seen.add(col))]
    return resolved, missing


def require_columns(schema_names: Iterable[str], specs: list[VariableSpec]) -> None:
    _, missing = resolve_columns(schema_names, [spec.varname for spec in specs if spec.required])
    if missing:
        raise SystemExit(f"Missing required research columns: {', '.join(missing)}")


def first_nonempty(values: pd.Series) -> str:
    for value in values.dropna().astype(str):
        text = value.strip()
        if text:
            return text
    return ""


def read_dictionary_manifest(dictionary_path: Path, specs: list[VariableSpec], present_cols: set[str]) -> pd.DataFrame:
    spec_df = pd.DataFrame([spec.__dict__ for spec in specs])
    spec_df["var_upper"] = spec_df["varname"].str.upper()
    present_upper = {col.upper() for col in present_cols}

    if not dictionary_path.exists():
        spec_df["present_in_input"] = spec_df["var_upper"].isin(present_upper)
        spec_df["first_dictionary_year"] = pd.NA
        spec_df["last_dictionary_year"] = pd.NA
        spec_df["varTitle"] = ""
        spec_df["source_files"] = ""
        spec_df["access_tables"] = ""
        return spec_df.drop(columns=["var_upper"])

    dictionary = pd.read_parquet(dictionary_path)
    keep_cols = [
        col
        for col in ("year", "varname", "varTitle", "longDescription", "DataType", "source_file", "access_table_name")
        if col in dictionary.columns
    ]
    dictionary = dictionary[keep_cols].copy()
    dictionary["var_upper"] = dictionary["varname"].astype(str).str.upper()

    rows: list[dict[str, object]] = []
    for _, spec in spec_df.iterrows():
        sub = dictionary[dictionary["var_upper"] == spec["var_upper"]]
        row = spec.to_dict()
        row["present_in_input"] = str(spec["var_upper"]).upper() in present_upper
        if sub.empty:
            row["first_dictionary_year"] = pd.NA
            row["last_dictionary_year"] = pd.NA
            row["varTitle"] = ""
            row["source_files"] = ""
            row["access_tables"] = ""
        else:
            row["first_dictionary_year"] = int(pd.to_numeric(sub["year"], errors="coerce").min())
            row["last_dictionary_year"] = int(pd.to_numeric(sub["year"], errors="coerce").max())
            row["varTitle"] = first_nonempty(sub.get("varTitle", pd.Series(dtype=str)))
            row["source_files"] = "|".join(sorted({str(v) for v in sub.get("source_file", pd.Series(dtype=str)).dropna() if str(v)}))
            row["access_tables"] = "|".join(
                sorted({str(v) for v in sub.get("access_table_name", pd.Series(dtype=str)).dropna() if str(v)})[:20]
            )
        rows.append(row)
    return pd.DataFrame(rows).drop(columns=["var_upper"])


def add_numeric_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def row_sum(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    return df[columns].sum(axis=1, min_count=len(columns))


def add_constructs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    add_numeric_columns(out, [col for col in CORE_MONEY_VARS + NET_PRICE_VARS if col in out.columns])

    construct_defs = {
        "COA_ON": ["CHG2AY0", "CHG4AY0", "CHG5AY0", "CHG6AY0"],
        "COA_OFF_NF": ["CHG2AY0", "CHG4AY0", "CHG7AY0", "CHG8AY0"],
        "COA_OFF_WF": ["CHG2AY0", "CHG4AY0", "CHG9AY0"],
        "HEADROOM_ON": ["CHG4AY0", "CHG5AY0", "CHG6AY0"],
        "HEADROOM_OFF_NF": ["CHG4AY0", "CHG7AY0", "CHG8AY0"],
        "HEADROOM_OFF_WF": ["CHG4AY0", "CHG9AY0"],
    }
    for name, columns in construct_defs.items():
        if all(col in out.columns for col in columns):
            out[name] = row_sum(out, columns)

    share_defs = {
        "HEADROOM_SHARE_ON": ("HEADROOM_ON", "COA_ON"),
        "HEADROOM_SHARE_OFF_NF": ("HEADROOM_OFF_NF", "COA_OFF_NF"),
        "HEADROOM_SHARE_OFF_WF": ("HEADROOM_OFF_WF", "COA_OFF_WF"),
    }
    for name, (num, denom) in share_defs.items():
        if num in out.columns and denom in out.columns:
            out[name] = out[num] / out[denom].where(out[denom] != 0)

    for col in NET_PRICE_VARS:
        if col not in out.columns:
            continue
        flag_col = f"FLAG_NEGATIVE_{col}"
        clean_col = f"{col}_CLEAN"
        out[flag_col] = out[col] < 0
        out[clean_col] = out[col].mask(out[flag_col])

    return out


def validate_panel_keys(df: pd.DataFrame) -> None:
    null_unitid = int(df["UNITID"].isna().sum())
    null_year = int(df["year"].isna().sum())
    if null_unitid or null_year:
        raise SystemExit(f"Panel key has nulls: UNITID={null_unitid}, year={null_year}")
    duplicate_count = int(df.duplicated(subset=["UNITID", "year"]).sum())
    if duplicate_count:
        raise SystemExit(f"Input panel has {duplicate_count} duplicate UNITID-year rows")


def validate_core_money_nonnegative(df: pd.DataFrame) -> None:
    negative_counts: dict[str, int] = {}
    for col in [c for c in CORE_MONEY_VARS if c in df.columns]:
        s = pd.to_numeric(df[col], errors="coerce")
        count = int((s < 0).sum())
        if count:
            negative_counts[col] = count
    if negative_counts:
        details = ", ".join(f"{col}={count}" for col, count in sorted(negative_counts.items()))
        raise SystemExit(f"Negative values in core money variables: {details}")


def sample_counts(df: pd.DataFrame, year_filtered: pd.DataFrame, analysis: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "sample": "input_all_rows",
            "rows": len(df),
            "unitids": df["UNITID"].nunique(dropna=True),
            "min_year": int(df["year"].min()) if not df.empty else pd.NA,
            "max_year": int(df["year"].max()) if not df.empty else pd.NA,
        },
        {
            "sample": "year_window",
            "rows": len(year_filtered),
            "unitids": year_filtered["UNITID"].nunique(dropna=True),
            "min_year": int(year_filtered["year"].min()) if not year_filtered.empty else pd.NA,
            "max_year": int(year_filtered["year"].max()) if not year_filtered.empty else pd.NA,
        },
        {
            "sample": "primary_four_year_titleiv",
            "rows": len(analysis),
            "unitids": analysis["UNITID"].nunique(dropna=True),
            "min_year": int(analysis["year"].min()) if not analysis.empty else pd.NA,
            "max_year": int(analysis["year"].max()) if not analysis.empty else pd.NA,
        },
    ]
    return pd.DataFrame(rows)


def missingness_by_year(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if df.empty:
        return pd.DataFrame(columns=["year", "varname", "rows", "nonnull", "missing", "missing_share"])
    for year, group in df.groupby("year", dropna=False):
        for col in df.columns:
            missing = int(group[col].isna().sum())
            rows.append(
                {
                    "year": year,
                    "varname": col,
                    "rows": len(group),
                    "nonnull": int(group[col].notna().sum()),
                    "missing": missing,
                    "missing_share": missing / len(group) if len(group) else pd.NA,
                }
            )
    return pd.DataFrame(rows)


def value_sanity(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for col in [c for c in CORE_MONEY_VARS + NET_PRICE_VARS if c in df.columns]:
        s = pd.to_numeric(df[col], errors="coerce")
        rows.append(
            {
                "varname": col,
                "nonnull": int(s.notna().sum()),
                "min": None if s.dropna().empty else float(s.min()),
                "median": None if s.dropna().empty else float(s.median()),
                "max": None if s.dropna().empty else float(s.max()),
                "negative_count": int((s < 0).sum()),
                "zero_count": int((s == 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def derived_manifest_rows() -> pd.DataFrame:
    derived_specs = [
        {"varname": "COA_ON", "group": "derived_coa", "role": "on-campus total COA construct", "required": False},
        {"varname": "COA_OFF_NF", "group": "derived_coa", "role": "off-campus not-with-family total COA construct", "required": False},
        {"varname": "COA_OFF_WF", "group": "derived_coa", "role": "off-campus with-family total COA construct", "required": False},
        {"varname": "HEADROOM_ON", "group": "derived_headroom", "role": "on-campus non-tuition headroom", "required": False},
        {"varname": "HEADROOM_OFF_NF", "group": "derived_headroom", "role": "off-campus not-with-family non-tuition headroom", "required": False},
        {"varname": "HEADROOM_OFF_WF", "group": "derived_headroom", "role": "off-campus with-family non-tuition headroom", "required": False},
        {"varname": "HEADROOM_SHARE_ON", "group": "derived_headroom", "role": "on-campus non-tuition share", "required": False},
        {"varname": "HEADROOM_SHARE_OFF_NF", "group": "derived_headroom", "role": "off-campus not-with-family non-tuition share", "required": False},
        {"varname": "HEADROOM_SHARE_OFF_WF", "group": "derived_headroom", "role": "off-campus with-family non-tuition share", "required": False},
    ]
    for col in NET_PRICE_VARS:
        derived_specs.extend(
            [
                {"varname": f"FLAG_NEGATIVE_{col}", "group": "quality_flag", "role": f"negative raw {col} flag", "required": False},
                {"varname": f"{col}_CLEAN", "group": "cleaned_net_price", "role": f"{col} with negative values set null", "required": False},
            ]
        )
    derived = pd.DataFrame(derived_specs)
    derived["present_in_input"] = False
    derived["first_dictionary_year"] = pd.NA
    derived["last_dictionary_year"] = pd.NA
    derived["varTitle"] = ""
    derived["source_files"] = "derived"
    derived["access_tables"] = ""
    return derived


def prepare_analysis_panel(
    input_panel: Path,
    dictionary: Path,
    output_dir: Path,
    variable_config: Path = DEFAULT_VARIABLE_CONFIG,
    years_spec: str = "2009:2023",
    sectors_spec: str = "1,2,3",
    title_iv_flag: int = 1,
) -> dict[str, object]:
    if not input_panel.exists():
        raise SystemExit(f"Input panel does not exist: {input_panel}")
    specs = load_variable_specs(variable_config)
    years = parse_years(years_spec)
    sectors = parse_int_list(sectors_spec)
    output_dir.mkdir(parents=True, exist_ok=True)

    schema_cols = pq.read_schema(input_panel).names
    require_columns(schema_cols, specs)
    requested_cols, missing_requested = resolve_columns(schema_cols, [spec.varname for spec in specs])

    df = pd.read_parquet(input_panel, columns=requested_cols)
    validate_panel_keys(df)
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    add_numeric_columns(df, [col for col in CLASSIFICATION_VARS if col in df.columns])

    year_filtered = df[df["year"].isin(years)].copy()
    sample_mask = (year_filtered["PSET4FLG"] == title_iv_flag) & (year_filtered["SECTOR"].isin(sectors))
    analysis = year_filtered.loc[sample_mask].copy()
    analysis = add_constructs(analysis)
    validate_core_money_nonnegative(analysis)

    year_label = f"{min(years)}_{max(years)}" if years else "all_years"
    analysis_path = output_dir / f"analysis_panel_coa_headroom_{year_label}.parquet"
    manifest_path = output_dir / "analysis_variable_manifest.csv"
    sample_counts_path = output_dir / "analysis_sample_counts.csv"
    missingness_path = output_dir / "analysis_missingness_by_year.csv"
    value_sanity_path = output_dir / "analysis_value_sanity.csv"
    summary_path = output_dir / "analysis_build_summary.json"

    analysis.to_parquet(analysis_path, index=False)
    manifest = read_dictionary_manifest(dictionary, specs, set(schema_cols))
    pd.concat([manifest, derived_manifest_rows()], ignore_index=True).to_csv(manifest_path, index=False)
    sample_counts(df, year_filtered, analysis).to_csv(sample_counts_path, index=False)
    missingness_by_year(analysis).to_csv(missingness_path, index=False)
    value_sanity(analysis).to_csv(value_sanity_path, index=False)

    negative_net_price_counts = {
        col: int((pd.to_numeric(analysis[col], errors="coerce") < 0).sum())
        for col in NET_PRICE_VARS
        if col in analysis.columns
    }
    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_panel": str(input_panel),
        "input_panel_sha256": sha256_file(input_panel),
        "dictionary": str(dictionary),
        "dictionary_sha256": sha256_file(dictionary) if dictionary.exists() else None,
        "variable_config": str(variable_config),
        "variable_config_sha256": sha256_file(variable_config),
        "output_panel": str(analysis_path),
        "output_panel_sha256": sha256_file(analysis_path),
        "years": years,
        "sectors": sectors,
        "title_iv_flag": title_iv_flag,
        "input_rows": int(len(df)),
        "year_window_rows": int(len(year_filtered)),
        "analysis_rows": int(len(analysis)),
        "analysis_unitids": int(analysis["UNITID"].nunique(dropna=True)),
        "output_columns": int(len(analysis.columns)),
        "missing_optional_columns": missing_requested,
        "negative_net_price_counts": negative_net_price_counts,
        "artifacts": {
            "variable_manifest": str(manifest_path),
            "sample_counts": str(sample_counts_path),
            "missingness_by_year": str(missingness_path),
            "value_sanity": str(value_sanity_path),
        },
    }
    write_json(summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    default_panel = default_input_panel()
    default_dict = default_dictionary()
    p = argparse.ArgumentParser(description="Prepare the COA/headroom research analysis panel.")
    p.add_argument("--input-panel", default=str(default_panel) if default_panel else None, help="Input clean IPEDS panel parquet")
    p.add_argument("--dictionary", default=str(default_dict) if default_dict else None, help="Input dictionary_lake parquet")
    p.add_argument("--variable-config", default=str(DEFAULT_VARIABLE_CONFIG), help="Variable-selection CSV")
    p.add_argument("--output-dir", default="outputs/analysis_panel", help="Output directory")
    p.add_argument("--years", default="2009:2023", help='Analysis years, for example "2009:2023"')
    p.add_argument("--sectors", default="1,2,3", help="Comma-separated SECTOR codes")
    p.add_argument("--title-iv-flag", type=int, default=1, help="Required PSET4FLG value")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_panel:
        raise SystemExit("Provide --input-panel or set IPEDSDB_ROOT/IPEDS_ANALYSIS_PANEL")
    if not args.dictionary:
        raise SystemExit("Provide --dictionary or set IPEDSDB_ROOT/IPEDS_DICTIONARY")
    summary = prepare_analysis_panel(
        input_panel=Path(args.input_panel),
        dictionary=Path(args.dictionary),
        output_dir=Path(args.output_dir),
        variable_config=Path(args.variable_config),
        years_spec=args.years,
        sectors_spec=args.sectors,
        title_iv_flag=args.title_iv_flag,
    )
    print(
        "Wrote "
        f"{summary['output_panel']} rows={summary['analysis_rows']:,} "
        f"unitids={summary['analysis_unitids']:,} cols={summary['output_columns']:,}"
    )


if __name__ == "__main__":
    main()

