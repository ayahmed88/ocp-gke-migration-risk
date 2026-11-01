"""Explainability layer (Phase 4B) — for the declared primary model (LR).

Methods (chosen per the research plan's option list, with rationale):
1. GLOBAL — model coefficients: for a multinomial LR on standardised numerics
   and one-hot categoricals, coefficients are the model's exact global logic;
   we report them per class with odds ratios (exp(coef)).
2. GLOBAL — grouped permutation importance: model-agnostic check computed on
   the SAME Repeated StratifiedGroupKFold folds as every other result
   (permute one raw column in the outer-test fold; measure Macro-F1 drop).
3. PER-CASE — exact additive attribution: contribution_i = coef[class,i] · x_i
   in the transformed space, aggregated back to the 13 original features.
   For a linear model this is exact (equivalent to SHAP with a mean baseline,
   since numerics are standardised to mean 0).

Wording rule enforced everywhere: these are associations the model relies on
for PREDICTION — never causal claims.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score

from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.models.factory import make_model

CACHE = C.RESULTS_DIR / "xai_global.json"
PERM_REPEATS = 3


# ------------------------------------------------------------ name mapping --
def _base_and_label(trans_name: str) -> tuple[str, str]:
    """'nom__Owner_Availability_Delayed' -> ('Owner_Availability',
    'Owner_Availability = Delayed'); ordinal/numeric pass through."""
    kind, rest = trans_name.split("__", 1)
    if kind == "nom":
        for col in C.NOMINAL_COLS:
            if rest.startswith(col + "_"):
                return col, f"{col} = {rest[len(col) + 1:]}"
    return rest, rest


def _fit_full_lr():
    """Global-explanation fit — A2 option 1: the 140-record selection pool,
    the same scope as every evaluation figure (vault untouched)."""
    from backend.experiments.split import vault_carve
    processed, groups, _ = run_pipeline(save=False)
    tr, _te = vault_carve(processed, processed[C.TARGET_PRIMARY], groups)
    processed = processed.iloc[tr].reset_index(drop=True)
    groups = groups.iloc[tr].reset_index(drop=True)
    X = processed[C.PRE_EXEC_FEATURES]
    y_enc = processed[C.TARGET_PRIMARY].map(
        {c: i for i, c in enumerate(C.RISK_CLASSES)}).astype(int)
    model = make_model("Logistic Regression", C.PRE_EXEC_FEATURES)
    model.fit(X, y_enc)
    return model, processed, groups, y_enc


# ---------------------------------------------------------------- global ----
def _coefficient_tables(model) -> dict:
    prep, clf = model.named_steps["prep"], model.named_steps["clf"]
    names = list(prep.get_feature_names_out())
    out = {}
    for ci, cls in enumerate(C.RISK_CLASSES):
        rows = []
        for j, n in enumerate(names):
            base, label = _base_and_label(n)
            coef = float(clf.coef_[ci, j])
            rows.append({"feature": base, "label": label,
                         "coef": round(coef, 4),
                         "odds_ratio": round(float(np.exp(coef)), 3)})
        rows.sort(key=lambda r: r["coef"], reverse=True)
        out[cls] = rows
    return out


def _grouped_permutation_importance(seed_rng: int = 7) -> list[dict]:
    _, processed, groups, y_enc = _fit_full_lr()
    X = processed[C.PRE_EXEC_FEATURES]
    rng = np.random.default_rng(seed_rng)
    drops: dict[str, list[float]] = {f: [] for f in C.PRE_EXEC_FEATURES}
    for rep in range(C.CV_N_REPEATS):
        skf = StratifiedGroupKFold(n_splits=C.CV_N_SPLITS, shuffle=True,
                                   random_state=C.SEED + rep)
        for tr, te in skf.split(X, y_enc, groups):
            m = make_model("Logistic Regression", C.PRE_EXEC_FEATURES)
            m.fit(X.iloc[tr], y_enc.iloc[tr])
            Xte = X.iloc[te]
            base = f1_score(y_enc.iloc[te], m.predict(Xte),
                            average="macro", zero_division=0)
            for f in C.PRE_EXEC_FEATURES:
                scores = []
                for _ in range(PERM_REPEATS):
                    Xp = Xte.copy()
                    Xp[f] = rng.permutation(Xp[f].to_numpy())
                    scores.append(f1_score(y_enc.iloc[te], m.predict(Xp),
                                           average="macro", zero_division=0))
                drops[f].append(base - float(np.mean(scores)))
    return sorted(
        [{"feature": f, "f1_drop_mean": round(float(np.mean(v)), 4),
          "f1_drop_std": round(float(np.std(v)), 4)} for f, v in drops.items()],
        key=lambda r: r["f1_drop_mean"], reverse=True)


def global_explanations(force: bool = False) -> dict:
    if CACHE.exists() and not force:
        return json.loads(CACHE.read_text())
    model, *_ = _fit_full_lr()
    data = {
        "model": "Logistic Regression (declared primary; defaults, balanced)",
        "method_note": ("Coefficients are the model's exact global logic (odds ratios per "
                        "one-unit / category change); permutation importance is computed on the "
                        "same 25 grouped CV folds. Associations used for prediction — not causal claims."),
        "fit_scope": "140-record selection pool / 70 services (A2 option 1)",
        "coefficients_per_class": _coefficient_tables(model),
        "permutation_importance": _grouped_permutation_importance(),
    }
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, indent=1))
    return data


# --------------------------------------------------------------- per-case ---
def per_case(model, X_row: pd.DataFrame, class_code: int) -> dict:
    """Exact additive attribution for one prediction of a fitted LR pipeline."""
    prep, clf = model.named_steps["prep"], model.named_steps["clf"]
    x = prep.transform(X_row)
    x = np.asarray(x.todense()).ravel() if hasattr(x, "todense") else np.asarray(x).ravel()
    names = list(prep.get_feature_names_out())
    agg: dict[str, dict] = {}
    for j, n in enumerate(names):
        base, label = _base_and_label(n)
        c = float(clf.coef_[class_code, j]) * float(x[j])
        if abs(c) < 1e-12:
            continue
        a = agg.setdefault(base, {"feature": base, "label": label, "contribution": 0.0})
        a["contribution"] += c
        if "= " in label and float(x[j]) != 0:      # active category names the label
            a["label"] = label
    items = sorted(agg.values(), key=lambda r: abs(r["contribution"]), reverse=True)
    for it in items:
        it["contribution"] = round(it["contribution"], 4)
    return {"class": C.RISK_CLASSES[class_code],
            "intercept": round(float(clf.intercept_[class_code]), 4),
            "contributions": items,
            "note": "Exact linear attributions toward this class's logit "
                    "(positive pushes toward it). Association, not causation."}
