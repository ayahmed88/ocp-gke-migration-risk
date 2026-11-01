"""Model registry — final-model training, persistence and loading.

'Final' models are fitted on ALL 176 records (fixed seed, same pipelines and
balanced-weight policy as the CV) and are used by the /predict endpoint.
Their quality claims always reference the grouped-CV numbers — never a score
computed on their own training data.
Each entry = <id>.joblib + metadata inside registry.json (traceability).
"""
from __future__ import annotations
import json, datetime, uuid
import pandas as pd
import joblib
from sklearn.utils.class_weight import compute_sample_weight

from backend.core import config as C
from backend.models.factory import make_model, needs_sample_weight, MODEL_ORDER
from backend.experiments.runner import CONFIGS

REG_PATH = C.ARTIFACTS_DIR / "registry.json"
_cache: dict = {}


def _read_registry() -> list[dict]:
    return json.loads(REG_PATH.read_text()) if REG_PATH.exists() else []


def list_models() -> list[dict]:
    return _read_registry()


def train_final(config_name: str) -> list[dict]:
    cfg = next((c for c in CONFIGS if c[0] == config_name), None)
    if cfg is None:
        raise ValueError(f"unknown config '{config_name}'")
    _, target, features, classes = cfg

    from backend.data.pipeline import run as run_pipeline
    processed, _, meta = run_pipeline(save=False)
    X = processed[features]
    y_enc = processed[target].map({c: i for i, c in enumerate(classes)}).astype(int)

    C.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    entries = _read_registry()
    new = []
    for name in MODEL_ORDER:
        if name == "Dummy (prior)":
            continue                                   # baseline is a yardstick, not a product
        model = make_model(name, features)
        fit_kw = {}
        if needs_sample_weight(name):
            fit_kw["clf__sample_weight"] = compute_sample_weight("balanced", y_enc)
        model.fit(X, y_enc, **fit_kw)
        mid = f"{config_name}__{name.replace(' ', '_')}__{uuid.uuid4().hex[:8]}"
        joblib.dump(model, C.ARTIFACTS_DIR / f"{mid}.joblib")
        entry = {"model_id": mid, "algorithm": name, "config": config_name,
                 "target": target, "classes": classes, "features": features,
                 "trained_on_rows": int(len(X)), "seed": C.SEED,
                 "fit_scope": "all-176 refit after the evaluation protocol (v34)",
        "trained_at": datetime.datetime.now().isoformat(timespec="seconds"),
                 "integrity_checks_passed": bool(meta["integrity"]["all_passed"]),
                 "note": "Fitted on all records for serving; quality figures = grouped-CV results."}
        entries.append(entry); new.append(entry)
    REG_PATH.write_text(json.dumps(entries, indent=2))
    return new


def load(model_id: str):
    if model_id not in _cache:
        path = C.ARTIFACTS_DIR / f"{model_id}.joblib"
        if not path.exists():
            raise FileNotFoundError(model_id)
        _cache[model_id] = joblib.load(path)
    return _cache[model_id]


def ensure_serving_all() -> None:
    """Self-heal on a clean checkout: build serving models on first demand
    (deterministic; mirrors the vault's lazy-build pattern)."""
    if not _read_registry():
        for cfg in ("A_Risk_PRE-EXEC", "B_Risk_FULL"):
            train_final(cfg)


def get_entry(model_id: str) -> dict:
    for e in _read_registry():
        if e["model_id"] == model_id:
            return e
    raise KeyError(model_id)
