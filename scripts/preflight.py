#!/usr/bin/env python3
"""Pre-release verification agent — must pass before shipping ANY version.
Usage: python scripts/preflight.py   (exit 0 = green)"""
import subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN = ["seed 42", "بذرة 42", "seed: 42", "بذرة: 42"]  # stale hardcoded seed displays


def fail(msg):
    print("PREFLIGHT FAIL:", msg)
    sys.exit(1)


# 1) full test suite
r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                   cwd=ROOT, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stdout[-1200:])
    fail("pytest not green")
print("pytest:", r.stdout.strip().splitlines()[-1])

# 2) stale-literal scan across UI source
hits = []
for f in (ROOT / "frontend" / "src").rglob("*"):
    if f.suffix in (".jsx", ".js", ".json") and f.is_file():
        txt = f.read_text(encoding="utf-8", errors="ignore")
        hits += [f"{f.relative_to(ROOT)} :: {pat}" for pat in FORBIDDEN if pat in txt]
if hits:
    fail("stale seed display remains:\n  " + "\n  ".join(hits))
print("UI scan: no stale hardcoded seed displays")

# identifier-wiring guard: identifiers used in pages must be DECLARED there (imports do not count)
import glob as _g, re as _re
_CHK = [(r"\bvm\s*[=!]==", "const vm = useViewMode()"),
        (r"\bwhyAll\b", "[whyAll, setWhyAll]"),
        (r"\bfull\b\s*[)?&|]", "[full, setFull]"),
        (r"\bsOpen\b", "[sOpen, setSOpen]"),
        (r"\bbuildNum\b", "[buildNum, setBuildNum]")]
for _f in _g.glob(str(ROOT / "frontend/src/pages/*.jsx")):
    _src = open(_f).read()
    for _rx, _decl in _CHK:
        if _re.search(_rx, _src) and _decl not in _src:
            fail(f"identifier-wiring: {_f} uses {_rx} without declaring {_decl}")
print("UI scan: identifier wiring consistent")

# old-family stale scan (B8): superseded selection-era figures must not live
# outside the two documented historical records (CHANGELOG, phase4a_winner).
_FAM = _re.compile(r"0\.6084|0\.608\b|0\.0966|0\.852\b|0\.5949")
_EXEMPT = {"CHANGELOG.md", "phase4a_winner.json", "influential11_sensitivity.json"}
import os as _os
for _f in _g.glob(str(ROOT / "data/exports/*")) + _g.glob(str(ROOT / "data/results/*.json")) + \
          _g.glob(str(ROOT / "docs/*.md")) + [str(ROOT / "README.md")]:
    if _os.path.basename(_f) in _EXEMPT or not _f.endswith((".json", ".csv", ".md", ".txt")):
        continue
    if _FAM.search(open(_f, encoding="utf-8", errors="ignore").read()):
        fail(f"old-family figure leaked into {_os.path.basename(_f)}")
print("UI scan: old-family literals clean (3 documented historical exemptions)")

# 3) API smoke on a fresh app instance
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient          # noqa: E402
from backend.api.main import app                   # noqa: E402

c = TestClient(app)
h = c.get("/api/health").json()
st = c.get("/api/experiments/baseline/status").json()
assert h.get("build"), "health/build missing"
for k in ("status", "completed", "last_run_at", "last_seed"):
    assert k in st, f"status missing {k}"
hold = c.get("/api/holdout").json()
assert hold["locked"] and hold["metrics"]["macro_f1"] == 0.559, "holdout seal drift!"
print(f"API smoke: build {h['build']} - status keys ok - holdout seal intact (0.559)")
if "--scenario" in sys.argv:
    import time
    c.post("/api/demo/reset", params={"confirm": "true"})
    st = c.get("/api/experiments/baseline/status").json()
    assert st["status"] == "idle" and st["completed"] == [], "reset left session state"
    assert c.get("/api/mode").json()["state"] == "reset", "mode badge must say reset"
    assert c.get("/api/models").json()["models"] == [], "models must wait after reset"
    assert c.post("/api/models/train-final",
                  json={"config": "A_Risk_PRE-EXEC"}).status_code == 409, \
        "train-final backdoor open after reset"
    assert c.post("/api/predict",
                  json={"model_id": "A_Risk_PRE-EXEC__stale__x", "features": {}}
                  ).status_code == 404, "stale-id predict leaked after reset"
    assert c.get("/api/explain/global").status_code == 404, "XAI must wait after reset"
    vh = c.get("/api/holdout").json()
    assert vh["locked"] and vh["metrics"]["macro_f1"] == 0.559, "vault must survive reset"
    first = c.get("/api/holdout/records").json()["records"][0]
    vc = c.post("/api/holdout/predict_case",
                json={"migration_id": first["migration_id"]}).json()
    assert vc["match"] == (vc["predicted"] == vc["true"]), "vault predict broken"
    c.post("/api/demo/restore")
    while c.get("/api/experiments/baseline/status").json()["status"] not in ("finished", "error"):
        time.sleep(3)
    res = c.get("/api/experiments/baseline/results").json()["results"]
    lr = [x for x in res if x["model"] == "Logistic Regression"
          and x["config"] == "A_Risk_PRE-EXEC"][0]
    assert abs(lr["f1_macro_mean"] - 0.634) < 0.005, "official number drifted"
    assert len(c.get("/api/models").json()["models"]) >= 6, "serving not rebuilt"
    assert c.get("/api/mode").json()["state"] == "demo", "mode badge must return to demo"
    print("scenario: reset-emptiness + vault-independence + restore-to-0.634 all verified")

if "--clean" in sys.argv:
    import shutil, tempfile
    tmp = pathlib.Path(tempfile.mkdtemp()) / "clean"
    shutil.copytree(ROOT, tmp, ignore=shutil.ignore_patterns(
        "node_modules", "__pycache__", ".venv", "artifacts", "processed", "vault"))
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                       cwd=tmp, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1200:]); fail("CLEAN-CHECKOUT pytest not green")
    print("clean-checkout pytest:", r.stdout.strip().splitlines()[-1])
    r2 = subprocess.run([sys.executable, "-c",
        "from backend.exports.figures import generate_all;import json;"
        "print(json.dumps(generate_all()))"],
        cwd=tmp, capture_output=True, text=True)
    if r2.returncode != 0:
        print(r2.stdout[-800:], r2.stderr[-800:]); fail("figures gate: generation failed in clean checkout")
    import json as _json
    _mf = _json.loads((tmp / "data/exports/manifest.json").read_text())
    _by = {f["file"]: f["numbers"] for f in _mf["figures"]}
    _cmp = _by["fig_model_comparison_preexec"]
    assert abs(_cmp["Logistic Regression"] - 0.634) < 0.001 and abs(_cmp["XGBoost"] - 0.592) < 0.001 \
        and abs(_cmp["Random Forest"] - 0.539) < 0.001 and abs(_cmp["Dummy (prior)"] - 0.238) < 0.001, _cmp
    assert _by["fig_confusion_winner_oof"]["sum"] == 140
    _h = _by["fig_confusion_holdout"]
    assert _h["sum"] == 36 and _h["correct"] == 22 and abs(_h["macro_f1"] - 0.559) < 0.002, _h
    assert abs(_by["fig_roc_winner"]["auc_macro"] - 0.859) < 0.01
    _blob = "".join(open(_q, encoding="utf-8", errors="ignore").read()
                    for _q in _g.glob(str(tmp / "data/exports/*"))
                    if _q.endswith((".json", ".csv", ".md")))
    assert not _FAM.search(_blob), "old-family leaked into freshly generated exports"
    print(f"figures gate: {len(_mf['figures'])} figures generated & verified in clean checkout")
print("PREFLIGHT PASS - safe to ship")
