from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype


IDENTIFIER_COLUMNS = ("UNITID", "year", "INSTNM", "OPEID", "SECTOR", "CONTROL")
CODE_LIKE_COLUMNS = {
    "UNITID",
    "year",
    "OPEID",
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
    "CBSA",
    "CBSATYPE",
    "CSA",
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
}
CODE_LIKE_PREFIXES = ("IMP_", "LOCK_", "REV_", "IDX_", "PRCH_", "PC")
NEGATIVE_ALLOWED_PREFIXES = ("SELECTIVITY_",)
NEGATIVE_ALLOWED_EXACT = {"LATITUDE", "LONGITUD"}
PROFILE_QUANTILES = (0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999)
PROFILE_QUANTILE_NAMES = {
    0.001: "p001",
    0.01: "p01",
    0.05: "p05",
    0.25: "p25",
    0.5: "p50",
    0.75: "p75",
    0.95: "p95",
    0.99: "p99",
    0.999: "p999",
}


def infer_scope(input_panel: Path, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    parent = input_panel.parent.name
    if parent:
        return parent
    return input_panel.stem


def classify_column(series: pd.Series) -> str:
    if is_bool_dtype(series):
        return "boolean"
    if is_numeric_dtype(series):
        return "numeric"
    nonnull = series.notna().sum()
    if nonnull == 0:
        return "empty"
    converted = pd.to_numeric(series, errors="coerce")
    if converted.notna().sum() / nonnull >= 0.95:
        return "numeric_like"
    return "categorical"


def numeric_series(series: pd.Series) -> pd.Series:
    if is_bool_dtype(series):
        return series.astype("Float64")
    return pd.to_numeric(series, errors="coerce")


def dataset_shape(df: pd.DataFrame, input_panel: Path, scope: str) -> pd.DataFrame:
    logical_types = pd.Series({col: classify_column(df[col]) for col in df.columns})
    duplicate_keys = 0
    if {"UNITID", "year"} <= set(df.columns):
        duplicate_keys = int(df.duplicated(["UNITID", "year"]).sum())
    years = numeric_series(df["year"]) if "year" in df.columns else pd.Series(dtype="Float64")
    return pd.DataFrame(
        [
            {
                "scope": scope,
                "input_panel": str(input_panel),
                "rows": int(len(df)),
                "columns": int(len(df.columns)),
                "unitids": int(df["UNITID"].nunique(dropna=True)) if "UNITID" in df.columns else 0,
                "min_year": None if years.dropna().empty else int(years.min()),
                "max_year": None if years.dropna().empty else int(years.max()),
                "duplicate_unitid_year_rows": duplicate_keys,
                "memory_bytes": int(df.memory_usage(deep=True).sum()),
                "numeric_columns": int(logical_types.isin(["numeric", "numeric_like"]).sum()),
                "categorical_columns": int(logical_types.eq("categorical").sum()),
                "boolean_columns": int(logical_types.eq("boolean").sum()),
                "empty_columns": int(logical_types.eq("empty").sum()),
            }
        ]
    )


def profile_numeric(series: pd.Series) -> dict[str, object]:
    s = numeric_series(series)
    nonnull = s.dropna()
    row: dict[str, object] = {
        "zero_count": int(s.eq(0).sum()),
        "negative_count": int(s.lt(0).sum()),
    }
    if nonnull.empty:
        row.update(
            {
                "min": None,
                "max": None,
                "mean": None,
                "std": None,
                "skew": None,
                "iqr": None,
                "lower_inner_fence": None,
                "upper_inner_fence": None,
                "lower_outer_fence": None,
                "upper_outer_fence": None,
                "extreme_low_count": 0,
                "extreme_high_count": 0,
                "p99_to_p50_ratio": None,
                "max_to_p99_ratio": None,
            }
        )
        for name in PROFILE_QUANTILE_NAMES.values():
            row[name] = None
        return row

    quantiles = nonnull.quantile(list(PROFILE_QUANTILES), interpolation="linear")
    for q, name in PROFILE_QUANTILE_NAMES.items():
        row[name] = float(quantiles.loc[q])

    p25 = float(quantiles.loc[0.25])
    p50 = float(quantiles.loc[0.5])
    p75 = float(quantiles.loc[0.75])
    p99 = float(quantiles.loc[0.99])
    iqr = p75 - p25
    lower_inner = p25 - 1.5 * iqr
    upper_inner = p75 + 1.5 * iqr
    lower_outer = p25 - 3.0 * iqr
    upper_outer = p75 + 3.0 * iqr
    max_value = float(nonnull.max())
    row.update(
        {
            "min": float(nonnull.min()),
            "max": max_value,
            "mean": float(nonnull.mean()),
            "std": None if pd.isna(nonnull.std()) else float(nonnull.std()),
            "skew": None if pd.isna(nonnull.skew()) else float(nonnull.skew()),
            "iqr": float(iqr),
            "lower_inner_fence": float(lower_inner),
            "upper_inner_fence": float(upper_inner),
            "lower_outer_fence": float(lower_outer),
            "upper_outer_fence": float(upper_outer),
            "extreme_low_count": int(s.lt(lower_outer).sum()),
            "extreme_high_count": int(s.gt(upper_outer).sum()),
            "p99_to_p50_ratio": None if p50 == 0 else float(p99 / p50),
            "max_to_p99_ratio": None if p99 == 0 else float(max_value / p99),
        }
    )
    return row


def variable_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_rows = len(df)
    for position, col in enumerate(df.columns, start=1):
        series = df[col]
        nonnull = int(series.notna().sum())
        logical_type = classify_column(series)
        row: dict[str, object] = {
            "position": position,
            "varname": col,
            "dtype": str(series.dtype),
            "logical_type": logical_type,
            "rows": total_rows,
            "nonnull": nonnull,
            "missing": total_rows - nonnull,
            "missing_share": (total_rows - nonnull) / total_rows if total_rows else 0.0,
            "unique_nonnull": int(series.nunique(dropna=True)),
        }
        if logical_type in {"numeric", "numeric_like", "boolean"}:
            row.update(profile_numeric(series))
        else:
            row.update(
                {
                    "zero_count": None,
                    "negative_count": None,
                    "min": None,
                    "p001": None,
                    "p01": None,
                    "p05": None,
                    "p25": None,
                    "p50": None,
                    "p75": None,
                    "p95": None,
                    "p99": None,
                    "p999": None,
                    "max": None,
                    "mean": None,
                    "std": None,
                    "skew": None,
                    "iqr": None,
                    "lower_inner_fence": None,
                    "upper_inner_fence": None,
                    "lower_outer_fence": None,
                    "upper_outer_fence": None,
                    "extreme_low_count": None,
                    "extreme_high_count": None,
                    "p99_to_p50_ratio": None,
                    "max_to_p99_ratio": None,
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def variable_group(varname: str) -> str:
    if varname in IDENTIFIER_COLUMNS:
        return "identifier"
    if varname.startswith(("COA_", "HEADROOM_")):
        return "derived_coa_headroom"
    if varname.startswith(("FIN_", "LN_FIN_")):
        return "derived_finance"
    if varname.startswith(("NET_PRICE_", "NPI", "NPT", "NPGRN")):
        return "net_price"
    if varname.startswith(("FLAG_",)):
        return "flag"
    if any(varname.startswith(prefix) for prefix in ("AGRNT", "FGRNT", "PGRNT", "SGRNT", "OFGRT", "IGRNT", "LOAN", "FLOAN", "OLOAN")):
        return "ftft_aid"
    if any(varname.startswith(prefix) for prefix in ("UAGRNT", "UFLOAN", "UPGRNT")):
        return "undergraduate_aid"
    if varname in {"APPLCN", "ADMSSN", "ENRLT"} or varname.startswith(("SAT", "ACT", "SELECTIVITY", "OPEN_", "VALID_", "TEST_SCORE")):
        return "admissions_selectivity"
    if varname.startswith(("CHG", "TUITION", "FEE")):
        return "charges"
    return "other"


def is_code_like(varname: str, logical_type: str) -> bool:
    if logical_type == "boolean":
        return True
    if varname in CODE_LIKE_COLUMNS:
        return True
    if varname.startswith(CODE_LIKE_PREFIXES):
        return True
    if varname.startswith("FLAG_"):
        return True
    return False


def negative_values_need_review(varname: str) -> bool:
    if variable_group(varname) == "net_price":
        return False
    if varname in NEGATIVE_ALLOWED_EXACT:
        return False
    if varname.startswith(NEGATIVE_ALLOWED_PREFIXES):
        return False
    if is_code_like(varname, "numeric"):
        return False
    return True


def review_candidates(profile: pd.DataFrame) -> pd.DataFrame:
    numeric = profile[profile["logical_type"].isin(["numeric", "numeric_like"])].copy()
    rows: list[dict[str, object]] = []
    for row in numeric.to_dict("records"):
        varname = str(row["varname"])
        if is_code_like(varname, str(row["logical_type"])):
            continue
        reasons: list[str] = []
        if (row.get("extreme_low_count") or 0) > 0:
            reasons.append("below_outer_iqr_fence")
        if (row.get("extreme_high_count") or 0) > 0:
            reasons.append("above_outer_iqr_fence")
        max_to_p99 = row.get("max_to_p99_ratio")
        if pd.notna(max_to_p99) and max_to_p99 is not None and max_to_p99 >= 3:
            reasons.append("max_at_least_3x_p99")
        p99_to_p50 = row.get("p99_to_p50_ratio")
        if pd.notna(p99_to_p50) and p99_to_p50 is not None and p99_to_p50 >= 10:
            reasons.append("p99_at_least_10x_median")
        if (row.get("negative_count") or 0) > 0 and negative_values_need_review(varname):
            reasons.append("negative_values")
        if not reasons:
            continue
        rows.append(
            {
                "varname": varname,
                "variable_group": variable_group(varname),
                "logical_type": row["logical_type"],
                "nonnull": row["nonnull"],
                "missing_share": row["missing_share"],
                "min": row["min"],
                "p01": row["p01"],
                "p50": row["p50"],
                "p99": row["p99"],
                "max": row["max"],
                "negative_count": row["negative_count"],
                "extreme_low_count": row["extreme_low_count"],
                "extreme_high_count": row["extreme_high_count"],
                "p99_to_p50_ratio": row["p99_to_p50_ratio"],
                "max_to_p99_ratio": row["max_to_p99_ratio"],
                "review_reason": ";".join(reasons),
                "candidate_action": "review_before_winsorizing",
            }
        )
    return pd.DataFrame(rows).sort_values(["variable_group", "varname"]).reset_index(drop=True)


def extreme_rows(df: pd.DataFrame, profile: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    id_cols = [col for col in IDENTIFIER_COLUMNS if col in df.columns]
    rows: list[dict[str, object]] = []
    numeric_vars = profile[profile["logical_type"].isin(["numeric", "numeric_like"])]["varname"].tolist()
    for varname in numeric_vars:
        s = numeric_series(df[varname])
        if s.dropna().empty:
            continue
        var_profile = profile.loc[profile["varname"] == varname].iloc[0]
        for direction, values in (("low", s.nsmallest(top_n)), ("high", s.nlargest(top_n))):
            for rank, (idx, value) in enumerate(values.items(), start=1):
                row = {
                    "varname": varname,
                    "variable_group": variable_group(str(varname)),
                    "direction": direction,
                    "rank": rank,
                    "value": float(value),
                    "p01": var_profile["p01"],
                    "p50": var_profile["p50"],
                    "p99": var_profile["p99"],
                    "lower_outer_fence": var_profile["lower_outer_fence"],
                    "upper_outer_fence": var_profile["upper_outer_fence"],
                }
                for col in id_cols:
                    row[col] = df.at[idx, col]
                rows.append(row)
    return pd.DataFrame(rows)


def year_distribution(df: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    columns = ["year", "varname", "nonnull", "missing", "min", "p01", "p50", "p99", "max"]
    if "year" not in df.columns:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    numeric_vars = profile[profile["logical_type"].isin(["numeric", "numeric_like"])]["varname"].tolist()
    for year, group in df.groupby("year", dropna=False, sort=True):
        for varname in numeric_vars:
            s = numeric_series(group[varname])
            nonnull = s.dropna()
            if nonnull.empty:
                rows.append({"year": year, "varname": varname, "nonnull": 0, "missing": int(len(group)), "min": None, "p01": None, "p50": None, "p99": None, "max": None})
                continue
            q = nonnull.quantile([0.01, 0.5, 0.99])
            rows.append(
                {
                    "year": year,
                    "varname": varname,
                    "nonnull": int(nonnull.count()),
                    "missing": int(len(group) - nonnull.count()),
                    "min": float(nonnull.min()),
                    "p01": float(q.loc[0.01]),
                    "p50": float(q.loc[0.5]),
                    "p99": float(q.loc[0.99]),
                    "max": float(nonnull.max()),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def categorical_profile(df: pd.DataFrame, profile: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    cat_vars = profile[profile["logical_type"].isin(["categorical", "boolean", "empty"])]["varname"].tolist()
    for varname in cat_vars:
        counts = df[varname].value_counts(dropna=False).head(top_n)
        for rank, (value, count) in enumerate(counts.items(), start=1):
            rows.append(
                {
                    "varname": varname,
                    "rank": rank,
                    "value": "" if pd.isna(value) else str(value),
                    "count": int(count),
                    "share": float(count / len(df)) if len(df) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def audit_extremes(
    input_panel: Path,
    output_dir: Path,
    scope_label: str | None = None,
    top_n: int = 10,
) -> dict[str, Path]:
    if not input_panel.exists():
        raise SystemExit(f"Input panel does not exist: {input_panel}")
    scope = infer_scope(input_panel, scope_label)
    scoped_output = output_dir / scope
    scoped_output.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(input_panel)
    shape = dataset_shape(df, input_panel, scope)
    profile = variable_profile(df)
    profile["variable_group"] = profile["varname"].map(variable_group)
    candidates = review_candidates(profile)
    extremes = extreme_rows(df, profile, top_n=top_n)
    by_year = year_distribution(df, profile)
    categorical = categorical_profile(df, profile, top_n=top_n)

    paths = {
        "dataset_shape": scoped_output / "extreme_audit_dataset_shape.csv",
        "variable_profile": scoped_output / "extreme_audit_variable_profile.csv",
        "review_candidates": scoped_output / "extreme_audit_review_candidates.csv",
        "extreme_rows": scoped_output / "extreme_audit_top_rows.csv",
        "year_distribution": scoped_output / "extreme_audit_by_year_distribution.csv",
        "categorical_profile": scoped_output / "extreme_audit_categorical_profile.csv",
        "summary": scoped_output / "extreme_audit_summary.json",
    }
    shape.to_csv(paths["dataset_shape"], index=False)
    profile.to_csv(paths["variable_profile"], index=False)
    candidates.to_csv(paths["review_candidates"], index=False)
    extremes.to_csv(paths["extreme_rows"], index=False)
    by_year.to_csv(paths["year_distribution"], index=False)
    categorical.to_csv(paths["categorical_profile"], index=False)

    summary = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_panel": str(input_panel),
        "scope": scope,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "numeric_or_numeric_like_columns": int(profile["logical_type"].isin(["numeric", "numeric_like"]).sum()),
        "review_candidate_columns": int(len(candidates)),
        "extreme_row_records": int(len(extremes)),
        "outputs": {key: str(value) for key, value in paths.items() if key != "summary"},
    }
    write_json(paths["summary"], summary)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit analysis-panel variable distributions and extreme values.")
    parser.add_argument("--input-panel", type=Path, action="append", required=True, help="Analysis panel parquet to audit. Can be passed more than once.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/extreme_audit"), help="Directory for generated audit files.")
    parser.add_argument("--scope-label", default=None, help="Optional scope label. Only use with one input panel.")
    parser.add_argument("--top-n", type=int, default=10, help="Top and bottom rows to retain per numeric variable.")
    args = parser.parse_args()

    if args.scope_label and len(args.input_panel) != 1:
        raise SystemExit("--scope-label can only be used with one --input-panel")

    for panel in args.input_panel:
        paths = audit_extremes(panel, args.output_dir, args.scope_label, args.top_n)
        print(f"Wrote {paths['summary'].parent}")


if __name__ == "__main__":
    main()
