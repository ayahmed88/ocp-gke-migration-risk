"""Phase 4A — Hyperparameter tuning with fully nested, group-aware CV.

Design (defensible by construction):
- OUTER: the same Repeated StratifiedGroupKFold (5 folds x 5 repeats, seeds
  42..46) used for the baselines -> tuned numbers are directly comparable.
- INNER: GroupKFold(3) on the OUTER-TRAIN portion only selects hyperparameters
  by mean Macro-F1. The outer test fold is never touched during selection.
- The search is a small, documented grid implemented as an explicit loop so
  XGBoost's balanced sample_weight is computed on each inner-train split
  correctly (GridSearchCV cannot route that cleanly here).
- Deployment parameters = the most frequently selected combination across the
  25 outer folds (reported with its selection count).

CLI (resumable, appends to JSON):
  python -m backend.experiments.tuning --model "Random Forest" --reps 0 1
"""
from __future__ import annotations
import argparse, itertools, json, time
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, GroupKFold
from sklearn.metrics import f1_score
from sklearn.utils.class_weight import compute_sample_weight

from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.models.factory import make_model, needs_sample_weight
from backend.evaluation.cv import _fold_metrics

GRIDS = {
    "Logistic Regression": {"clf__C": [0.05, 0.2, 1.0, 5.0]},
    "Random Forest": {"clf__max_depth": [None, 8],
                      "clf__min_samples_leaf": [1, 3],
                      "clf__max_features": ["sqrt", None]},
    "XGBoost": {"clf__max_depth": [3, 4, 6],
                "clf__learning_rate": [0.05, 0.10]},
}
OUT_PATH = C.RESULTS_DIR / "phase4a_tuning_folds.json"


def _combos(grid: dict):
    keys = list(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


def _fit(model_name, features, params, X, y_enc, sw=None):
    m = make_model(model_name, features)
    m.set_params(**params)
    kw = {"clf__sample_weight": sw} if sw is not None else {}
    m.fit(X, y_enc, **kw)
    return m


def tune_model(model_name: str, reps: list[int]) -> list[dict]:
    _, target, features, classes = ("A_Risk_PRE-EXEC", C.TARGET_PRIMARY,
                                    C.PRE_EXEC_FEATURES, C.RISK_CLASSES)
    processed, groups, _ = run_pipeline(save=False)
    X = processed[features]
    y = processed[target]
    code_of = {c: i for i, c in enumerate(classes)}
    y_enc = y.map(code_of).astype(int)
    k = len(classes)

    fold_records = []
    for rep in reps:
        outer = StratifiedGroupKFold(n_splits=C.CV_N_SPLITS, shuffle=True,
                                     random_state=C.SEED + rep)
        for fold_i, (tr, te) in enumerate(outer.split(X, y_enc, groups)):
            Xtr, ytr, gtr = X.iloc[tr], y_enc.iloc[tr], groups.iloc[tr]

            # ---- inner selection on outer-train only -------------------
            best_params, best_score = None, -1.0
            inner = GroupKFold(n_splits=3)
            for params in _combos(GRIDS[model_name]):
                scores = []
                for itr, iva in inner.split(Xtr, ytr, gtr):
                    sw = (compute_sample_weight("balanced", ytr.iloc[itr])
                          if needs_sample_weight(model_name) else None)
                    m = _fit(model_name, features, params,
                             Xtr.iloc[itr], ytr.iloc[itr], sw)
                    pred = m.predict(Xtr.iloc[iva])
                    scores.append(f1_score(ytr.iloc[iva], pred,
                                           average="macro", zero_division=0))
                sc = float(np.mean(scores))
                if sc > best_score:
                    best_score, best_params = sc, params

            # ---- refit on full outer-train, evaluate on outer-test -----
            sw = (compute_sample_weight("balanced", ytr)
                  if needs_sample_weight(model_name) else None)
            t0 = time.perf_counter()
            m = _fit(model_name, features, best_params, Xtr, ytr, sw)
            fit_s = time.perf_counter() - t0
            raw = m.predict_proba(X.iloc[te])
            proba = np.zeros((len(te), k))
            for j, cc in enumerate(m.classes_):
                proba[:, int(cc)] = raw[:, j]
            y_pred = [classes[i] for i in m.predict(X.iloc[te])]
            met = _fold_metrics(y.iloc[te], y_pred, proba, classes, y_enc.iloc[te])
            fold_records.append({"model": model_name, "rep": rep, "fold": fold_i,
                                 "params": best_params, "inner_f1": best_score,
                                 "fit_time_s": fit_s, **met})
            print(f"  rep{rep} fold{fold_i}: f1={met['f1_macro']:.3f} "
                  f"params={best_params}")
    return fold_records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(GRIDS))
    ap.add_argument("--reps", type=int, nargs="+", required=True)
    a = ap.parse_args()
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = json.loads(OUT_PATH.read_text()) if OUT_PATH.exists() else []
    existing = [r for r in existing                       # idempotent re-runs
                if not (r["model"] == a.model and r["rep"] in a.reps)]
    existing += tune_model(a.model, a.reps)
    OUT_PATH.write_text(json.dumps(existing, indent=1))
    done = pd.DataFrame(existing)
    print(f"\nstored: {len(existing)} fold records "
          f"({done.groupby('model')['fold'].count().to_dict()})")


if __name__ == "__main__":
    main()
