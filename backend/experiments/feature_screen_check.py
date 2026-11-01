"""Verification: the workbook's exploratory feature screen vs the vault boundary.

The raw workbook's Feature_Analysis sheet documents an exploratory screen
(MI + RF importance + XGB importance, each against Risk_Level and Outcome,
keep rule: any score >= 0.02 on either target, seed 42) computed on the full
dataset before the carve protocol existed. The official feature set is
availability-determined (every pre-execution column; structural drops only),
so the screen selects nothing — this script PROVES the decisions are also
insensitive to the vault boundary: the same screen, same implementation, is
computed on the full 176 AND on the 140-record selection pool; the keep/drop
decisions must match.

Run:  python -m backend.experiments.feature_screen_check
Writes: data/results/feature_screen_pool_check.json
"""
from __future__ import annotations
import datetime, json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import OrdinalEncoder
from xgboost import XGBClassifier

from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve

CANDIDATES = C.PRE_EXEC_FEATURES + C.EXEC_PHASE_FEATURES          # the 20 screened columns
THRESHOLD = 0.02


def _encode(df: pd.DataFrame) -> tuple[np.ndarray, list[bool]]:
    cats = [c for c in CANDIDATES if not pd.api.types.is_numeric_dtype(df[c])]
    X = df[CANDIDATES].copy()
    if cats:
        X[cats] = OrdinalEncoder().fit_transform(X[cats].astype(str))
    discrete = [c in cats or str(df[c].dtype).startswith("int") for c in CANDIDATES]
    return X.to_numpy(dtype=float), discrete


def _scores(df: pd.DataFrame, target: str) -> dict[str, dict[str, float]]:
    X, discrete = _encode(df)
    y = df[target].astype(str)
    classes = sorted(y.unique())
    y_enc = y.map({c: i for i, c in enumerate(classes)}).to_numpy()
    mi = mutual_info_classif(X, y_enc, discrete_features=discrete, random_state=C.SEED)
    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                random_state=C.SEED, n_jobs=-1).fit(X, y_enc).feature_importances_
    xgb = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.1,
                        objective="multi:softprob", eval_metric="mlogloss",
                        random_state=C.SEED, n_jobs=-1).fit(X, y_enc).feature_importances_
    return {f: {"mi": float(mi[i]), "rf": float(rf[i]), "xgb": float(xgb[i])}
            for i, f in enumerate(CANDIDATES)}


def _decisions(df: pd.DataFrame) -> dict[str, dict]:
    s_risk = _scores(df, C.TARGET_PRIMARY)
    s_out = _scores(df, C.TARGET_SECONDARY)
    out = {}
    for f in CANDIDATES:
        scores = {f"{m}_vs_Risk": s_risk[f][m] for m in ("mi", "rf", "xgb")}
        scores |= {f"{m}_vs_Outcome": s_out[f][m] for m in ("mi", "rf", "xgb")}
        out[f] = {"scores": {k: round(v, 4) for k, v in scores.items()},
                  "keep": bool(max(scores.values()) >= THRESHOLD),
                  "max_score": round(max(scores.values()), 4)}
    return out


def run() -> dict:
    processed, groups, _ = run_pipeline(save=False)
    tr, _te = vault_carve(processed, processed[C.TARGET_PRIMARY], groups)
    pool = processed.iloc[tr].reset_index(drop=True)
    assert len(pool) == 140, len(pool)

    full_d = _decisions(processed)
    pool_d = _decisions(pool)
    rows, changed = [], []
    for f in CANDIDATES:
        match = full_d[f]["keep"] == pool_d[f]["keep"]
        if not match:
            changed.append(f)
        rows.append({"feature": f,
                     "timing": "Pre-execution" if f in C.PRE_EXEC_FEATURES else "Execution-phase",
                     "keep_full_176": full_d[f]["keep"], "max_score_full": full_d[f]["max_score"],
                     "keep_pool_140": pool_d[f]["keep"], "max_score_pool": pool_d[f]["max_score"],
                     "decision_unchanged": match,
                     "scores_pool": pool_d[f]["scores"]})
    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "purpose": ("Prove the workbook's exploratory feature screen is insensitive to the "
                    "vault boundary: same implementation on 176 vs the 140-record pool."),
        "method": "MI + RF importance + XGB importance vs Risk_Level and Outcome; "
                  f"keep if any score >= {THRESHOLD}; seed {C.SEED}.",
        "note": ("The official feature set is availability-determined (all pre-execution "
                 "columns; structural drops only), so the screen never selected features; "
                 "this check additionally shows its decisions do not depend on vault rows."),
        "n_candidates": len(CANDIDATES),
        "decisions_changed": changed,
        "all_decisions_unchanged": not changed,
        "features": rows,
    }
    out = C.RESULTS_DIR / "feature_screen_pool_check.json"
    out.write_text(json.dumps(report, indent=1))
    print(f"candidates: {len(CANDIDATES)} | decisions changed between 176 and pool: {len(changed)}")
    for r in rows:
        flag = "OK " if r["decision_unchanged"] else "CHANGED"
        print(f"  {flag} {r['feature']:28s} keep(full)={r['keep_full_176']} "
              f"keep(pool)={r['keep_pool_140']} max_pool={r['max_score_pool']}")
    return report


if __name__ == "__main__":
    run()
