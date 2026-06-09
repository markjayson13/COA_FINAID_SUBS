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
DEFAULT_MAIN_SECTORS_SPEC = "1,2"
DEFAULT_SECTOR_OUTPUT_SPECS = (DEFAULT_MAIN_SECTORS_SPEC, "1", "2")
FORPROFIT_DIAGNOSTIC_SECTORS_SPEC = "3"
KEY_VARS = ("year", "UNITID")
SECTOR_LABELS = {
    1: "public",
    2: "private_nonprofit",
    3: "private_forprofit",
}
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
    "NPIS410",
    "NPIS420",
    "NPIS430",
    "NPIS440",
    "NPIS450",
    "NPT410",
    "NPT420",
    "NPT430",
    "NPT440",
    "NPT450",
)
HARMONIZED_NET_PRICE_DEFS = {
    "NET_PRICE_0_30000": ("NPIS410", "NPT410"),
    "NET_PRICE_30001_48000": ("NPIS420", "NPT420"),
    "NET_PRICE_48001_75000": ("NPIS430", "NPT430"),
    "NET_PRICE_75001_110000": ("NPIS440", "NPT440"),
    "NET_PRICE_OVER_110000": ("NPIS450", "NPT450"),
}
HARMONIZED_NET_PRICE_VARS = tuple(HARMONIZED_NET_PRICE_DEFS)
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
METADATA_STATUS_VARS = (
    "IMP_IC",
    "IMP_SFA",
    "IMP_F",
    "IMP_EF",
    "IMP_E12",
    "IMP_ADM",
    "LOCK_IC",
    "LOCK_SFA",
    "LOCK_F",
    "LOCK_EF",
    "LOCK_E12",
    "LOCK_ADM",
    "REV_IC",
    "REV_SFA",
    "REV_F",
    "REV_EF",
    "REV_E12",
    "REV_ADM",
    "IDX_SFA",
    "IDX_F",
    "IDX_EF",
    "IDX_E12",
    "IDX_ADM",
    "PRCH_SFA",
    "PRCH_F",
    "PRCH_EF",
    "PRCH_E12",
    "PRCH_ADM",
    "PCSFA_F",
    "PCF_F",
    "PCF_F_RV",
    "PCEF_F",
    "PCE12_F",
    "PCADM_F",
)
METADATA_CODE_SUMMARY_VARS = tuple(
    col for col in METADATA_STATUS_VARS if col.startswith(("IMP_", "LOCK_", "REV_", "PRCH_"))
)
METADATA_COMPONENTS = {
    "IC": {"imp": "IMP_IC", "lock": "LOCK_IC", "rev": "REV_IC"},
    "SFA": {"imp": "IMP_SFA", "lock": "LOCK_SFA", "rev": "REV_SFA", "idx": "IDX_SFA", "prch": "PRCH_SFA", "pc": "PCSFA_F"},
    "F": {"imp": "IMP_F", "lock": "LOCK_F", "rev": "REV_F", "idx": "IDX_F", "prch": "PRCH_F", "pc": "PCF_F", "pc_rev": "PCF_F_RV"},
    "EF": {"imp": "IMP_EF", "lock": "LOCK_EF", "rev": "REV_EF", "idx": "IDX_EF", "prch": "PRCH_EF", "pc": "PCEF_F"},
    "E12": {"imp": "IMP_E12", "lock": "LOCK_E12", "rev": "REV_E12", "idx": "IDX_E12", "prch": "PRCH_E12", "pc": "PCE12_F"},
    "ADM": {"imp": "IMP_ADM", "lock": "LOCK_ADM", "rev": "REV_ADM", "idx": "IDX_ADM", "prch": "PRCH_ADM", "pc": "PCADM_F"},
}
AID_ZERO_AUDIT_SPECS = (
    ("ftft", "AGRNT", "total grant", "AGRNT_A", "AGRNT_N", "AGRNT_P", "AGRNT_T", "SCFA1N"),
    ("ftft", "FGRNT", "federal grant", "FGRNT_A", "FGRNT_N", "FGRNT_P", "FGRNT_T", "SCFA1N"),
    ("ftft", "PGRNT", "Pell grant", "PGRNT_A", "PGRNT_N", "PGRNT_P", "PGRNT_T", "SCFA1N"),
    ("ftft", "SGRNT", "state and local grant", "SGRNT_A", "SGRNT_N", "SGRNT_P", "SGRNT_T", "SCFA1N"),
    ("ftft", "OFGRT", "other federal grant", "OFGRT_A", "OFGRT_N", "OFGRT_P", "OFGRT_T", "SCFA1N"),
    ("ftft", "IGRNT", "institutional grant", "IGRNT_A", "IGRNT_N", "IGRNT_P", "IGRNT_T", "SCFA1N"),
    ("ftft", "LOAN", "student loan", "LOAN_A", "LOAN_N", "LOAN_P", "LOAN_T", "SCFA1N"),
    ("ftft", "FLOAN", "federal loan", "FLOAN_A", "FLOAN_N", "FLOAN_P", "FLOAN_T", "SCFA1N"),
    ("ftft", "OLOAN", "other loan", "OLOAN_A", "OLOAN_N", "OLOAN_P", "OLOAN_T", "SCFA1N"),
    ("undergraduate", "UAGRNT", "undergraduate grant", "UAGRNTA", "UAGRNTN", "UAGRNTP", "UAGRNTT", "SCUGRAD"),
    ("undergraduate", "UFLOAN", "undergraduate federal loan", "UFLOANA", "UFLOANN", "UFLOANP", "UFLOANT", "SCUGRAD"),
    ("undergraduate", "UPGRNT", "undergraduate Pell", "UPGRNTA", "UPGRNTN", "UPGRNTP", "UPGRNTT", "SCUGRAD"),
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


def normalize_sector_spec(spec: str) -> str:
    return ",".join(str(sector) for sector in sorted(set(parse_int_list(spec))))


def sector_output_specs(sectors_spec: str | None = None, include_forprofit_diagnostic: bool = False) -> list[str]:
    specs = [sectors_spec] if sectors_spec else list(DEFAULT_SECTOR_OUTPUT_SPECS)
    if include_forprofit_diagnostic:
        specs.append(FORPROFIT_DIAGNOSTIC_SECTORS_SPEC)

    normalized: list[str] = []
    seen: set[str] = set()
    for spec in specs:
        if spec is None:
            continue
        key = normalize_sector_spec(spec)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def sector_scope_label(sectors: list[int]) -> str:
    normalized = sorted(set(sectors))
    if normalized == [1, 2]:
        return "public_private_nonprofit"
    if normalized == [1]:
        return "public"
    if normalized == [2]:
        return "private_nonprofit"
    if normalized == [3]:
        return "private_forprofit_diagnostic"
    if normalized == [1, 2, 3]:
        return "all_four_year_titleiv"
    return "sectors_" + "_".join(str(sector) for sector in normalized)


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


def numeric_or_na(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="Float64")
    return pd.to_numeric(df[column], errors="coerce")


def derive_metadata_flags(df: pd.DataFrame) -> pd.DataFrame:
    flags: dict[str, pd.Series] = {}
    component_exposures: list[pd.Series] = []

    for component, fields in METADATA_COMPONENTS.items():
        imp = numeric_or_na(df, fields["imp"])
        rev = numeric_or_na(df, fields["rev"])
        imputed = imp.notna() & ~imp.isin([-2, 1])
        revised = rev.eq(1)

        parent_parts: list[pd.Series] = []
        for field_key in ("idx", "pc", "pc_rev"):
            field = fields.get(field_key)
            if not field:
                continue
            values = numeric_or_na(df, field)
            if field_key == "idx":
                parent_parts.append(values.notna() & values.ne(-2))
            else:
                parent_parts.append(values.notna() & values.gt(0))
        if parent_parts:
            parent_linked = parent_parts[0].copy()
            for part in parent_parts[1:]:
                parent_linked = parent_linked | part
        else:
            parent_linked = pd.Series(False, index=df.index)

        exposure = imputed | revised | parent_linked
        flags[f"FLAG_IPEDS_{component}_IMPUTED"] = imputed
        flags[f"FLAG_IPEDS_{component}_REVISED"] = revised
        flags[f"FLAG_IPEDS_{component}_PARENT_LINK"] = parent_linked
        flags[f"FLAG_IPEDS_{component}_METADATA_EXPOSURE"] = exposure
        component_exposures.append(exposure)

    if component_exposures:
        any_exposure = component_exposures[0].copy()
        for exposure in component_exposures[1:]:
            any_exposure = any_exposure | exposure
        flags["FLAG_IPEDS_ANY_METADATA_EXPOSURE"] = any_exposure

    return pd.DataFrame(flags, index=df.index)


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


def sector_net_price_value(df: pd.DataFrame, public_col: str, private_col: str) -> pd.Series:
    result = pd.Series(pd.NA, index=df.index, dtype="Float64")
    if "CONTROL" not in df.columns:
        return result
    control = pd.to_numeric(df["CONTROL"], errors="coerce")
    if public_col in df.columns:
        result = result.mask(control.eq(1), pd.to_numeric(df[public_col], errors="coerce"))
    if private_col in df.columns:
        result = result.mask(control.isin([2, 3]), pd.to_numeric(df[private_col], errors="coerce"))
    return result


def add_ratio(out: pd.DataFrame, derived: dict[str, pd.Series], name: str, numerator: str, denominator: str) -> None:
    if numerator in out.columns and denominator in out.columns:
        derived[name] = safe_divide(out[numerator], out[denominator])


def zscore_within_year(df: pd.DataFrame, series: pd.Series, mask: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    result = pd.Series(pd.NA, index=df.index, dtype="Float64")
    work = pd.DataFrame({"year": df["year"], "value": numeric, "eligible": mask.fillna(False).astype(bool)}, index=df.index)
    for _, group in work[work["eligible"] & work["value"].notna()].groupby("year", dropna=False):
        if len(group) < 2:
            continue
        std = group["value"].std(ddof=0)
        if pd.isna(std) or std == 0:
            continue
        result.loc[group.index] = (group["value"] - group["value"].mean()) / std
    return result


def add_selectivity_constructs(out: pd.DataFrame) -> pd.DataFrame:
    if "OPENADMP" not in out.columns:
        return out

    result = out.copy()
    openadmp = pd.to_numeric(result["OPENADMP"], errors="coerce")
    applicants = pd.to_numeric(result["APPLCN"], errors="coerce") if "APPLCN" in result.columns else pd.Series(pd.NA, index=result.index)
    admissions = pd.to_numeric(result["ADMSSN"], errors="coerce") if "ADMSSN" in result.columns else pd.Series(pd.NA, index=result.index)
    enrolled = pd.to_numeric(result["ENRLT"], errors="coerce") if "ENRLT" in result.columns else pd.Series(pd.NA, index=result.index)

    open_admissions = openadmp.eq(1)
    selective_admissions = openadmp.eq(2)
    valid_admit_rate = selective_admissions & applicants.gt(0) & admissions.ge(0) & admissions.le(applicants)
    valid_yield = selective_admissions & admissions.gt(0) & enrolled.ge(0) & enrolled.le(admissions)
    result["OPEN_ADMISSIONS_FLAG"] = open_admissions
    result["SELECTIVE_ADMISSIONS_FLAG"] = selective_admissions
    result["VALID_ADMIT_RATE_FLAG"] = valid_admit_rate
    result["VALID_YIELD_RATE_FLAG"] = valid_yield

    sat_available = pd.Series(False, index=result.index)
    if "SAT_TOTAL_MIDPOINT" in result.columns:
        sat = pd.to_numeric(result["SAT_TOTAL_MIDPOINT"], errors="coerce")
        sat_available = sat.between(400, 1600, inclusive="both")
    act_available = pd.Series(False, index=result.index)
    if "ACT_COMPOSITE_MIDPOINT" in result.columns:
        act = pd.to_numeric(result["ACT_COMPOSITE_MIDPOINT"], errors="coerce")
        act_available = act.between(1, 36, inclusive="both")

    score_share_parts: list[pd.Series] = []
    for col in ("SATPCT", "ACTPCT"):
        if col in result.columns:
            share = pd.to_numeric(result[col], errors="coerce")
            score_share_parts.append(share.where(share.between(0, 100, inclusive="both")))
    if score_share_parts:
        result["TEST_SCORE_REPORTING_SHARE"] = pd.concat(score_share_parts, axis=1).max(axis=1)
    else:
        result["TEST_SCORE_REPORTING_SHARE"] = pd.Series(pd.NA, index=result.index, dtype="Float64")

    test_score_available = selective_admissions & (sat_available | act_available)
    selectivity_sample = valid_admit_rate & test_score_available
    result["TEST_SCORE_AVAILABLE_FLAG"] = test_score_available
    result["SELECTIVE_ADMISSIONS_ROBUSTNESS_SAMPLE"] = selectivity_sample

    result["SELECTIVITY_ADMIT_RATE_Z"] = -zscore_within_year(result, result["ADMIT_RATE"], selectivity_sample)
    if "SAT_TOTAL_MIDPOINT" in result.columns:
        result["SELECTIVITY_SAT_Z"] = zscore_within_year(result, result["SAT_TOTAL_MIDPOINT"], selectivity_sample & sat_available)
    else:
        result["SELECTIVITY_SAT_Z"] = pd.Series(pd.NA, index=result.index, dtype="Float64")
    if "ACT_COMPOSITE_MIDPOINT" in result.columns:
        result["SELECTIVITY_ACT_Z"] = zscore_within_year(result, result["ACT_COMPOSITE_MIDPOINT"], selectivity_sample & act_available)
    else:
        result["SELECTIVITY_ACT_Z"] = pd.Series(pd.NA, index=result.index, dtype="Float64")
    result["SELECTIVITY_TEST_SCORE_Z"] = result[["SELECTIVITY_SAT_Z", "SELECTIVITY_ACT_Z"]].mean(axis=1, skipna=True)
    result.loc[~selectivity_sample, "SELECTIVITY_TEST_SCORE_Z"] = pd.NA
    result["SELECTIVITY_INDEX"] = result[["SELECTIVITY_ADMIT_RATE_Z", "SELECTIVITY_TEST_SCORE_Z"]].mean(axis=1, skipna=False)

    result["SELECTIVITY_PERCENTILE_WITHIN_YEAR"] = pd.Series(pd.NA, index=result.index, dtype="Float64")
    for _, group in result[result["SELECTIVITY_INDEX"].notna()].groupby("year", dropna=False):
        if group.empty:
            continue
        result.loc[group.index, "SELECTIVITY_PERCENTILE_WITHIN_YEAR"] = group["SELECTIVITY_INDEX"].rank(pct=True, method="average")

    category = pd.Series("admissions_policy_unknown", index=result.index, dtype="object")
    category.loc[open_admissions] = "open_admission"
    category.loc[selective_admissions & ~selectivity_sample] = "selective_admissions_index_missing"
    category.loc[selective_admissions & selectivity_sample & result["SELECTIVITY_INDEX"].isna()] = "selective_admissions_index_missing"
    pct = pd.to_numeric(result["SELECTIVITY_PERCENTILE_WITHIN_YEAR"], errors="coerce")
    category.loc[selectivity_sample & pct.le(0.25)] = "less_selective"
    category.loc[selectivity_sample & pct.gt(0.25) & pct.le(0.50)] = "moderately_selective"
    category.loc[selectivity_sample & pct.gt(0.50) & pct.le(0.75)] = "selective"
    category.loc[selectivity_sample & pct.gt(0.75)] = "highly_selective"
    result["SELECTIVITY_CATEGORY"] = category
    return result


def add_constructs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric_inputs = CORE_MONEY_VARS + NET_PRICE_VARS + FINANCE_MONEY_VARS + COUNT_PERCENT_VARS + METADATA_STATUS_VARS
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

    if "COA_OFF_NF" in derived:
        derived["COA_MAIN"] = derived["COA_OFF_NF"]
    if "HEADROOM_OFF_NF" in derived:
        derived["HEADROOM_MAIN"] = derived["HEADROOM_OFF_NF"]
    if "HEADROOM_SHARE_OFF_NF" in derived:
        derived["HEADROOM_MAIN_SHARE_COA"] = derived["HEADROOM_SHARE_OFF_NF"]
    if "HEADROOM_MAIN" in derived and "CHG2AY0" in out.columns:
        derived["HEADROOM_MAIN_SHARE_TUITION"] = safe_divide(derived["HEADROOM_MAIN"], out["CHG2AY0"])

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
        ("COA_MAIN", "LN_COA_MAIN"),
        ("HEADROOM_MAIN", "LN_HEADROOM_MAIN"),
        ("FIN_TOTAL_REVENUE", "LN_FIN_TOTAL_REVENUE"),
        ("FIN_TOTAL_EXPENSES", "LN_FIN_TOTAL_EXPENSES"),
        ("FIN_TOTAL_ASSETS", "LN_FIN_TOTAL_ASSETS"),
    ):
        if source in out.columns or source in derived:
            derived[target] = safe_log(get_series(source))

    for name, (public_col, private_col) in HARMONIZED_NET_PRICE_DEFS.items():
        if public_col in out.columns or private_col in out.columns:
            harmonized = sector_net_price_value(out, public_col, private_col)
            flag_col = f"FLAG_NEGATIVE_{name}"
            clean_col = f"{name}_CLEAN"
            derived[name] = harmonized
            derived[flag_col] = harmonized < 0
            derived[clean_col] = harmonized.mask(derived[flag_col])

    for col in NET_PRICE_VARS:
        if col not in out.columns:
            continue
        flag_col = f"FLAG_NEGATIVE_{col}"
        clean_col = f"{col}_CLEAN"
        derived[flag_col] = out[col] < 0
        derived[clean_col] = out[col].mask(derived[flag_col])

    metadata_flags = derive_metadata_flags(out)
    for col in metadata_flags.columns:
        derived[col] = metadata_flags[col]

    if derived:
        out = pd.concat([out, pd.DataFrame(derived, index=out.index)], axis=1)
    return add_selectivity_constructs(out)


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


def sample_counts(df: pd.DataFrame, year_filtered: pd.DataFrame, analysis: pd.DataFrame, sector_label: str) -> pd.DataFrame:
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
            "sample": f"analysis_four_year_titleiv_{sector_label}",
            "rows": len(analysis),
            "unitids": analysis["UNITID"].nunique(dropna=True),
            "min_year": int(analysis["year"].min()) if not analysis.empty else pd.NA,
            "max_year": int(analysis["year"].max()) if not analysis.empty else pd.NA,
        },
    ]
    return pd.DataFrame(rows)


def sector_name(value: object) -> str:
    if pd.isna(value):
        return "missing"
    try:
        return SECTOR_LABELS.get(int(value), f"sector_{int(value)}")
    except (TypeError, ValueError):
        return f"sector_{value}"


def first_nonnull_value(values: pd.Series) -> object:
    nonnull = values.dropna()
    return pd.NA if nonnull.empty else nonnull.iloc[0]


def last_nonnull_value(values: pd.Series) -> object:
    nonnull = values.dropna()
    return pd.NA if nonnull.empty else nonnull.iloc[-1]


def pipe_join_ints(values: Iterable[object]) -> str:
    cleaned: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        try:
            cleaned.append(str(int(value)))
        except (TypeError, ValueError):
            cleaned.append(str(value))
    return "|".join(cleaned)


def normalized_value(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def value_changed(left: object, right: object) -> bool:
    if pd.isna(left) and pd.isna(right):
        return False
    if pd.isna(left) or pd.isna(right):
        return True
    return bool(left != right)


def event_row_at_year(df: pd.DataFrame, unitid: object, year: int) -> dict[str, object]:
    row = df[(df["UNITID"] == unitid) & (df["year"] == year)].iloc[0]
    return row.to_dict()


def classify_transition_reason(
    event_type: str,
    sample_row: dict[str, object],
    comparison_row: dict[str, object] | None,
) -> dict[str, object]:
    if comparison_row is None:
        if event_type == "entry":
            reason = "full_panel_first_appearance"
            return {
                "reason_category": reason,
                "full_panel_first_appearance": True,
                "full_panel_disappearance": False,
                "pset4flg_transition": False,
                "sector_transition": False,
            }
        reason = "full_panel_disappearance"
        return {
            "reason_category": reason,
            "full_panel_first_appearance": False,
            "full_panel_disappearance": True,
            "pset4flg_transition": False,
            "sector_transition": False,
        }

    sample_pset = normalized_value(sample_row.get("PSET4FLG"))
    sample_sector = normalized_value(sample_row.get("SECTOR"))
    comparison_pset = normalized_value(comparison_row.get("PSET4FLG"))
    comparison_sector = normalized_value(comparison_row.get("SECTOR"))
    pset_changed = value_changed(sample_pset, comparison_pset)
    sector_changed = value_changed(sample_sector, comparison_sector)
    if pset_changed and sector_changed:
        reason = "pset4flg_and_sector_transition"
    elif pset_changed:
        reason = "pset4flg_transition"
    elif sector_changed:
        reason = "sector_transition"
    else:
        reason = "full_panel_gap_or_other"
    return {
        "reason_category": reason,
        "full_panel_first_appearance": False,
        "full_panel_disappearance": False,
        "pset4flg_transition": pset_changed,
        "sector_transition": sector_changed,
    }


def build_panel_balance_by_institution(df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    columns = [
        "UNITID",
        "INSTNM",
        "OPEID",
        "first_year",
        "last_year",
        "years_observed",
        "possible_years",
        "observation_share",
        "balanced_full_window",
        "first_observed_after_start",
        "last_observed_before_end",
        "missing_years",
        "missing_year_count",
        "observed_years",
        "sector_first",
        "sector_last",
        "sector_label_first",
        "sector_label_last",
        "sector_changed",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    start_year = min(years)
    end_year = max(years)
    possible_years = len(years)
    expected_years = set(years)
    work = df.sort_values(["UNITID", "year"]).copy()
    rows: list[dict[str, object]] = []

    for unitid, group in work.groupby("UNITID", dropna=False, sort=True):
        observed = sorted(int(year) for year in pd.to_numeric(group["year"], errors="coerce").dropna().unique())
        observed_set = set(observed)
        missing = sorted(expected_years - observed_set)
        sector_values = pd.to_numeric(group["SECTOR"], errors="coerce") if "SECTOR" in group.columns else pd.Series(dtype="Float64")
        sector_first = first_nonnull_value(sector_values)
        sector_last = last_nonnull_value(sector_values)
        sector_unique = sector_values.dropna().astype(int).nunique() if not sector_values.empty else 0
        row = {
            "UNITID": unitid,
            "INSTNM": first_nonnull_value(group["INSTNM"]) if "INSTNM" in group.columns else "",
            "OPEID": first_nonnull_value(group["OPEID"]) if "OPEID" in group.columns else "",
            "first_year": observed[0] if observed else pd.NA,
            "last_year": observed[-1] if observed else pd.NA,
            "years_observed": len(observed),
            "possible_years": possible_years,
            "observation_share": len(observed) / possible_years if possible_years else pd.NA,
            "balanced_full_window": len(observed) == possible_years,
            "first_observed_after_start": bool(observed and observed[0] > start_year),
            "last_observed_before_end": bool(observed and observed[-1] < end_year),
            "missing_years": pipe_join_ints(missing),
            "missing_year_count": len(missing),
            "observed_years": pipe_join_ints(observed),
            "sector_first": sector_first,
            "sector_last": sector_last,
            "sector_label_first": sector_name(sector_first),
            "sector_label_last": sector_name(sector_last),
            "sector_changed": bool(sector_unique > 1),
        }
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def entry_exit_reason_audit(full_panel: pd.DataFrame, analysis: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    columns = [
        "UNITID",
        "INSTNM",
        "OPEID",
        "event_type",
        "event_year",
        "reason_category",
        "full_panel_first_appearance",
        "full_panel_disappearance",
        "pset4flg_transition",
        "sector_transition",
        "comparison_basis",
        "comparison_year",
        "sample_first_year",
        "sample_last_year",
        "sample_years_observed",
        "full_panel_first_year",
        "full_panel_last_year",
        "full_panel_years_observed",
        "sample_event_pset4flg",
        "comparison_pset4flg",
        "sample_event_sector",
        "comparison_sector",
        "sample_event_sector_label",
        "comparison_sector_label",
        "sample_event_control",
        "comparison_control",
        "sample_event_iclevel",
        "comparison_iclevel",
        "sample_event_hloffer",
        "comparison_hloffer",
        "sample_event_deggrant",
        "comparison_deggrant",
        "sample_event_ugoffer",
        "comparison_ugoffer",
    ]
    if analysis.empty:
        return pd.DataFrame(columns=columns)

    start_year = min(years)
    end_year = max(years)
    full_work = full_panel.sort_values(["UNITID", "year"]).copy()
    sample_balance = build_panel_balance_by_institution(analysis, years)
    rows: list[dict[str, object]] = []

    def add_event(unit_balance: pd.Series, event_type: str) -> None:
        unitid = unit_balance["UNITID"]
        event_year = int(unit_balance["first_year"] if event_type == "entry" else unit_balance["last_year"])
        unit_full = full_work[full_work["UNITID"] == unitid]
        full_years = sorted(int(year) for year in pd.to_numeric(unit_full["year"], errors="coerce").dropna().unique())
        if event_type == "entry":
            comparison = unit_full[unit_full["year"] < event_year].tail(1)
            comparison_basis = "nearest_prior_full_panel_row"
        else:
            comparison = unit_full[unit_full["year"] > event_year].head(1)
            comparison_basis = "nearest_next_full_panel_row"
        comparison_row = None if comparison.empty else comparison.iloc[0].to_dict()
        if comparison_row is None:
            comparison_basis = "no_prior_full_panel_row" if event_type == "entry" else "no_later_full_panel_row"
        sample_row = event_row_at_year(analysis, unitid, event_year)
        reason = classify_transition_reason(event_type, sample_row, comparison_row)

        row = {
            "UNITID": unitid,
            "INSTNM": sample_row.get("INSTNM", ""),
            "OPEID": sample_row.get("OPEID", ""),
            "event_type": event_type,
            "event_year": event_year,
            "comparison_basis": comparison_basis,
            "comparison_year": normalized_value(comparison_row.get("year")) if comparison_row else pd.NA,
            "sample_first_year": normalized_value(unit_balance["first_year"]),
            "sample_last_year": normalized_value(unit_balance["last_year"]),
            "sample_years_observed": normalized_value(unit_balance["years_observed"]),
            "full_panel_first_year": min(full_years) if full_years else pd.NA,
            "full_panel_last_year": max(full_years) if full_years else pd.NA,
            "full_panel_years_observed": len(full_years),
            "sample_event_pset4flg": normalized_value(sample_row.get("PSET4FLG")),
            "comparison_pset4flg": normalized_value(comparison_row.get("PSET4FLG")) if comparison_row else pd.NA,
            "sample_event_sector": normalized_value(sample_row.get("SECTOR")),
            "comparison_sector": normalized_value(comparison_row.get("SECTOR")) if comparison_row else pd.NA,
            "sample_event_sector_label": sector_name(sample_row.get("SECTOR")),
            "comparison_sector_label": sector_name(comparison_row.get("SECTOR")) if comparison_row else "",
            "sample_event_control": normalized_value(sample_row.get("CONTROL")),
            "comparison_control": normalized_value(comparison_row.get("CONTROL")) if comparison_row else pd.NA,
            "sample_event_iclevel": normalized_value(sample_row.get("ICLEVEL")),
            "comparison_iclevel": normalized_value(comparison_row.get("ICLEVEL")) if comparison_row else pd.NA,
            "sample_event_hloffer": normalized_value(sample_row.get("HLOFFER")),
            "comparison_hloffer": normalized_value(comparison_row.get("HLOFFER")) if comparison_row else pd.NA,
            "sample_event_deggrant": normalized_value(sample_row.get("DEGGRANT")),
            "comparison_deggrant": normalized_value(comparison_row.get("DEGGRANT")) if comparison_row else pd.NA,
            "sample_event_ugoffer": normalized_value(sample_row.get("UGOFFER")),
            "comparison_ugoffer": normalized_value(comparison_row.get("UGOFFER")) if comparison_row else pd.NA,
        }
        row.update(reason)
        rows.append(row)

    for _, unit_balance in sample_balance.sort_values(["UNITID"]).iterrows():
        first_year = int(unit_balance["first_year"])
        last_year = int(unit_balance["last_year"])
        if first_year > start_year:
            add_event(unit_balance, "entry")
        if last_year < end_year:
            add_event(unit_balance, "exit")

    return pd.DataFrame(rows, columns=columns).sort_values(["event_year", "event_type", "UNITID"]).reset_index(drop=True)


def balance_summary(balance: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "scope",
        "sector",
        "institutions",
        "balanced_institutions",
        "balanced_share",
        "mean_years_observed",
        "median_years_observed",
        "min_years_observed",
        "max_years_observed",
        "first_observed_after_start",
        "last_observed_before_end",
        "observed_both_after_start_and_before_end",
        "sector_changed",
    ]
    if balance.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []

    def add_row(scope: str, sector: str, group: pd.DataFrame) -> None:
        institutions = int(len(group))
        balanced = int(group["balanced_full_window"].fillna(False).astype(bool).sum())
        first_after_start = group["first_observed_after_start"].fillna(False).astype(bool)
        last_before_end = group["last_observed_before_end"].fillna(False).astype(bool)
        rows.append(
            {
                "scope": scope,
                "sector": sector,
                "institutions": institutions,
                "balanced_institutions": balanced,
                "balanced_share": balanced / institutions if institutions else 0.0,
                "mean_years_observed": float(group["years_observed"].mean()) if institutions else 0.0,
                "median_years_observed": float(group["years_observed"].median()) if institutions else 0.0,
                "min_years_observed": int(group["years_observed"].min()) if institutions else 0,
                "max_years_observed": int(group["years_observed"].max()) if institutions else 0,
                "first_observed_after_start": int(first_after_start.sum()),
                "last_observed_before_end": int(last_before_end.sum()),
                "observed_both_after_start_and_before_end": int((first_after_start & last_before_end).sum()),
                "sector_changed": int(group["sector_changed"].fillna(False).astype(bool).sum()),
            }
        )

    add_row("overall", "all", balance)
    for sector, group in balance.groupby("sector_label_first", dropna=False, sort=True):
        add_row("sector", str(sector), group)
    return pd.DataFrame(rows, columns=columns)


def entry_exit_by_sector_year(balance: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    columns = [
        "year",
        "sector",
        "first_observed_in_window",
        "first_observed_after_window_start",
        "last_observed_in_window",
        "last_observed_before_window_end",
    ]
    if balance.empty:
        return pd.DataFrame(columns=columns)

    start_year = min(years)
    end_year = max(years)
    sectors = ["all"] + sorted(str(sector) for sector in balance["sector_label_first"].dropna().unique())
    rows: list[dict[str, object]] = []
    for sector in sectors:
        group = balance if sector == "all" else balance[balance["sector_label_first"] == sector]
        for year in years:
            first_count = int((group["first_year"] == year).sum())
            last_count = int((group["last_year"] == year).sum())
            rows.append(
                {
                    "year": year,
                    "sector": sector,
                    "first_observed_in_window": first_count,
                    "first_observed_after_window_start": first_count if year > start_year else 0,
                    "last_observed_in_window": last_count,
                    "last_observed_before_window_end": last_count if year < end_year else 0,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def institution_years_by_sector_year(df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    columns = ["year", "sector", "institution_years", "institutions"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    work = df.copy()
    work["SECTOR"] = pd.to_numeric(work["SECTOR"], errors="coerce")
    grouped = (
        work.groupby(["year", "SECTOR"], dropna=False)
        .agg(institution_years=("UNITID", "size"), institutions=("UNITID", "nunique"))
        .reset_index()
    )
    grouped["sector"] = grouped["SECTOR"].map(sector_name)
    grouped = grouped[["year", "sector", "institution_years", "institutions"]]

    all_rows = (
        work.groupby("year", dropna=False)
        .agg(institution_years=("UNITID", "size"), institutions=("UNITID", "nunique"))
        .reset_index()
    )
    all_rows["sector"] = "all"
    all_rows = all_rows[["year", "sector", "institution_years", "institutions"]]

    out = pd.concat([all_rows, grouped], ignore_index=True)
    sectors = ["all"] + sorted(sector for sector in out["sector"].unique() if sector != "all")
    complete_index = pd.MultiIndex.from_product([years, sectors], names=["year", "sector"])
    out = out.set_index(["year", "sector"]).reindex(complete_index, fill_value=0).reset_index()
    return out[columns].sort_values(["sector", "year"]).reset_index(drop=True)


def minimum_years_sensitivity(balance: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "sector",
        "min_years_required",
        "institutions_retained",
        "institution_share_retained",
        "institution_years_retained",
        "institution_year_share_retained",
    ]
    if balance.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    max_years = int(balance["possible_years"].max())

    def add_rows(sector: str, group: pd.DataFrame) -> None:
        total_institutions = len(group)
        total_institution_years = int(group["years_observed"].sum())
        for threshold in range(1, max_years + 1):
            retained = group[group["years_observed"] >= threshold]
            retained_institutions = int(len(retained))
            retained_years = int(retained["years_observed"].sum())
            rows.append(
                {
                    "sector": sector,
                    "min_years_required": threshold,
                    "institutions_retained": retained_institutions,
                    "institution_share_retained": retained_institutions / total_institutions if total_institutions else 0.0,
                    "institution_years_retained": retained_years,
                    "institution_year_share_retained": retained_years / total_institution_years if total_institution_years else 0.0,
                }
            )

    add_rows("all", balance)
    for sector, group in balance.groupby("sector_label_first", dropna=False, sort=True):
        add_rows(str(sector), group)
    return pd.DataFrame(rows, columns=columns)


def selectivity_summary(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "year",
        "sector",
        "selectivity_category",
        "rows",
        "unitids",
        "mean_admit_rate",
        "median_admit_rate",
        "mean_sat_total_midpoint",
        "mean_act_composite_midpoint",
        "mean_selectivity_index",
    ]
    if df.empty or "SELECTIVITY_CATEGORY" not in df.columns:
        return pd.DataFrame(columns=columns)

    work = df.copy()
    work["sector"] = work["SECTOR"].map(sector_name) if "SECTOR" in work.columns else "all"
    rows: list[dict[str, object]] = []

    def add_rows(scope_sector: str, group: pd.DataFrame) -> None:
        for (year, category), sub in group.groupby(["year", "SELECTIVITY_CATEGORY"], dropna=False, sort=True):
            admit = pd.to_numeric(sub["ADMIT_RATE"], errors="coerce") if "ADMIT_RATE" in sub.columns else pd.Series(dtype="Float64")
            sat = pd.to_numeric(sub["SAT_TOTAL_MIDPOINT"], errors="coerce") if "SAT_TOTAL_MIDPOINT" in sub.columns else pd.Series(dtype="Float64")
            act = pd.to_numeric(sub["ACT_COMPOSITE_MIDPOINT"], errors="coerce") if "ACT_COMPOSITE_MIDPOINT" in sub.columns else pd.Series(dtype="Float64")
            index = pd.to_numeric(sub["SELECTIVITY_INDEX"], errors="coerce") if "SELECTIVITY_INDEX" in sub.columns else pd.Series(dtype="Float64")
            rows.append(
                {
                    "year": year,
                    "sector": scope_sector,
                    "selectivity_category": category,
                    "rows": int(len(sub)),
                    "unitids": int(sub["UNITID"].nunique(dropna=True)) if "UNITID" in sub.columns else 0,
                    "mean_admit_rate": None if admit.dropna().empty else float(admit.mean()),
                    "median_admit_rate": None if admit.dropna().empty else float(admit.median()),
                    "mean_sat_total_midpoint": None if sat.dropna().empty else float(sat.mean()),
                    "mean_act_composite_midpoint": None if act.dropna().empty else float(act.mean()),
                    "mean_selectivity_index": None if index.dropna().empty else float(index.mean()),
                }
            )

    add_rows("all", work)
    for sector, group in work.groupby("sector", dropna=False, sort=True):
        add_rows(str(sector), group)
    return pd.DataFrame(rows, columns=columns)


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
    sanity_vars = CORE_MONEY_VARS + NET_PRICE_VARS + HARMONIZED_NET_PRICE_VARS + FINANCE_MONEY_VARS
    for col in [c for c in sanity_vars if c in df.columns]:
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


def numeric_or_na(df: pd.DataFrame, col: str) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(pd.NA, index=df.index, dtype="Float64")


def aid_zero_consistency_rows(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "year",
        "UNITID",
        "INSTNM",
        "sector",
        "aid_scope",
        "aid_family",
        "aid_label",
        "average_var",
        "count_var",
        "percent_var",
        "total_var",
        "denominator_var",
        "average_value",
        "count_value",
        "percent_value",
        "total_value",
        "denominator_value",
        "expected_percent",
        "percent_gap",
        "expected_total_from_average",
        "total_gap",
        "true_zero",
        "positive_consistent",
        "suspect_zero_total",
        "suspect_zero_count",
        "suspect_zero_percent",
        "suspect_zero_average",
        "count_percent_mismatch",
        "total_average_count_mismatch",
        "any_issue",
        "issue_reason",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    out_rows: list[pd.DataFrame] = []
    sector = df["SECTOR"].map(sector_name) if "SECTOR" in df.columns else pd.Series("all", index=df.index)
    instnm = df["INSTNM"] if "INSTNM" in df.columns else pd.Series("", index=df.index)
    year = df["year"] if "year" in df.columns else pd.Series(pd.NA, index=df.index)
    unitid = df["UNITID"] if "UNITID" in df.columns else pd.Series(pd.NA, index=df.index)

    for aid_scope, family, label, avg_col, count_col, pct_col, total_col, denom_col in AID_ZERO_AUDIT_SPECS:
        avg = numeric_or_na(df, avg_col)
        count = numeric_or_na(df, count_col)
        pct = numeric_or_na(df, pct_col)
        total = numeric_or_na(df, total_col)
        denom = numeric_or_na(df, denom_col)
        any_observed = avg.notna() | count.notna() | pct.notna() | total.notna()

        true_zero = (
            any_observed
            & count.fillna(0).eq(0)
            & pct.fillna(0).eq(0)
            & total.fillna(0).eq(0)
            & (avg.isna() | avg.eq(0))
        ).fillna(False).astype(bool)
        suspect_zero_total = (total.eq(0) & (count.gt(0) | pct.gt(0) | avg.gt(0))).fillna(False).astype(bool)
        suspect_zero_count = (count.eq(0) & (total.gt(0) | avg.gt(0))).fillna(False).astype(bool)
        suspect_zero_percent = (pct.eq(0) & (count.gt(0) | total.gt(0))).fillna(False).astype(bool)
        suspect_zero_average = (avg.eq(0) & (count.gt(0) | total.gt(0))).fillna(False).astype(bool)

        expected_pct = count / denom.where(denom != 0) * 100
        pct_gap = pct - expected_pct
        count_percent_mismatch = (
            count.notna() & pct.notna() & denom.gt(0) & pct_gap.abs().gt(1.0)
        ).fillna(False).astype(bool)

        expected_total = avg * count
        total_gap = total - expected_total
        total_tolerance = pd.concat(
            [count.abs() * 0.51, total.abs() * 0.01, pd.Series(1.0, index=df.index)],
            axis=1,
        ).max(axis=1)
        total_average_count_mismatch = (
            total.notna()
            & avg.notna()
            & count.gt(0)
            & expected_total.notna()
            & total_gap.abs().gt(total_tolerance)
        ).fillna(False).astype(bool)

        any_issue = (
            suspect_zero_total
            | suspect_zero_count
            | suspect_zero_percent
            | suspect_zero_average
            | count_percent_mismatch
            | total_average_count_mismatch
        )
        positive_signal = (avg.gt(0) | count.gt(0) | pct.gt(0) | total.gt(0)).fillna(False).astype(bool)
        positive_consistent = (any_observed & ~true_zero & positive_signal & ~any_issue).fillna(False).astype(bool)

        issue_parts = pd.DataFrame(
            {
                "suspect_zero_total": suspect_zero_total,
                "suspect_zero_count": suspect_zero_count,
                "suspect_zero_percent": suspect_zero_percent,
                "suspect_zero_average": suspect_zero_average,
                "count_percent_mismatch": count_percent_mismatch,
                "total_average_count_mismatch": total_average_count_mismatch,
            },
            index=df.index,
        )
        issue_reason = issue_parts.apply(lambda row: ";".join(name for name, value in row.items() if bool(value)), axis=1)

        out_rows.append(
            pd.DataFrame(
                {
                    "year": year,
                    "UNITID": unitid,
                    "INSTNM": instnm,
                    "sector": sector,
                    "aid_scope": aid_scope,
                    "aid_family": family,
                    "aid_label": label,
                    "average_var": avg_col,
                    "count_var": count_col,
                    "percent_var": pct_col,
                    "total_var": total_col,
                    "denominator_var": denom_col,
                    "average_value": avg,
                    "count_value": count,
                    "percent_value": pct,
                    "total_value": total,
                    "denominator_value": denom,
                    "expected_percent": expected_pct,
                    "percent_gap": pct_gap,
                    "expected_total_from_average": expected_total,
                    "total_gap": total_gap,
                    "true_zero": true_zero,
                    "positive_consistent": positive_consistent,
                    "suspect_zero_total": suspect_zero_total,
                    "suspect_zero_count": suspect_zero_count,
                    "suspect_zero_percent": suspect_zero_percent,
                    "suspect_zero_average": suspect_zero_average,
                    "count_percent_mismatch": count_percent_mismatch,
                    "total_average_count_mismatch": total_average_count_mismatch,
                    "any_issue": any_issue,
                    "issue_reason": issue_reason.where(any_issue, ""),
                },
                index=df.index,
            )
        )

    return pd.concat(out_rows, ignore_index=True)[columns]


def aid_zero_consistency_summary(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "scope",
        "scope_value",
        "aid_scope",
        "aid_family",
        "aid_label",
        "rows",
        "true_zero_rows",
        "positive_consistent_rows",
        "suspect_zero_rows",
        "suspect_zero_total_rows",
        "suspect_zero_count_rows",
        "suspect_zero_percent_rows",
        "suspect_zero_average_rows",
        "count_percent_mismatch_rows",
        "total_average_count_mismatch_rows",
        "issue_share",
    ]
    if rows.empty:
        return pd.DataFrame(columns=columns)

    summary_rows: list[dict[str, object]] = []

    def add_group(scope: str, scope_value: object, group: pd.DataFrame) -> None:
        for (aid_scope, family, label), sub in group.groupby(
            ["aid_scope", "aid_family", "aid_label"],
            dropna=False,
            sort=True,
        ):
            total_rows = int(len(sub))
            suspect_zero = sub[
                [
                    "suspect_zero_total",
                    "suspect_zero_count",
                    "suspect_zero_percent",
                    "suspect_zero_average",
                ]
            ].any(axis=1)
            summary_rows.append(
                {
                    "scope": scope,
                    "scope_value": scope_value,
                    "aid_scope": aid_scope,
                    "aid_family": family,
                    "aid_label": label,
                    "rows": total_rows,
                    "true_zero_rows": int(sub["true_zero"].fillna(False).astype(bool).sum()),
                    "positive_consistent_rows": int(sub["positive_consistent"].fillna(False).astype(bool).sum()),
                    "suspect_zero_rows": int(suspect_zero.sum()),
                    "suspect_zero_total_rows": int(sub["suspect_zero_total"].fillna(False).astype(bool).sum()),
                    "suspect_zero_count_rows": int(sub["suspect_zero_count"].fillna(False).astype(bool).sum()),
                    "suspect_zero_percent_rows": int(sub["suspect_zero_percent"].fillna(False).astype(bool).sum()),
                    "suspect_zero_average_rows": int(sub["suspect_zero_average"].fillna(False).astype(bool).sum()),
                    "count_percent_mismatch_rows": int(sub["count_percent_mismatch"].fillna(False).astype(bool).sum()),
                    "total_average_count_mismatch_rows": int(sub["total_average_count_mismatch"].fillna(False).astype(bool).sum()),
                    "issue_share": float(sub["any_issue"].fillna(False).astype(bool).mean()) if total_rows else 0.0,
                }
            )

    add_group("overall", "all", rows)
    if "year" in rows.columns:
        for year, group in rows.groupby("year", dropna=False):
            add_group("year", year, group)
    if "sector" in rows.columns:
        for sector, group in rows.groupby("sector", dropna=False):
            add_group("sector", sector, group)
    return pd.DataFrame(summary_rows, columns=columns)


def metadata_flag_summary(df: pd.DataFrame) -> pd.DataFrame:
    flag_cols = [col for col in df.columns if col.startswith("FLAG_IPEDS_")]
    rows: list[dict[str, object]] = []

    def add_rows(scope: str, scope_value: object, group: pd.DataFrame) -> None:
        for col in flag_cols:
            s = group[col].fillna(False).astype(bool)
            rows.append(
                {
                    "scope": scope,
                    "scope_value": scope_value,
                    "flag": col,
                    "rows": int(len(group)),
                    "flagged_rows": int(s.sum()),
                    "flagged_share": float(s.mean()) if len(group) else 0.0,
                }
            )

    add_rows("overall", "all", df)
    if "year" in df.columns:
        for year, group in df.groupby("year", dropna=False):
            add_rows("year", year, group)
    if "CONTROL" in df.columns:
        for control, group in df.groupby("CONTROL", dropna=False):
            add_rows("control", control, group)
    return pd.DataFrame(rows)


def metadata_code_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for col in [c for c in METADATA_CODE_SUMMARY_VARS if c in df.columns]:
        s = pd.to_numeric(df[col], errors="coerce")
        counts = s.dropna().value_counts().sort_index()
        for value, count in counts.items():
            rows.append(
                {
                    "varname": col,
                    "code": value,
                    "rows": int(len(df)),
                    "nonnull": int(s.notna().sum()),
                    "count": int(count),
                    "share_of_rows": float(count / len(df)) if len(df) else 0.0,
                    "share_of_nonnull": float(count / s.notna().sum()) if s.notna().sum() else 0.0,
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
        {"varname": "COA_MAIN", "group": "derived_coa", "role": "preferred total COA construct for the main headroom measure", "required": False},
        {
            "varname": "HEADROOM_IN_DISTRICT",
            "group": "derived_headroom",
            "role": "in-district non-tuition headroom",
            "required": False,
        },
        {"varname": "HEADROOM_ON", "group": "derived_headroom", "role": "on-campus non-tuition headroom", "required": False},
        {"varname": "HEADROOM_OFF_NF", "group": "derived_headroom", "role": "off-campus not-with-family non-tuition headroom", "required": False},
        {"varname": "HEADROOM_OFF_WF", "group": "derived_headroom", "role": "off-campus with-family non-tuition headroom", "required": False},
        {"varname": "HEADROOM_MAIN", "group": "derived_headroom", "role": "preferred non-tuition COA headroom measure", "required": False},
        {
            "varname": "HEADROOM_SHARE_IN_DISTRICT",
            "group": "derived_headroom",
            "role": "in-district non-tuition share",
            "required": False,
        },
        {"varname": "HEADROOM_SHARE_ON", "group": "derived_headroom", "role": "on-campus non-tuition share", "required": False},
        {"varname": "HEADROOM_SHARE_OFF_NF", "group": "derived_headroom", "role": "off-campus not-with-family non-tuition share", "required": False},
        {"varname": "HEADROOM_SHARE_OFF_WF", "group": "derived_headroom", "role": "off-campus with-family non-tuition share", "required": False},
        {"varname": "HEADROOM_MAIN_SHARE_COA", "group": "derived_headroom", "role": "preferred non-tuition headroom share of total COA", "required": False},
        {
            "varname": "HEADROOM_MAIN_SHARE_TUITION",
            "group": "derived_headroom",
            "role": "preferred non-tuition headroom divided by in-state tuition and fees",
            "required": False,
        },
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
        {"varname": "OPEN_ADMISSIONS_FLAG", "group": "derived_admissions", "role": "OPENADMP indicates an open-admissions policy", "required": False},
        {
            "varname": "SELECTIVE_ADMISSIONS_FLAG",
            "group": "derived_admissions",
            "role": "OPENADMP indicates the institution does not have open admissions",
            "required": False,
        },
        {
            "varname": "VALID_ADMIT_RATE_FLAG",
            "group": "derived_admissions_quality",
            "role": "applicant and admission counts form a valid admit rate",
            "required": False,
        },
        {
            "varname": "VALID_YIELD_RATE_FLAG",
            "group": "derived_admissions_quality",
            "role": "admission and enrolled counts form a valid yield rate",
            "required": False,
        },
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
            "varname": "TEST_SCORE_REPORTING_SHARE",
            "group": "derived_selectivity",
            "role": "larger of SATPCT and ACTPCT where reported",
            "required": False,
        },
        {
            "varname": "TEST_SCORE_AVAILABLE_FLAG",
            "group": "derived_selectivity",
            "role": "selective-admissions row has a usable SAT or ACT midpoint",
            "required": False,
        },
        {
            "varname": "SELECTIVE_ADMISSIONS_ROBUSTNESS_SAMPLE",
            "group": "derived_selectivity",
            "role": "non-open-admissions row with valid admit rate and usable test-score midpoint",
            "required": False,
        },
        {
            "varname": "SELECTIVITY_ADMIT_RATE_Z",
            "group": "derived_selectivity",
            "role": "within-year standardized negative admit-rate component; higher means more selective",
            "required": False,
        },
        {
            "varname": "SELECTIVITY_SAT_Z",
            "group": "derived_selectivity",
            "role": "within-year standardized SAT midpoint component",
            "required": False,
        },
        {
            "varname": "SELECTIVITY_ACT_Z",
            "group": "derived_selectivity",
            "role": "within-year standardized ACT midpoint component",
            "required": False,
        },
        {
            "varname": "SELECTIVITY_TEST_SCORE_Z",
            "group": "derived_selectivity",
            "role": "mean of available SAT and ACT within-year standardized test-score components",
            "required": False,
        },
        {
            "varname": "SELECTIVITY_INDEX",
            "group": "derived_selectivity",
            "role": "mean of admit-rate and test-score selectivity components in the robustness sample",
            "required": False,
        },
        {
            "varname": "SELECTIVITY_PERCENTILE_WITHIN_YEAR",
            "group": "derived_selectivity",
            "role": "percentile rank of the selectivity index within year and output scope",
            "required": False,
        },
        {
            "varname": "SELECTIVITY_CATEGORY",
            "group": "derived_selectivity",
            "role": "open-admission, missing-index, or within-year selectivity category",
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
        {"varname": "LN_COA_MAIN", "group": "derived_scale", "role": "log preferred total COA construct", "required": False},
        {"varname": "LN_HEADROOM_MAIN", "group": "derived_scale", "role": "log preferred non-tuition headroom", "required": False},
        {"varname": "LN_FIN_TOTAL_REVENUE", "group": "derived_scale", "role": "log sector-harmonized total revenue", "required": False},
        {"varname": "LN_FIN_TOTAL_EXPENSES", "group": "derived_scale", "role": "log sector-harmonized total expenses", "required": False},
        {"varname": "LN_FIN_TOTAL_ASSETS", "group": "derived_scale", "role": "log sector-harmonized total assets", "required": False},
    ]
    for component in METADATA_COMPONENTS:
        label = component.lower()
        derived_specs.extend(
            [
                {
                    "varname": f"FLAG_IPEDS_{component}_IMPUTED",
                    "group": "derived_metadata_flag",
                    "role": f"{label} component has an imputation-method code other than baseline reported or not applicable",
                    "required": False,
                },
                {
                    "varname": f"FLAG_IPEDS_{component}_REVISED",
                    "group": "derived_metadata_flag",
                    "role": f"{label} component has an IPEDS prior-year revision indicator",
                    "required": False,
                },
                {
                    "varname": f"FLAG_IPEDS_{component}_PARENT_LINK",
                    "group": "derived_metadata_flag",
                    "role": f"{label} component has a parent UNITID or positive allocation factor",
                    "required": False,
                },
                {
                    "varname": f"FLAG_IPEDS_{component}_METADATA_EXPOSURE",
                    "group": "derived_metadata_flag",
                    "role": f"{label} component is imputed, revised, or parent-linked",
                    "required": False,
                },
            ]
        )
    derived_specs.append(
        {
            "varname": "FLAG_IPEDS_ANY_METADATA_EXPOSURE",
            "group": "derived_metadata_flag",
            "role": "any tracked IPEDS component is imputed, revised, or parent-linked",
            "required": False,
        }
    )
    for name, (public_col, private_col) in HARMONIZED_NET_PRICE_DEFS.items():
        derived_specs.extend(
            [
                {
                    "varname": name,
                    "group": "derived_net_price",
                    "role": f"sector-harmonized net price from public {public_col} and private {private_col}",
                    "required": False,
                },
                {"varname": f"FLAG_NEGATIVE_{name}", "group": "quality_flag", "role": f"negative harmonized {name} flag", "required": False},
                {"varname": f"{name}_CLEAN", "group": "cleaned_net_price", "role": f"{name} with negative values set null", "required": False},
            ]
        )
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
    sectors_spec: str = DEFAULT_MAIN_SECTORS_SPEC,
    title_iv_flag: int = 1,
) -> dict[str, object]:
    if not input_panel.exists():
        raise SystemExit(f"Input panel does not exist: {input_panel}")
    specs = load_variable_specs(variable_config)
    years = parse_years(years_spec)
    sectors = parse_int_list(sectors_spec)
    sector_label = sector_scope_label(sectors)
    output_root = output_dir
    output_dir = output_root / sector_label
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
    analysis_path = output_dir / f"analysis_panel_coa_headroom_{year_label}_{sector_label}.parquet"
    selective_admissions_path = output_dir / f"analysis_panel_selective_admissions_robustness_{year_label}_{sector_label}.parquet"
    manifest_path = output_dir / "analysis_variable_manifest.csv"
    sample_counts_path = output_dir / "analysis_sample_counts.csv"
    panel_balance_path = output_dir / "analysis_panel_balance_by_institution.csv"
    panel_balance_summary_path = output_dir / "analysis_panel_balance_summary.csv"
    entry_exit_path = output_dir / "analysis_entry_exit_by_sector_year.csv"
    entry_exit_reason_path = output_dir / "analysis_entry_exit_reason_audit.csv"
    sector_year_path = output_dir / "analysis_institution_years_by_sector_year.csv"
    min_years_path = output_dir / "analysis_min_years_sensitivity.csv"
    selectivity_summary_path = output_dir / "analysis_selectivity_summary.csv"
    missingness_path = output_dir / "analysis_missingness_by_year.csv"
    value_sanity_path = output_dir / "analysis_value_sanity.csv"
    aid_zero_consistency_path = output_dir / "analysis_aid_zero_consistency.csv"
    aid_zero_suspect_path = output_dir / "analysis_aid_zero_suspect_rows.csv"
    metadata_summary_path = output_dir / "analysis_metadata_flag_summary.csv"
    metadata_code_path = output_dir / "analysis_metadata_code_summary.csv"
    summary_path = output_dir / "analysis_build_summary.json"

    analysis.to_parquet(analysis_path, index=False)
    selective_admissions = analysis[analysis["SELECTIVE_ADMISSIONS_ROBUSTNESS_SAMPLE"].fillna(False).astype(bool)].copy()
    selective_admissions.to_parquet(selective_admissions_path, index=False)
    manifest = read_dictionary_manifest(dictionary, specs, set(schema_cols))
    pd.concat([manifest, derived_manifest_rows()], ignore_index=True).to_csv(manifest_path, index=False)
    sample_counts(df, year_filtered, analysis, sector_label).to_csv(sample_counts_path, index=False)
    panel_balance = build_panel_balance_by_institution(analysis, years)
    panel_balance.to_csv(panel_balance_path, index=False)
    balance_summary(panel_balance).to_csv(panel_balance_summary_path, index=False)
    entry_exit_by_sector_year(panel_balance, years).to_csv(entry_exit_path, index=False)
    entry_exit_reason_audit(year_filtered, analysis, years).to_csv(entry_exit_reason_path, index=False)
    institution_years_by_sector_year(analysis, years).to_csv(sector_year_path, index=False)
    minimum_years_sensitivity(panel_balance).to_csv(min_years_path, index=False)
    selectivity_summary(analysis).to_csv(selectivity_summary_path, index=False)
    missingness_by_year(analysis).to_csv(missingness_path, index=False)
    value_sanity(analysis).to_csv(value_sanity_path, index=False)
    aid_zero_rows = aid_zero_consistency_rows(analysis)
    aid_zero_consistency_summary(aid_zero_rows).to_csv(aid_zero_consistency_path, index=False)
    zero_suspect_mask = aid_zero_rows[
        [
            "suspect_zero_total",
            "suspect_zero_count",
            "suspect_zero_percent",
            "suspect_zero_average",
        ]
    ].any(axis=1)
    aid_zero_rows[zero_suspect_mask].to_csv(aid_zero_suspect_path, index=False)
    metadata_flag_summary(analysis).to_csv(metadata_summary_path, index=False)
    metadata_code_summary(analysis).to_csv(metadata_code_path, index=False)

    negative_net_price_counts = {
        col: int((pd.to_numeric(analysis[col], errors="coerce") < 0).sum())
        for col in NET_PRICE_VARS + HARMONIZED_NET_PRICE_VARS
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
        "output_dir_root": str(output_root),
        "output_dir": str(output_dir),
        "output_panel": str(analysis_path),
        "output_panel_sha256": sha256_file(analysis_path),
        "selective_admissions_robustness_panel": str(selective_admissions_path),
        "selective_admissions_robustness_panel_sha256": sha256_file(selective_admissions_path),
        "years": years,
        "sectors": sectors,
        "sector_scope": sector_label,
        "title_iv_flag": title_iv_flag,
        "input_rows": int(len(df)),
        "year_window_rows": int(len(year_filtered)),
        "analysis_rows": int(len(analysis)),
        "analysis_unitids": int(analysis["UNITID"].nunique(dropna=True)),
        "selective_admissions_robustness_rows": int(len(selective_admissions)),
        "selective_admissions_robustness_unitids": int(selective_admissions["UNITID"].nunique(dropna=True)),
        "output_columns": int(len(analysis.columns)),
        "missing_optional_columns": missing_requested,
        "negative_net_price_counts": negative_net_price_counts,
        "artifacts": {
            "variable_manifest": str(manifest_path),
            "sample_counts": str(sample_counts_path),
            "panel_balance_by_institution": str(panel_balance_path),
            "panel_balance_summary": str(panel_balance_summary_path),
            "entry_exit_by_sector_year": str(entry_exit_path),
            "entry_exit_reason_audit": str(entry_exit_reason_path),
            "institution_years_by_sector_year": str(sector_year_path),
            "min_years_sensitivity": str(min_years_path),
            "selectivity_summary": str(selectivity_summary_path),
            "missingness_by_year": str(missingness_path),
            "value_sanity": str(value_sanity_path),
            "aid_zero_consistency": str(aid_zero_consistency_path),
            "aid_zero_suspect_rows": str(aid_zero_suspect_path),
            "metadata_flag_summary": str(metadata_summary_path),
            "metadata_code_summary": str(metadata_code_path),
        },
    }
    write_json(summary_path, summary)
    return summary


def prepare_analysis_outputs(
    input_panel: Path,
    dictionary: Path,
    output_dir: Path,
    variable_config: Path = DEFAULT_VARIABLE_CONFIG,
    years_spec: str = "2009:2023",
    sectors_spec: str | None = None,
    title_iv_flag: int = 1,
    include_forprofit_diagnostic: bool = False,
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for sector_spec in sector_output_specs(sectors_spec, include_forprofit_diagnostic):
        summaries.append(
            prepare_analysis_panel(
                input_panel=input_panel,
                dictionary=dictionary,
                output_dir=output_dir,
                variable_config=variable_config,
                years_spec=years_spec,
                sectors_spec=sector_spec,
                title_iv_flag=title_iv_flag,
            )
        )
    return summaries


def parse_args() -> argparse.Namespace:
    default_panel = default_input_panel()
    default_dict = default_dictionary()
    p = argparse.ArgumentParser(description="Prepare the COA/headroom research analysis panel.")
    p.add_argument("--input-panel", default=str(default_panel) if default_panel else None, help="Input clean IPEDS panel parquet")
    p.add_argument("--dictionary", default=str(default_dict) if default_dict else None, help="Input dictionary_lake parquet")
    p.add_argument("--variable-config", default=str(DEFAULT_VARIABLE_CONFIG), help="Variable-selection CSV")
    p.add_argument("--output-dir", default="outputs/analysis_panel", help="Output directory")
    p.add_argument("--years", default="2009:2023", help='Analysis years, for example "2009:2023"')
    p.add_argument(
        "--sectors",
        default=None,
        help="Comma-separated SECTOR codes. When omitted, writes baseline, public, and private nonprofit outputs.",
    )
    p.add_argument(
        "--include-forprofit-diagnostic",
        action="store_true",
        help="Also write the private for-profit diagnostic output.",
    )
    p.add_argument("--title-iv-flag", type=int, default=1, help="Required PSET4FLG value")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_panel:
        raise SystemExit("Provide --input-panel or set IPEDSDB_ROOT/IPEDS_ANALYSIS_PANEL")
    if not args.dictionary:
        raise SystemExit("Provide --dictionary or set IPEDSDB_ROOT/IPEDS_DICTIONARY")
    summaries = prepare_analysis_outputs(
        input_panel=Path(args.input_panel),
        dictionary=Path(args.dictionary),
        output_dir=Path(args.output_dir),
        variable_config=Path(args.variable_config),
        years_spec=args.years,
        sectors_spec=args.sectors,
        title_iv_flag=args.title_iv_flag,
        include_forprofit_diagnostic=args.include_forprofit_diagnostic,
    )
    for summary in summaries:
        print(
            "Wrote "
            f"{summary['output_panel']} rows={summary['analysis_rows']:,} "
            f"unitids={summary['analysis_unitids']:,} cols={summary['output_columns']:,}"
        )


if __name__ == "__main__":
    main()
