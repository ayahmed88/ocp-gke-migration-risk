"""Phase 6 — end-to-end acceptance sweep.

One test per UI page (14 pages): every API that feeds a page is hit and its
essential shape asserted, plus the SPA shell, a served export file, and a
predict round-trip carrying all four layers (prediction, probabilities,
explanation, recommendations). `pytest -q` green == acceptance gate passed.
"""
import pytest
from fastapi.testclient import TestClient
from backend.core import config as C

real_data = pytest.mark.skipif(C.IS_SYNTHETIC_DATA, reason="asserts figures that exist only for the real dataset")


@pytest.fixture(scope="module")
def c():
    from backend.api.main import app
    return TestClient(app)


def test_p01_overview(c):
    s = c.get("/api/dataset/summary").json()
    assert s["rows"] == 176 and s["services"] == 88 and s["integrity_checks"]["all_passed"]


def test_p02_research_progress(c):
    p = c.get("/api/research/progress").json()
    assert p["chapters"] and 0 < p["overall_pct"] <= 100
    ch = p["chapters"][0]
    assert {"id", "title", "items", "done", "total", "pct"} <= set(ch)  # UI contract: hero chips + group cards
    assert {"title", "done", "auto"} <= set(ch["items"][0])


def test_p03_presentation_flow(c):
    m = c.get("/api/mode").json()
    assert m["mode"] in ("demo", "live_training") and m["records"] == 176 and m["version"]
    rc = c.get("/api/holdout/random_case").json()
    assert rc["vault_size"] == 36 and rc["match"] == (rc["predicted"] == rc["true"])


@real_data
def test_p04_live_training_endpoints(c):
    st = c.get("/api/experiments/baseline/status").json()
    assert st["status"] in ("idle", "running", "finished", "error")
    assert "completed" in st and "recent_unit_s" in st and "duration_s" in st
    assert "last_run_at" in st and st["last_run_at"]          # persistent timestamp
    assert c.get("/api/docs/manual").status_code == 200          # user manual served
    dl = c.get("/api/dataset/download")                            # raw dataset
    assert dl.status_code == 200 and len(dl.content) > 50_000
    assert c.post("/api/demo/reset").status_code == 400          # guard only; no reset


def test_p05_evaluation_results(c):
    r = c.get("/api/experiments/baseline/results").json()
    assert len(r["results"]) == 12 and r["manifest"]["split_seed_base"] == 42


def test_p06_xai(c):
    g = c.get("/api/explain/global").json()
    assert set(g["coefficients_per_class"]) == {"Low", "Medium", "High"}
    assert len(g["permutation_importance"]) == 13


def test_p07_predict_four_layers(c):
    ms = [m for m in c.get("/api/models").json()["models"]
          if m["algorithm"] == "Logistic Regression" and m["config"] == "A_Risk_PRE-EXEC"]
    assert ms, "serving LR model must exist"
    body = {"model_id": ms[-1]["model_id"], "features": {
        "Environment": "QA", "Service_Category": "API", "Business_Criticality": "High",
        "Complexity_Level": 4, "Has_DB_Dependency": 1, "DB_Type": "PostgreSQL",
        "Has_Network_Change": 1, "Firewall_Rules_Count": 6, "External_Integrations_Count": 3,
        "Route_Ingress_Changed": 1, "Has_Config_Change": 1, "Owner_Availability": "Delayed",
        "Previous_Issues_Count": 2}}
    p = c.post("/api/predict", json=body).json()
    assert p["prediction"] == "High" and abs(sum(p["probabilities"].values()) - 1) < 1e-6
    assert p["explanation"]["contributions"] and p["recommendations"]["recommendations"]


def test_p08_recommendations_rulebook(c):
    assert len(c.get("/api/recommend/rules").json()["rules"]) == 8


def test_p09_data_dictionary(c):
    assert len(c.get("/api/dataset/dictionary").json()["dictionary"]) == 27


def test_p10_data_quality(c):
    q = c.get("/api/dataset/quality").json()
    assert q["checks"] and not any(k["status"] == "FAIL" for k in q["checks"])


def test_p11_exports(c):
    m = c.get("/api/exports/manifest").json()
    assert len(m["figures"]) >= 8 and m["dpi"] == 300 and "version" in m
    assert len(m["files"]) >= 18          # UI contract: the page maps m.files
    first_png = m["figures"][0]["file"] + ".png"
    f = c.get(f"/exports/{first_png}")
    assert f.status_code == 200 and len(f.content) > 10_000


def test_p12_model_registry(c):
    ms = c.get("/api/models").json()["models"]
    assert len(ms) >= 6 and all(m["seed"] == 42 for m in ms)


@real_data
def test_p13_holdout_sealed(c):
    h = c.get("/api/holdout").json()
    assert h["locked"] and h["metrics"]["macro_f1"] == 0.559
    vr = c.get("/api/holdout/records").json()                # sealed roster
    first = vr["records"][0]
    vc = c.post("/api/holdout/predict_case",
                json={"migration_id": first["migration_id"]}).json()
    assert vc["predicted"] == first["pred"] and vc["true"] == first["true"]
    assert vc["match"] == (vc["predicted"] == vc["true"])
    assert abs(sum(vc["probabilities"].values()) - 1.0) < 0.01
    assert c.post("/api/holdout/predict_case",                 # MIG-006 is the classroom
                  json={"migration_id": "MIG-006"}).status_code == 404  # specimen, NOT vault
    assert vr["total"] == 36 and len(vr["records"]) == 36
    assert vr["hits"] == 22 and vr["matches_seal"] is True
    assert vr["class_counts"] == {"High": 15, "Medium": 18, "Low": 3}


def test_p14_vault_and_docs_guide(c):
    assert "docs" in c.get("/api/vault").json()
    assert c.get("/api/health").json()["status"] == "ok"


def test_spa_shell_served(c):
    r = c.get("/")
    assert r.status_code == 200 and "<div id=" in r.text
