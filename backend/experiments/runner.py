"""Experiment runner — callable from the CLI and from the FastAPI layer.

Emits fine-grained progress events through an optional callback so the API
can stream live training progress (SSE) to the browser:
  {"type":"experiment_started", total_units}
  {"type":"model_started",  config, model}
  {"type":"fold_done",      config, model, fold, total_folds}
  {"type":"model_done",     config, model, f1_macro, accuracy, auc, seconds}
  {"type":"experiment_finished", results_path}
"""
from __future__ import annotations
import json, time, datetime, platform
from typing import Callable, Optional
import pandas as pd
import sklearn, xgboost

from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.models.factory import MODEL_ORDER
from backend.evaluation.cv import evaluate_model

CONFIGS = [
    ("A_Risk_PRE-EXEC", C.TARGET_PRIMARY, C.PRE_EXEC_FEATURES, C.RISK_CLASSES),
    ("B_Risk_FULL",     C.TARGET_PRIMARY, C.FULL_FEATURES,     C.RISK_CLASSES),
    ("C_Outcome_PRE-EXEC", C.TARGET_SECONDARY, C.PRE_EXEC_FEATURES, C.OUTCOME_CLASSES),
]
TOTAL_FOLDS = C.CV_N_SPLITS * C.CV_N_REPEATS


def run_all(progress_cb: Optional[Callable[[dict], None]] = None,
            seed_base: int | None = None) -> dict:
    emit = progress_cb or (lambda e: None)
    t_run = time.perf_counter()
    emit({"type": "experiment_started",
          "total_units": len(CONFIGS) * len(MODEL_ORDER) * TOTAL_FOLDS})

    processed, groups, meta = run_pipeline(save=True)
    # v34 (decision B): carve the sealed 20% vault FIRST; every comparison
    # below sees only the 80% selection pool — the vault influences nothing.
    from backend.experiments.split import vault_carve
    _tr, _ = vault_carve(processed, processed[C.TARGET_PRIMARY], groups)
    processed = processed.iloc[_tr].reset_index(drop=True)
    groups = groups.iloc[_tr].reset_index(drop=True)
    rows = []
    for cfg_name, target, features, classes in CONFIGS:
        X, y = processed[features], processed[target]
        for model_name in MODEL_ORDER:
            emit({"type": "model_started", "config": cfg_name, "model": model_name})
            t0 = time.perf_counter()
            r = evaluate_model(
                model_name, X, y, groups, classes, seed_base=seed_base,
                fold_cb=lambda i, n, c=cfg_name, m=model_name: emit(
                    {"type": "fold_done", "config": c, "model": m,
                     "fold": i, "total_folds": n}))
            r.update({"config": cfg_name, "target": target, "n_features": len(features)})
            rows.append(r)
            emit({"type": "model_done", "config": cfg_name, "model": model_name,
                  "f1_macro": round(r["f1_macro_mean"], 4),
                  "f1_macro_std": round(r["f1_macro_std"], 4),
                  "accuracy": round(r["accuracy_mean"], 4),
                  "auc": round(r["roc_auc_ovr_macro_mean"], 4),
                  "recall_per_class": {c2: round(r[f"recall_{c2}_mean"], 4) for c2 in classes},
                  "seconds": round(time.perf_counter() - t0, 2)})

    res = pd.DataFrame(rows)
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    res_path = C.RESULTS_DIR / "phase3a_baseline_results.csv"
    res.to_csv(res_path, index=False)
    manifest = {
        "experiment": "baseline_grouped_cv",
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "wall_seconds": round(time.perf_counter() - t_run, 1),
        "dataset": C.RAW_XLSX.name, "sheet": C.RAW_SHEET, "rows": 176, "groups": 88,
        "selection_pool": {"rows": int(len(processed)), "services": int(groups.nunique()),
                           "vault_excluded": True, "policy": "carve-before-any-comparison (v34)"},
        "validation": f"StratifiedGroupKFold {C.CV_N_SPLITS}-fold x {C.CV_N_REPEATS} repeats (split seeds {(seed_base if seed_base is not None else C.SEED)}..{(seed_base if seed_base is not None else C.SEED) + C.CV_N_REPEATS - 1})",
        "split_seed_base": int(seed_base) if seed_base is not None else C.SEED,
        "imbalance_handling": "class_weight='balanced' (XGBoost: balanced sample_weight per training fold)",
        "tuning": "none (defaults; Phase 4)", "seed": C.SEED,
        "primary_metric": "f1_macro (guardrail: recall_High)",
        "integrity_checks": meta["integrity"],
        "cleaned_ref_verification": meta["verification"],
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                     "xgboost": xgboost.__version__, "pandas": pd.__version__},
    }
    (C.RESULTS_DIR / "phase3a_manifest.json").write_text(json.dumps(manifest, indent=2))
    emit({"type": "experiment_finished", "results_path": str(res_path)})
    return {"results": res, "manifest": manifest}
