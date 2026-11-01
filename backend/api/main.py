"""FastAPI service — build 3B.

Endpoints (all under /api, interactive docs at /docs):
  GET  /api/health                          liveness + versions
  GET  /api/dataset/summary                 integrity, class distributions
  POST /api/experiments/baseline/start      launch grouped-CV experiment (background)
  GET  /api/experiments/baseline/stream     Server-Sent Events live progress
  GET  /api/experiments/baseline/status     current job state (polling fallback)
  GET  /api/experiments/baseline/results    latest results table + manifest
  POST /api/models/train-final              fit serving models on all records
  GET  /api/models                          model registry
  POST /api/predict                         risk prediction for a new migration case
"""
from __future__ import annotations
import json, queue, threading, platform, time, collections, datetime
import pandas as pd
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.runner import run_all, CONFIGS
from backend.models import registry

app = FastAPI(
    title="AI-Based Risk Prediction and Recommendation Framework for Cloud Migration Projects",
    version=C.APP_VERSION,
    description="MSc research application — Ahmed Yaseen Abdelgader, SUSTECH. "
                "Real 176-record OCP→GKE dataset; grouped-CV methodology.")

# --------------------------------------------------------------- job state --
class Job:
    def __init__(self):
        self.status = "idle"            # idle | running | finished | error
        self.q: queue.Queue = queue.Queue()
        self.last_event: dict | None = None
        self.error: str | None = None
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.done_units = 0
        self.total_units: int | None = None
        self.phase: str | None = None
        self.completed: list[dict] = []
        self.run_seed: int | None = None
        self.unit_marks: collections.deque = collections.deque(maxlen=9)

    def begin(self):
        self.status, self.error = "running", None
        self.q = queue.Queue()
        self.started_at, self.finished_at = time.time(), None
        self.done_units, self.total_units, self.phase = 0, None, None
        self.completed = []
        self.unit_marks = collections.deque(maxlen=9)

    def track(self, e: dict):
        """queue + progress accounting — the server-side source of truth."""
        self.q.put(e); self.last_event = e
        t = e.get("type")
        if t == "experiment_started":
            self.total_units, self.done_units = e.get("total_units"), 0
        elif t == "fold_done":
            self.done_units += 1
            self.unit_marks.append(time.time())
        elif t == "model_done":
            self.completed.append(e)
        elif t == "phase":
            self.phase = e.get("label")

    def reset(self):
        """Wipe the in-memory session so the UI reflects a truly blank state."""
        self.__init__()

    def end(self, ok: bool, err: str | None = None):
        self.finished_at = time.time()
        self.status = "finished" if ok else "error"
        self.error = err

JOB = Job()
_summary_cache: dict | None = None


_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if not _DIST.exists():                                   # dev fallback: API docs only
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/docs")


@app.get("/api/health")
def health():
    import sklearn, xgboost
    return {"status": "ok", "build": C.APP_VERSION, "seed": C.SEED,
            "python": platform.python_version(),
            "sklearn": sklearn.__version__, "xgboost": xgboost.__version__}


@app.get("/api/dataset/summary")
def dataset_summary():
    global _summary_cache
    if _summary_cache is None:
        processed, groups, meta = run_pipeline(save=False)
        _summary_cache = {
            "rows": int(len(processed)), "services": int(groups.nunique()),
            "environments": processed["Environment"].value_counts().to_dict(),
            "risk_distribution": processed[C.TARGET_PRIMARY].value_counts().to_dict(),
            "outcome_distribution": processed[C.TARGET_SECONDARY].value_counts().to_dict(),
            "feature_sets": {"PRE_EXEC": C.PRE_EXEC_FEATURES, "FULL": C.FULL_FEATURES},
            "categorical_domains": {c: sorted(processed[c].astype(str).unique().tolist())
                                    for c in C.NOMINAL_COLS + list(C.ORDINAL_MAPS)},
            "integrity_checks": meta["integrity"],
            "cleaned_reference_verification": meta["verification"],
        }
    return _summary_cache


@app.get("/api/dataset/dictionary")
def dataset_dictionary():
    from backend.data.dictionary import build
    return {"dictionary": build()}


@app.get("/api/dataset/quality")
def dataset_quality():
    from backend.data.quality import build
    return build()


@app.get("/api/mode")
def mode():
    import json as _j
    reg = C.ARTIFACTS_DIR / "registry.json"
    latest = None
    if reg.exists():
        entries = [e for e in _j.loads(reg.read_text()) if e["config"] == "A_Risk_PRE-EXEC"]
        primary = [e for e in entries if e["algorithm"] == "Logistic Regression"]
        latest = (primary or entries)[-1] if entries else None
    man = C.RESULTS_DIR / "phase3a_manifest.json"
    hold = C.RESULTS_DIR / "holdout_report.json"
    _ready = (C.RESULTS_DIR / "phase3a_manifest.json").exists()
    _state = "live" if JOB.status == "running" else ("demo" if _ready else "reset")
    return {"version": C.APP_VERSION,
            "live_training": JOB.status == "running",
            "state": _state,
            "mode": "live_training" if JOB.status == "running" else "demo",
            "dataset": C.RAW_XLSX.name, "records": 176, "seed": C.SEED,
            "latest_model": latest,
            "results_generated_at": _j.loads(man.read_text())["ts"] if man.exists() else None,
            "holdout_generated_at": _j.loads(hold.read_text())["generated_at"] if hold.exists() else None}


@app.get("/api/holdout")
def holdout(force: bool = False):
    from backend.experiments.holdout import run as run_holdout
    return run_holdout(force=force)


@app.get("/api/research/progress")
def research_progress():
    from backend.research.progress import build
    return build()


@app.post("/api/exports/generate")
def exports_generate():
    from backend.exports.figures import generate_all
    return generate_all()


@app.get("/api/exports/manifest")
def exports_manifest():
    import json
    mpath = C.ROOT / "data" / "exports" / "manifest.json"
    if not mpath.exists():
        raise HTTPException(404, "no exports yet — generate first")
    return json.loads(mpath.read_text())


# ------------------------------------------------------------- experiment --
class StartRequest(BaseModel):
    seed: int | None = None


@app.post("/api/experiments/baseline/start")
def start_experiment(req: StartRequest | None = None):
    seed_base = req.seed if req else None
    if JOB.status == "running":
        raise HTTPException(409, "already running")
    JOB.begin()
    JOB.run_seed = int(seed_base) if seed_base is not None else C.SEED

    def work():
        try:
            run_all(progress_cb=JOB.track, seed_base=seed_base)
            # v30: live training completes the same trilogy as restore,
            # so every session page refills (serving models + XAI cache).
            JOB.track({"type": "phase", "label": "training serving models"})
            registry.train_final("A_Risk_PRE-EXEC")
            registry.train_final("B_Risk_FULL")
            JOB.track({"type": "phase", "label": "computing explanations"})
            from backend.explain.explainer import global_explanations
            global_explanations(force=True)
            JOB.end(ok=True)
            JOB.q.put({"type": "experiment_finished"})
        except Exception as ex:                                    # surfaced, never hidden
            JOB.end(ok=False, err=repr(ex))
            JOB.q.put({"type": "error", "detail": repr(ex)})

    threading.Thread(target=work, daemon=True).start()
    return {"started": True}


@app.get("/api/experiments/baseline/stream")
def stream():
    def gen():
        while True:
            try:
                e = JOB.q.get(timeout=15)
                yield f"data: {json.dumps(e)}\n\n"
                if e["type"] in ("experiment_finished", "error"):
                    return
            except queue.Empty:
                if JOB.status in ("finished", "error", "idle"):
                    return
                yield ": heartbeat\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.get("/api/experiments/baseline/status")
def status():
    now = time.time()
    elapsed = ((JOB.finished_at or now) - JOB.started_at) if JOB.started_at else None
    duration = (JOB.finished_at - JOB.started_at) if (JOB.finished_at and JOB.started_at) else None
    last_at, last_wall, last_seed = None, None, None
    if JOB.finished_at or JOB.status == "running":
        last_seed = JOB.run_seed
    if JOB.finished_at:
        last_at = datetime.datetime.fromtimestamp(JOB.finished_at).isoformat(timespec="seconds")
        last_wall = round(JOB.finished_at - JOB.started_at, 1) if JOB.started_at else None
    else:
        mf = C.RESULTS_DIR / "phase3a_manifest.json"
        if mf.exists():
            try:
                _m = json.loads(mf.read_text())
                last_at, last_wall = _m.get("ts"), _m.get("wall_seconds")
                if last_seed is None:
                    last_seed = _m.get("split_seed_base")
            except Exception:
                pass
    m = list(JOB.unit_marks)
    recent = round((m[-1] - m[0]) / (len(m) - 1), 2) if len(m) >= 4 else None
    return {"status": JOB.status, "error": JOB.error, "phase": JOB.phase,
            "recent_unit_s": recent, "completed": JOB.completed,
            "last_run_at": last_at, "last_wall_s": last_wall, "last_seed": last_seed,
            "elapsed_s": round(elapsed, 1) if elapsed is not None else None,
            "duration_s": round(duration, 1) if duration is not None else None,
            "done_units": JOB.done_units, "total_units": JOB.total_units,
            "last_event": JOB.last_event}


@app.get("/api/experiments/baseline/results")
def results():
    path = C.RESULTS_DIR / "phase3a_baseline_results.csv"
    if not path.exists():
        raise HTTPException(404, "no results yet — start the experiment first")
    df = pd.read_csv(path)
    manifest = json.loads((C.RESULTS_DIR / "phase3a_manifest.json").read_text())
    # NaN -> null: Risk rows have empty Outcome-recall columns and vice versa;
    # strict JSON rejects NaN, so serialise through to_json (emits null).
    records = json.loads(df.round(4).to_json(orient="records"))
    return {"manifest": manifest, "results": records}


# ------------------------------------------------------------------ models --
class TrainFinalRequest(BaseModel):
    config: str = "A_Risk_PRE-EXEC"


@app.post("/api/models/train-final")
def train_final(req: TrainFinalRequest):
    if not (C.RESULTS_DIR / "phase3a_manifest.json").exists():
        raise HTTPException(409, "session was reset — run live training or one-click restore first")
    if req.config not in [c[0] for c in CONFIGS]:
        raise HTTPException(422, f"unknown config; choose one of {[c[0] for c in CONFIGS]}")
    return {"trained": registry.train_final(req.config)}


@app.get("/api/models")
def models():
    # v36: self-heal ONLY on a clean checkout (shipped results present).
    # After an explicit session reset the manifest is gone too, so the page
    # honestly waits for live training / restore — demo integrity restored.
    if not registry.list_models() and (C.RESULTS_DIR / "phase3a_manifest.json").exists():
        registry.ensure_serving_all()
    return {"models": registry.list_models()}


# ------------------------------------------------------------------- xai ----
@app.get("/api/explain/global")
def explain_global(force: bool = False):
    from backend.explain.explainer import CACHE, global_explanations
    if not force and not CACHE.exists():
        raise HTTPException(404, "no session explanations yet — run live training or restore first")
    return global_explanations(force=force)


# -------------------------------------------------------------- demo (v19) --
@app.post("/api/demo/reset")
def demo_reset(confirm: bool = False):
    if JOB.status == "running":
        raise HTTPException(409, "training is running — wait for it to finish")
    if not confirm:
        raise HTTPException(400, "pass ?confirm=true to reset the demo session")
    from backend.experiments.demo import reset_session
    out = reset_session()
    JOB.reset()                       # v28: clear in-memory session too
    out["job_state"] = "cleared"
    return out


@app.post("/api/demo/restore")
def demo_restore():
    """One-click rebuild: full experiment -> serving models -> XAI cache."""
    if JOB.status == "running":
        raise HTTPException(409, "already running")
    JOB.begin()
    JOB.run_seed = C.SEED

    def work():
        try:
            run_all(progress_cb=JOB.track)
            JOB.track({"type": "phase", "label": "training serving models"})
            registry.train_final("A_Risk_PRE-EXEC")
            registry.train_final("B_Risk_FULL")
            JOB.track({"type": "phase", "label": "computing explanations"})
            from backend.explain.explainer import global_explanations
            global_explanations(force=True)
            JOB.end(ok=True)
            JOB.q.put({"type": "experiment_finished"})
        except Exception as ex:                                    # noqa: BLE001
            JOB.end(ok=False, err=repr(ex))
            JOB.q.put({"type": "error", "detail": repr(ex)})
    threading.Thread(target=work, daemon=True).start()
    return {"started": True}


@app.get("/api/holdout/records")
def holdout_records():
    from backend.experiments.demo import vault_records
    return vault_records()


@app.post("/api/holdout/predict_case")
def holdout_predict_case(req: dict):
    from backend.experiments.demo import vault_case
    try:
        return vault_case(str(req.get("migration_id", "")))
    except KeyError:
        raise HTTPException(404, "record is not in the sealed vault")


@app.get("/api/holdout/random_case")
def holdout_random_case():
    from backend.experiments.demo import random_unseen_case
    return random_unseen_case()


# ------------------------------------------------------------- vault (v19) --
@app.get("/api/vault")
def vault_list():
    from backend.research.vault import list_docs
    return {"docs": list_docs()}


@app.post("/api/vault/upload")
async def vault_upload(file: UploadFile = File(...), note: str = Form("")):
    data = await file.read()
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(413, "max file size is 50MB")
    if not data:
        raise HTTPException(400, "empty file")
    from backend.research.vault import save
    return save(file.filename, data, note)


@app.get("/api/vault/download")
def vault_download(name: str, version: int | None = None):
    from backend.research.vault import filepath
    try:
        path, _ = filepath(name, version)
    except Exception:
        raise HTTPException(404, "document/version not found")
    return FileResponse(path, filename=name)


@app.get("/api/dataset/download")
def dataset_download():
    path = C.RAW_XLSX
    if not path.exists():
        raise HTTPException(404, "dataset file not found")
    return FileResponse(path, filename="OCP_GKE_Migration_Risk_Dataset_REAL_176.xlsx")


@app.get("/api/docs/manual")
def user_manual():
    path = C.ROOT / "docs" / "System_User_Manual_AR.docx"
    if not path.exists():
        raise HTTPException(404, "manual not found in docs/")
    return FileResponse(path, filename="System_User_Manual_AR.docx")


# ---------------------------------------------------------------- recommend --
@app.get("/api/recommend/rules")
def recommend_rules():
    from backend.recommend.engine import load_rules
    return {"rules": load_rules()}


# ----------------------------------------------------------------- predict --
class PredictRequest(BaseModel):
    model_id: str
    features: dict


@app.post("/api/predict")
def predict(req: PredictRequest):
    try:
        entry = registry.get_entry(req.model_id)
        model = registry.load(req.model_id)
    except (KeyError, FileNotFoundError):
        raise HTTPException(404, "model_id not found — train final models first")

    missing = [f for f in entry["features"] if f not in req.features]
    if missing:
        raise HTTPException(422, f"missing features: {missing}")

    X = pd.DataFrame([{f: req.features[f] for f in entry["features"]}])
    try:
        proba = model.predict_proba(X)[0]
    except Exception as ex:
        raise HTTPException(422, f"invalid feature values: {ex}")

    classes = entry["classes"]
    aligned = {classes[int(c)]: float(p) for c, p in zip(model.classes_, proba)}
    pred = max(aligned, key=aligned.get)
    explanation = None
    if entry["algorithm"] == "Logistic Regression":
        from backend.explain.explainer import per_case
        explanation = per_case(model, X, classes.index(pred))
    from backend.recommend.engine import evaluate as recommend
    rec = recommend(req.features, prediction=pred)
    return {"prediction": pred,
            "explanation": explanation,
            "recommendations": rec,
            "probabilities": {c: round(aligned.get(c, 0.0), 4) for c in classes},
            "model": {k: entry[k] for k in ("model_id", "algorithm", "config", "target", "trained_at")},
            "disclaimer": "Decision-support output; final approval rests with human experts."}


# Serve the built Arabic/English SPA at "/" (registered last so /api and /docs win).
_EXP = Path(__file__).resolve().parents[2] / "data" / "exports"
_EXP.mkdir(parents=True, exist_ok=True)
app.mount("/exports", StaticFiles(directory=_EXP), name="exports")
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="ui")
