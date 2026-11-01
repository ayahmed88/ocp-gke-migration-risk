"""Data loading + documented cleaning (RAW -> processed) with an audit trail.

Design (approved decisions F1/F5):
- The ORIGINAL workbook is never modified. We read the RAW sheet only.
- Cleaning is executed here, in code, so it is reproducible and visible in the app.
- The workbook's human-made CLEANED sheet is used as a verification ORACLE:
  our cleaning output must match it cell-for-cell (plus the retained group key).
"""
from __future__ import annotations
import json, datetime
import pandas as pd

from backend.core import config as C


def load_raw() -> pd.DataFrame:
    df = pd.read_excel(C.RAW_XLSX, sheet_name=C.RAW_SHEET)
    return df


def integrity_checks(df: pd.DataFrame) -> dict:
    """Hard gates — fail loudly if the file is not the expected research dataset."""
    checks = {
        "shape_176x27": df.shape == (176, 27),
        "migration_id_unique": df["Migration_ID"].is_unique,
        "services_88_x2": df[C.GROUP_COL].nunique() == 88
                          and (df[C.GROUP_COL].value_counts() == 2).all(),
        "dev_qa_pair_per_service": bool(
            df.groupby(C.GROUP_COL)["Environment"]
              .apply(lambda s: sorted(s) == ["Dev", "QA"]).all()),
        "no_duplicate_rows": int(df.duplicated().sum()) == 0,
        "db_type_nan_structural": bool(
            df.loc[df.Has_DB_Dependency == 0, "DB_Type"].isna().all()
            and df.loc[df.Has_DB_Dependency == 1, "DB_Type"].notna().all()),
    }
    checks = {k: bool(v) for k, v in checks.items()}     # numpy.bool_ -> native bool (JSON-safe)
    checks["all_passed"] = all(checks.values())
    return checks


def clean(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[dict]]:
    """Return (processed_df, groups, audit_log).

    processed_df = model-ready table (features + targets), group key retained
    separately so it can never be used as a feature by mistake.
    """
    audit: list[dict] = []
    ts = datetime.datetime.now().isoformat(timespec="seconds")

    def log(step: str, detail: str, n: int):
        audit.append({"ts": ts, "step": step, "detail": detail, "rows_affected": n})

    df = df_raw.copy()
    groups = df[C.GROUP_COL].copy()

    df = df.drop(columns=C.ID_COLS)
    log("drop_identifiers", f"dropped {C.ID_COLS} (Service_Code retained separately as CV grouping key)", len(df))

    df = df.drop(columns=C.CONSTANT_COLS)
    log("drop_constants", f"dropped {C.CONSTANT_COLS} (constant OCP/GKE in all rows)", len(df))

    n_fill = int(df["DB_Type"].isna().sum())
    df["DB_Type"] = df["DB_Type"].fillna(C.DB_TYPE_FILL)
    log("fill_db_type", f"structural NaN (no DB dependency) -> category '{C.DB_TYPE_FILL}'", n_fill)

    assert df.isna().sum().sum() == 0, "unexpected missing values after cleaning"
    log("assert_no_missing", "0 missing values in processed table", len(df))
    return df, groups, audit


def verify_against_cleaned_reference(processed: pd.DataFrame) -> dict:
    """Prove our code reproduces the author's hand-made CLEANED sheet.

    Known, documented difference (finding F1, pending the author's decision):
    the reference sheet did NOT actually apply the DB_Type fill its README
    describes — so we compare against the reference WITH the fill applied,
    which is the documented intent.
    """
    ref = pd.read_excel(C.RAW_XLSX, sheet_name=C.CLEANED_REF_SHEET)
    ref["DB_Type"] = ref["DB_Type"].fillna(C.DB_TYPE_FILL)          # documented intent (F1)
    same_cols = set(ref.columns) == set(processed.columns)          # RAW orders targets Outcome,Risk_Level;
    equal = same_cols and processed[list(ref.columns)].reset_index(drop=True).equals(
        ref.reset_index(drop=True))                                  # CLEANED swaps them -> compare in ref order
    return {"columns_match": bool(same_cols), "values_match_documented_intent": bool(equal)}


def run(save: bool = True):
    raw = load_raw()
    checks = integrity_checks(raw)
    if not checks["all_passed"]:
        raise RuntimeError(f"Integrity gate failed: {checks}")
    processed, groups, audit = clean(raw)
    verification = verify_against_cleaned_reference(processed)
    if save:
        C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        processed.assign(**{C.GROUP_COL: groups}).to_csv(
            C.PROCESSED_DIR / "processed_dataset.csv", index=False)
        (C.PROCESSED_DIR / "cleaning_audit_log.jsonl").write_text(
            "\n".join(json.dumps(a) for a in audit))
        (C.PROCESSED_DIR / "integrity_checks.json").write_text(
            json.dumps({"integrity": checks, "cleaned_ref_verification": verification}, indent=2))
    return processed, groups, {"integrity": checks, "verification": verification, "audit": audit}
