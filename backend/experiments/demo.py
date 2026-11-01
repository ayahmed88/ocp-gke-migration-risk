"""Defense-session controls (v19).

reset_session(): clears ONLY the reproducible session state (serving models,
baseline results, XAI cache) so the committee can watch everything rebuild
live. It NEVER touches: raw data, the sealed holdout report, tuning/winner
records, sensitivity evidence, or exports.

ensure_vault_model(): the exact model of the sealed holdout (same seed, same
80/20 group split -> byte-identical refit), persisted once and kept through
resets, so the random unseen-case tester is always honest.

random_unseen_case(): draws a record from the sealed 20% vault (never seen in
training), predicts it, then reveals the expert label.
"""
from __future__ import annotations
import json, random
import joblib
from backend.experiments.split import vault_carve

from backend.core import config as C
from backend.data.pipeline import run as run_pipeline, load_raw
from backend.models.factory import make_model

VAULT_MODEL = C.ARTIFACTS_DIR / "vault_model.joblib"
SESSION_RESULTS = ["phase3a_baseline_results.csv", "phase3a_manifest.json",
                   "xai_global.json"]


def reset_session() -> dict:
    cleared = []
    if C.ARTIFACTS_DIR.exists():
        for p in list(C.ARTIFACTS_DIR.iterdir()):
            if p.name == VAULT_MODEL.name:          # the seal survives
                continue
            p.unlink(); cleared.append(f"artifacts/{p.name}")
    for name in SESSION_RESULTS:
        f = C.RESULTS_DIR / name
        if f.exists():
            f.unlink(); cleared.append(f"results/{name}")
    from backend.models import registry
    registry._cache.clear()
    return {"cleared": sorted(cleared),
            "kept": ["raw dataset", "sealed holdout report + vault model",
                     "tuning & winner records", "seed/feature sensitivity",
                     "exports", "file vault"]}


def _vault_split():
    processed, groups, _ = run_pipeline(save=False)
    X = processed[C.PRE_EXEC_FEATURES]
    y = processed[C.TARGET_PRIMARY].map(
        {c: i for i, c in enumerate(C.RISK_CLASSES)}).astype(int)
    tr, te = vault_carve(X, y, groups)
    return processed, X, y, tr, te


def ensure_vault_model():
    if VAULT_MODEL.exists():
        return joblib.load(VAULT_MODEL)
    _, X, y, tr, _ = _vault_split()
    m = make_model("Logistic Regression", C.PRE_EXEC_FEATURES)
    m.fit(X.iloc[tr], y.iloc[tr])
    C.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(m, VAULT_MODEL)
    return m


def vault_records() -> dict:
    """Full roster of the sealed 20% vault, derived deterministically from the
    seed and checked against the sealed confusion matrix."""
    from collections import Counter
    m = ensure_vault_model()
    processed, X, y, _, te = _vault_split()
    raw = load_raw()
    recs = []
    for i in sorted(int(j) for j in te):
        pred = C.RISK_CLASSES[int(m.predict(X.iloc[[i]])[0])]
        true = C.RISK_CLASSES[int(y.iloc[i])]
        recs.append({"service": str(raw.iloc[i]["Service_Code"]),
                     "migration_id": str(raw.iloc[i]["Migration_ID"]),
                     "environment": str(raw.iloc[i]["Environment"]),
                     "true": true, "pred": pred, "match": pred == true})
    recs.sort(key=lambda r: (r["service"], r["environment"]))
    idx = {c: k for k, c in enumerate(C.RISK_CLASSES)}
    mat = [[0] * 3 for _ in range(3)]
    for r in recs:
        mat[idx[r["true"]]][idx[r["pred"]]] += 1
    matches = None
    f = C.RESULTS_DIR / "holdout_report.json"
    if f.exists():
        sealed = json.loads(f.read_text()).get("confusion", {})
        matches = (sealed.get("matrix") == mat)
    return {"records": recs, "hits": sum(r["match"] for r in recs),
            "total": len(recs),
            "class_counts": dict(Counter(r["true"] for r in recs)),
            "matches_seal": matches}


def vault_case(migration_id: str) -> dict:
    """Live prediction on one specific sealed-vault record (chosen freely)."""
    m = ensure_vault_model()
    processed, X, y, _, te = _vault_split()
    raw = load_raw()
    idx = {str(raw.iloc[int(j)]["Migration_ID"]): int(j) for j in te}
    if migration_id not in idx:
        raise KeyError(migration_id)
    i = idx[migration_id]
    row = X.iloc[[i]]
    probs = {C.RISK_CLASSES[int(c)]: round(float(p), 3)
             for c, p in zip(m.classes_, m.predict_proba(row)[0])}
    pred = C.RISK_CLASSES[int(m.predict(row)[0])]
    true = C.RISK_CLASSES[int(y.iloc[i])]
    return {"migration_id": migration_id, "probabilities": probs,
            "predicted": pred, "true": true, "match": pred == true}


def random_unseen_case() -> dict:
    m = ensure_vault_model()
    processed, X, y, _, te = _vault_split()
    raw = load_raw()
    i = int(random.choice(list(te)))
    row = X.iloc[[i]]
    probs = {C.RISK_CLASSES[int(c)]: round(float(p), 3)
             for c, p in zip(m.classes_, m.predict_proba(row)[0])}
    pred = C.RISK_CLASSES[int(m.predict(row)[0])]
    true = C.RISK_CLASSES[int(y.iloc[i])]
    feats = {k: str(processed.iloc[i][k]) for k in
             ("Environment", "Business_Criticality", "Complexity_Level",
              "Has_DB_Dependency", "Firewall_Rules_Count", "Owner_Availability")}
    return {"migration_id": str(raw.iloc[i]["Migration_ID"]),
            "features": feats, "probabilities": probs,
            "predicted": pred, "true": true, "match": pred == true,
            "vault_size": int(len(te)),
            "note": "Drawn from the sealed 20% vault — the model never trained on this record."}
