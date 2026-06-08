from __future__ import annotations

import argparse
import hashlib
import json
import math
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
CLASSIFICATION_VARS = (
    "PSET4FLG",
    "PSEFLAG",
    "SECTOR",
    "CONTROL",
    "ICLEVEL",
    "HLOFFER",
    "F2PELL",
    "F3PELL",
    "FIPS",
    "OBEREG",
    "LOCALE",
    "INSTSIZE",
    "CARNEGIE",
    "CCBASIC",
    "C18BASIC",
    "C21BASIC",
    "DEGGRANT",
    "UGOFFER",
    "GROFFER",
    "HBCU",
    "TRIBAL",
    "LANDGRNT",
    "HOSPITAL",
    "MEDICAL",
    "CALSYS",
    "RPTMTH",
    "OPENADMP",
    "ALLONCAM",
    "COHRTSTU",
    "FT_UG",
    "PT_UG",
    "FT_FTUG",
    "PT_FTUG",
    "DISTNCED",
)
COUNT_PERCENT_VARS = (
    "APPLCN",
    "ADMSSN",
    "ENRLT",
    "SATVR25",
    "SATVR75",
    "SATMT25",
    "SATMT75",
    "SATPCT",
    "ACTCM25",
    "ACTCM75",
    "ACTPCT",
    "SCUGRAD",
    "SCUGFFN",
    "SCUGFFP",
    "SCFA2",
    "SCFA1N",
    "SCFA1P",
    "ANYAIDN",
    "ANYAIDP",
)
NET_PRICE_VARS = (
    "NPIST0",
    "NPIST1",
    "NPIST2",
    "NPGRN0",
    "NPGRN1",
    "NPGRN2",
    "NPT410",
    "NPT420",
    "NPT430",
    "NPT440",
    "NPT450",
)
CORE_MONEY_VARS = (
    "CHG1AY0",
    "CHG2AY0",
    "CHG3AY0",
    "CHG4AY0",
    "CHG5AY0",
    "CHG6AY0",
    "CHG7AY0",
    "CHG8AY0",
    "CHG9AY0",
    "TUITION1",
    "TUITION2",
    "TUITION3",
    "FEE1",
    "FEE2",
    "FEE3",
    "AGRNT_A",
    "AGRNT_T",
    "FGRNT_A",
    "FGRNT_T",
    "PGRNT_A",
    "PGRNT_T",
    "SGRNT_A",
    "SGRNT_T",
    "OFGRT_A",
    "OFGRT_T",
    "IGRNT_A",
    "IGRNT_T",
    "LOAN_A",
    "LOAN_T",
    "FLOAN_A",
    "FLOAN_T",
    "OLOAN_A",
    "OLOAN_T",
    "UAGRNTA",
    "UAGRNTT",
    "UFLOANA",
    "UFLOANT",
    "UPGRNTA",
    "UPGRNTT",
)
FINANCE_MONEY_VARS = (
    "F1A06",
    "F1B01",
    "F1B09",
    "F1B10",
    "F1B11",
    "F1B12",
    "F1B13",
    "F1B14",
    "F1B15",
    "F1D01",
    "F1D02",
    "F1H01",
    "F1C011",
    "F1C051",
    "F1C061",
    "F1C071",
    "F1C191",
    "F2A02",
    "F2B01",
    "F2B02",
    "F2D01",
    "F2H01",
    "F2E011",
    "F2E041",
    "F2E051",
    "F2E061",
    "F2E131",
    "F3A01",
    "F3B01",
    "F3B02",
    "F3D01",
    "F3E07",
    "F3E011",
    "F3E03A1",
    "F3E03B1",
    "F3E03C1",
    "F3E071",
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


def row_sum_any(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    return df[columns].sum(axis=1, min_count=1)


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")
    return num / den.where(den != 0)


def safe_log(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    positive = s.where(s > 0)
    return positive.map(lambda value: math.log(value) if pd.notna(value) else pd.NA)


def sector_finance_value(
    df: pd.DataFrame,
    public_col: str | None = None,
    private_np_col: str | None = None,
    forprofit_col: str | None = None,
) -> pd.Series:
    result = pd.Series(pd.NA, index=df.index, dtype="Float64")
    if "CONTROL" not in df.columns:
        return result
    control = pd.to_numeric(df["CONTROL"], errors="coerce")
    for control_value, col in ((1, public_col), (2, private_np_col), (3, forprofit_col)):
        if col and col in df.columns:
            result = result.mask(control.eq(control_value), pd.to_numeric(df[col], errors="coerce"))
    return result


def add_ratio(out: pd.DataFrame, derived: dict[str, pd.Series], name: str, numerator: str, denominator: str) -> None:
    if numerator in out.columns and denominator in out.columns:
        derived[name] = safe_divide(out[numerator], out[denominator])


def add_constructs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric_inputs = CORE_MONEY_VARS + NET_PRICE_VARS + FINANCE_MONEY_VARS + COUNT_PERCENT_VARS
    add_numeric_columns(out, [col for col in numeric_inputs if col in out.columns])
    derived: dict[str, pd.Series] = {}

    def get_series(name: str) -> pd.Series:
        if name in derived:
            return derived[name]
        return out[name]

    construct_defs = {
        "COA_IN_DISTRICT": ["CHG1AY0", "CHG4AY0", "CHG7AY0", "CHG8AY0"],
        "COA_ON": ["CHG2AY0", "CHG4AY0", "CHG5AY0", "CHG6AY0"],
        "COA_OFF_NF": ["CHG2AY0", "CHG4AY0", "CHG7AY0", "CHG8AY0"],
        "COA_OFF_WF": ["CHG2AY0", "CHG4AY0", "CHG9AY0"],
        "HEADROOM_IN_DISTRICT": ["CHG4AY0", "CHG7AY0", "CHG8AY0"],
        "HEADROOM_ON": ["CHG4AY0", "CHG5AY0", "CHG6AY0"],
        "HEADROOM_OFF_NF": ["CHG4AY0", "CHG7AY0", "CHG8AY0"],
        "HEADROOM_OFF_WF": ["CHG4AY0", "CHG9AY0"],
    }
    for name, columns in construct_defs.items():
        if all(col in out.columns for col in columns):
            derived[name] = row_sum(out, columns)

    share_defs = {
        "HEADROOM_SHARE_IN_DISTRICT": ("HEADROOM_IN_DISTRICT", "COA_IN_DISTRICT"),
        "HEADROOM_SHARE_ON": ("HEADROOM_ON", "COA_ON"),
        "HEADROOM_SHARE_OFF_NF": ("HEADROOM_OFF_NF", "COA_OFF_NF"),
        "HEADROOM_SHARE_OFF_WF": ("HEADROOM_OFF_WF", "COA_OFF_WF"),
    }
    for name, (num, denom) in share_defs.items():
        if (num in out.columns or num in derived) and (denom in out.columns or denom in derived):
            numerator = get_series(num)
            denominator = get_series(denom)
            derived[name] = numerator / denominator.where(denominator != 0)

    for prefix in ("AGRNT", "FGRNT", "PGRNT", "SGRNT", "OFGRT", "IGRNT", "LOAN", "FLOAN", "OLOAN"):
        add_ratio(out, derived, f"{prefix}_PER_FTFT_COHORT", f"{prefix}_T", "SCFA1N")

    for prefix in ("UAGRNT", "UFLOAN", "UPGRNT"):
        add_ratio(out, derived, f"{prefix}_PER_UG", f"{prefix}T", "SCUGRAD")

    add_ratio(out, derived, "PELL_SHARE_OF_TOTAL_GRANT_FTFT", "PGRNT_T", "AGRNT_T")
    add_ratio(out, derived, "INST_GRANT_SHARE_OF_TOTAL_GRANT_FTFT", "IGRNT_T", "AGRNT_T")
    add_ratio(out, derived, "FED_GRANT_SHARE_OF_TOTAL_GRANT_FTFT", "FGRNT_T", "AGRNT_T")
    add_ratio(out, derived, "STATE_LOCAL_GRANT_SHARE_OF_TOTAL_GRANT_FTFT", "SGRNT_T", "AGRNT_T")
    add_ratio(out, derived, "OTHER_FED_GRANT_SHARE_OF_TOTAL_GRANT_FTFT", "OFGRT_T", "AGRNT_T")

    add_ratio(out, derived, "ADMIT_RATE", "ADMSSN", "APPLCN")
    add_ratio(out, derived, "YIELD_RATE", "ENRLT", "ADMSSN")
    if all(col in out.columns for col in ("SATVR25", "SATVR75", "SATMT25", "SATMT75")):
        derived["SAT_TOTAL_MIDPOINT"] = (out["SATVR25"] + out["SATVR75"] + out["SATMT25"] + out["SATMT75"]) / 2
    if all(col in out.columns for col in ("ACTCM25", "ACTCM75")):
        derived["ACT_COMPOSITE_MIDPOINT"] = (out["ACTCM25"] + out["ACTCM75"]) / 2

    finance_defs = {
        "FIN_TUITION_REVENUE": ("F1B01", "F2D01", "F3D01"),
        "FIN_TOTAL_REVENUE": ("F1D01", "F2B01", "F3B01"),
        "FIN_TOTAL_EXPENSES": ("F1D02", "F2B02", "F3B02"),
        "FIN_TOTAL_ASSETS": ("F1A06", "F2A02", "F3A01"),
        "FIN_ENDOWMENT_BEGIN": ("F1H01", "F2H01", None),
        "FIN_INSTRUCTION_EXPENSE": ("F1C011", "F2E011", "F3E011"),
        "FIN_ACADEMIC_SUPPORT_EXPENSE": ("F1C051", "F2E041", "F3E03A1"),
        "FIN_STUDENT_SERVICES_EXPENSE": ("F1C061", "F2E051", "F3E03B1"),
        "FIN_INSTITUTIONAL_SUPPORT_EXPENSE": ("F1C071", "F2E061", "F3E03C1"),
    }
    for name, (public_col, private_np_col, forprofit_col) in finance_defs.items():
        derived[name] = sector_finance_value(out, public_col, private_np_col, forprofit_col)

    public_appropriation_cols = [col for col in ("F1B11", "F1B12", "F1B14", "F1B15") if col in out.columns]
    if public_appropriation_cols and "CONTROL" in out.columns:
        public_total = row_sum_any(out, public_appropriation_cols)
        derived["FIN_STATE_LOCAL_APPROPS_PUBLIC"] = public_total.where(pd.to_numeric(out["CONTROL"], errors="coerce").eq(1))

    for source, target in (
        ("SCUGRAD", "LN_SCUGRAD"),
        ("SCFA1N", "LN_SCFA1N"),
        ("FIN_TOTAL_REVENUE", "LN_FIN_TOTAL_REVENUE"),
        ("FIN_TOTAL_EXPENSES", "LN_FIN_TOTAL_EXPENSES"),
        ("FIN_TOTAL_ASSETS", "LN_FIN_TOTAL_ASSETS"),
    ):
        if source in out.columns or source in derived:
            derived[target] = safe_log(get_series(source))

    for col in NET_PRICE_VARS:
        if col not in out.columns:
            continue
        flag_col = f"FLAG_NEGATIVE_{col}"
        clean_col = f"{col}_CLEAN"
        derived[flag_col] = out[col] < 0
        derived[clean_col] = out[col].mask(derived[flag_col])

    if derived:
        out = pd.concat([out, pd.DataFrame(derived, index=out.index)], axis=1)
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
    for col in [c for c in CORE_MONEY_VARS + NET_PRICE_VARS + FINANCE_MONEY_VARS if c in df.columns]:
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
        {
            "varname": "COA_IN_DISTRICT",
            "group": "derived_coa",
            "role": "in-district off-campus not-with-family total COA construct",
            "required": False,
        },
        {"varname": "COA_ON", "group": "derived_coa", "role": "on-campus total COA construct", "required": False},
        {"varname": "COA_OFF_NF", "group": "derived_coa", "role": "off-campus not-with-family total COA construct", "required": False},
        {"varname": "COA_OFF_WF", "group": "derived_coa", "role": "off-campus with-family total COA construct", "required": False},
        {
            "varname": "HEADROOM_IN_DISTRICT",
            "group": "derived_headroom",
            "role": "in-district non-tuition headroom",
            "required": False,
        },
        {"varname": "HEADROOM_ON", "group": "derived_headroom", "role": "on-campus non-tuition headroom", "required": False},
        {"varname": "HEADROOM_OFF_NF", "group": "derived_headroom", "role": "off-campus not-with-family non-tuition headroom", "required": False},
        {"varname": "HEADROOM_OFF_WF", "group": "derived_headroom", "role": "off-campus with-family non-tuition headroom", "required": False},
        {
            "varname": "HEADROOM_SHARE_IN_DISTRICT",
            "group": "derived_headroom",
            "role": "in-district non-tuition share",
            "required": False,
        },
        {"varname": "HEADROOM_SHARE_ON", "group": "derived_headroom", "role": "on-campus non-tuition share", "required": False},
        {"varname": "HEADROOM_SHARE_OFF_NF", "group": "derived_headroom", "role": "off-campus not-with-family non-tuition share", "required": False},
        {"varname": "HEADROOM_SHARE_OFF_WF", "group": "derived_headroom", "role": "off-campus with-family non-tuition share", "required": False},
        {"varname": "PELL_SHARE_OF_TOTAL_GRANT_FTFT", "group": "derived_aid", "role": "Pell share of total FTFT grant dollars", "required": False},
        {
            "varname": "INST_GRANT_SHARE_OF_TOTAL_GRANT_FTFT",
            "group": "derived_aid",
            "role": "institutional grant share of total FTFT grant dollars",
            "required": False,
        },
        {
            "varname": "FED_GRANT_SHARE_OF_TOTAL_GRANT_FTFT",
            "group": "derived_aid",
            "role": "federal grant share of total FTFT grant dollars",
            "required": False,
        },
        {
            "varname": "STATE_LOCAL_GRANT_SHARE_OF_TOTAL_GRANT_FTFT",
            "group": "derived_aid",
            "role": "state and local grant share of total FTFT grant dollars",
            "required": False,
        },
        {
            "varname": "OTHER_FED_GRANT_SHARE_OF_TOTAL_GRANT_FTFT",
            "group": "derived_aid",
            "role": "other federal grant share of total FTFT grant dollars",
            "required": False,
        },
        {"varname": "ADMIT_RATE", "group": "derived_admissions", "role": "admissions divided by applicants", "required": False},
        {"varname": "YIELD_RATE", "group": "derived_admissions", "role": "enrolled divided by admissions", "required": False},
        {
            "varname": "SAT_TOTAL_MIDPOINT",
            "group": "derived_admissions",
            "role": "SAT verbal plus math midpoint from 25th and 75th percentiles",
            "required": False,
        },
        {
            "varname": "ACT_COMPOSITE_MIDPOINT",
            "group": "derived_admissions",
            "role": "ACT composite midpoint from 25th and 75th percentiles",
            "required": False,
        },
        {
            "varname": "FIN_TUITION_REVENUE",
            "group": "derived_finance",
            "role": "sector-harmonized tuition revenue",
            "required": False,
        },
        {"varname": "FIN_TOTAL_REVENUE", "group": "derived_finance", "role": "sector-harmonized total revenue", "required": False},
        {"varname": "FIN_TOTAL_EXPENSES", "group": "derived_finance", "role": "sector-harmonized total expenses", "required": False},
        {"varname": "FIN_TOTAL_ASSETS", "group": "derived_finance", "role": "sector-harmonized total assets", "required": False},
        {
            "varname": "FIN_ENDOWMENT_BEGIN",
            "group": "derived_finance",
            "role": "sector-harmonized beginning endowment where reported",
            "required": False,
        },
        {
            "varname": "FIN_INSTRUCTION_EXPENSE",
            "group": "derived_finance",
            "role": "sector-harmonized instruction expense",
            "required": False,
        },
        {
            "varname": "FIN_ACADEMIC_SUPPORT_EXPENSE",
            "group": "derived_finance",
            "role": "sector-harmonized academic support expense",
            "required": False,
        },
        {
            "varname": "FIN_STUDENT_SERVICES_EXPENSE",
            "group": "derived_finance",
            "role": "sector-harmonized student services expense",
            "required": False,
        },
        {
            "varname": "FIN_INSTITUTIONAL_SUPPORT_EXPENSE",
            "group": "derived_finance",
            "role": "sector-harmonized institutional support expense",
            "required": False,
        },
        {
            "varname": "FIN_STATE_LOCAL_APPROPS_PUBLIC",
            "group": "derived_finance",
            "role": "public-sector state and local appropriations and grants",
            "required": False,
        },
        {"varname": "LN_SCUGRAD", "group": "derived_scale", "role": "log total undergraduate SFA cohort", "required": False},
        {"varname": "LN_SCFA1N", "group": "derived_scale", "role": "log FTFT SFA cohort count", "required": False},
        {"varname": "LN_FIN_TOTAL_REVENUE", "group": "derived_scale", "role": "log sector-harmonized total revenue", "required": False},
        {"varname": "LN_FIN_TOTAL_EXPENSES", "group": "derived_scale", "role": "log sector-harmonized total expenses", "required": False},
        {"varname": "LN_FIN_TOTAL_ASSETS", "group": "derived_scale", "role": "log sector-harmonized total assets", "required": False},
    ]
    for prefix, label in (
        ("AGRNT", "total grant"),
        ("FGRNT", "federal grant"),
        ("PGRNT", "Pell grant"),
        ("SGRNT", "state and local grant"),
        ("OFGRT", "other federal grant"),
        ("IGRNT", "institutional grant"),
        ("LOAN", "student loan"),
        ("FLOAN", "federal loan"),
        ("OLOAN", "other loan"),
    ):
        derived_specs.append(
            {
                "varname": f"{prefix}_PER_FTFT_COHORT",
                "group": "derived_aid",
                "role": f"{label} dollars per FTFT SFA cohort student",
                "required": False,
            }
        )
    for prefix, label in (("UAGRNT", "undergraduate grant"), ("UFLOAN", "undergraduate federal loan"), ("UPGRNT", "undergraduate Pell")):
        derived_specs.append(
            {
                "varname": f"{prefix}_PER_UG",
                "group": "derived_aid",
                "role": f"{label} dollars per undergraduate in SFA cohort",
                "required": False,
            }
        )
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
