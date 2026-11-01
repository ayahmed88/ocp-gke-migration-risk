"""Exact per-case attribution for the winning Logistic Regression model.

For a linear model on the transformed space, the contribution of transformed
column j to class-c log-odds relative to the background mean is exactly
    contrib[c, j] = coef[c, j] * (x_t[j] - mu[j])
which coincides with SHAP's LinearExplainer (interventional, independent
features). We aggregate transformed columns back to the ORIGINAL features
(summing a categorical's one-hot dummies) so the explanation reads in the
vocabulary of the migration record. Wording everywhere: predictive
association — NOT causation.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from backend.core import config as C


def _readable(name: str, case_row: dict) -> tuple[str, str]:
    """Transformed column name -> (original_feature, display label)."""
    kind, rest = name.split("__", 1)
    if kind == "nom":
        for col in C.NOMINAL_COLS:
            if rest.startswith(col + "_"):
                return col, f"{col} = {case_row.get(col, rest[len(col)+1:])}"
    if kind == "ord" or kind == "num":
        return rest, f"{rest} = {case_row.get(rest, '')}"
    return rest, rest


def _parts(model):
    prep = model.named_steps["prep"]
    clf = model.named_steps["clf"]
    names = list(prep.get_feature_names_out())
    return prep, clf, names


def background_mean(model, X_train: pd.DataFrame) -> np.ndarray:
    prep, _, _ = _parts(model)
    Xt = prep.transform(X_train)
    Xt = Xt.toarray() if hasattr(Xt, "toarray") else np.asarray(Xt)
    return Xt.mean(axis=0)


def explain_case(model, mu: np.ndarray, case: pd.DataFrame,
                 classes: list[str], pred_class: str, top_k: int = 8) -> dict:
    prep, clf, names = _parts(model)
    xt = prep.transform(case)
    xt = (xt.toarray() if hasattr(xt, "toarray") else np.asarray(xt))[0]
    ci = classes.index(pred_class)                      # clf.classes_ == [0..k-1]
    contrib_t = clf.coef_[ci] * (xt - mu)

    row = case.iloc[0].to_dict()
    agg: dict[str, dict] = {}
    for j, n in enumerate(names):
        feat, label = _readable(n, row)
        a = agg.setdefault(feat, {"feature": feat, "label": label, "contribution": 0.0})
        a["contribution"] += float(contrib_t[j])
    items = sorted(agg.values(), key=lambda d: -abs(d["contribution"]))
    for d in items:
        d["contribution"] = round(d["contribution"], 4)
        d["direction"] = "raises" if d["contribution"] > 0 else "lowers"
    return {"explained_class": pred_class,
            "unit": "log-odds contribution vs dataset average case",
            "wording": "predictive association — not causation",
            "contributions": items[:top_k]}


def global_coefficients(model, classes: list[str]) -> list[dict]:
    """Winner's global view: transformed-level coefficients per class."""
    _, clf, names = _parts(model)
    out = []
    for ci, cls in enumerate(classes):
        for j, n in enumerate(names):
            kind, rest = n.split("__", 1)
            out.append({"class": cls, "feature": rest.replace("_", " = ", 1) if kind == "nom" else rest,
                        "coef": round(float(clf.coef_[ci][j]), 4),
                        "unit": "per +1 SD" if kind == "num" else
                                ("per ordinal step" if kind == "ord" else "vs category absent")})
    return out
