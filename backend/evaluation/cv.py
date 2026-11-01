"""Repeated, group-aware, stratified cross-validation (the defensible design).

Unit of analysis: one migration activity (service x environment).
Groups: Service_Code — both rows of a service always fall on the same side,
preventing the model from 'memorising the service' (decision F5).
Repeats: CV_N_REPEATS runs of StratifiedGroupKFold with different shuffle
seeds -> CV_N_SPLITS * CV_N_REPEATS fold-scores; we report mean +/- std.

A manual loop (instead of cross_validate) keeps every step auditable and
lets us pass balanced sample_weight to XGBoost per training fold (F4).
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                             recall_score, precision_score, roc_auc_score)
from sklearn.utils.class_weight import compute_sample_weight

from backend.core import config as C
from backend.models.factory import make_model, needs_sample_weight


def _fold_metrics(y_true, y_pred, proba, classes, y_true_enc) -> dict:
    m = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
    }
    for cls in classes:                                   # per-class recall (High is critical)
        m[f"recall_{cls}"] = recall_score(y_true, y_pred, labels=[cls],
                                          average="macro", zero_division=0)
    try:                                                  # OvR macro AUC needs every class present
        m["roc_auc_ovr_macro"] = roc_auc_score(y_true_enc, proba, multi_class="ovr",
                                               average="macro",
                                               labels=list(range(len(classes))))
    except ValueError:                                    # a class absent in this test fold
        m["roc_auc_ovr_macro"] = np.nan
    return m


def evaluate_model(name: str, X: pd.DataFrame, y: pd.Series,
                   groups: pd.Series, classes: list[str],
                   fold_cb=None, seed_base: int | None = None) -> dict:
    # Uniform integer encoding of the target (required by modern XGBoost;
    # also makes probability-column alignment and AUC computation unambiguous).
    code_of = {c: i for i, c in enumerate(classes)}
    y_enc = y.map(code_of).astype(int)
    k = len(classes)

    base = C.SEED if seed_base is None else int(seed_base)
    fold_rows, fit_times = [], []
    for rep in range(C.CV_N_REPEATS):
        skf = StratifiedGroupKFold(n_splits=C.CV_N_SPLITS, shuffle=True,
                                   random_state=base + rep)
        for tr, te in skf.split(X, y_enc, groups):
            model = make_model(name, list(X.columns))
            fit_kw = {}
            if needs_sample_weight(name):
                fit_kw["clf__sample_weight"] = compute_sample_weight("balanced", y_enc.iloc[tr])
            t0 = time.perf_counter()
            model.fit(X.iloc[tr], y_enc.iloc[tr], **fit_kw)
            fit_times.append(time.perf_counter() - t0)

            raw = model.predict_proba(X.iloc[te])
            proba = np.zeros((len(te), k))                 # robust alignment: column j = class code j
            for j, cls_code in enumerate(model.classes_):
                proba[:, int(cls_code)] = raw[:, j]
            y_pred = [classes[i] for i in model.predict(X.iloc[te])]
            fold_rows.append(_fold_metrics(y.iloc[te], y_pred, proba, classes,
                                           y_enc.iloc[te]))
            if fold_cb:
                fold_cb(len(fold_rows), C.CV_N_SPLITS * C.CV_N_REPEATS)
    f = pd.DataFrame(fold_rows)
    out = {"model": name, "n_folds": len(f), "fit_time_mean_s": float(np.mean(fit_times))}
    for col in f.columns:
        out[f"{col}_mean"] = float(np.nanmean(f[col]))
        out[f"{col}_std"] = float(np.nanstd(f[col]))
    out["auc_folds_valid"] = int(f["roc_auc_ovr_macro"].notna().sum())
    return out
