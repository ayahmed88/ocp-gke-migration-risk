"""Phase 4D automated tests — run with:  pytest -q"""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.data.pipeline import run as run_pipeline
from backend.recommend.engine import evaluate
from backend.core import config as C


def test_pipeline_integrity_and_oracle():
    processed, groups, meta = run_pipeline(save=False)
    assert meta["integrity"]["all_passed"]
    assert meta["verification"]["values_match_documented_intent"]
    assert len(processed) == 176 and groups.nunique() == 88
    assert processed.isna().sum().sum() == 0


def test_feature_sets_exclude_leakage():
    assert len(C.PRE_EXEC_FEATURES) == 13 and len(C.FULL_FEATURES) == 20
    for banned in ("Recommended_Action", C.TARGET_PRIMARY, C.TARGET_SECONDARY):
        assert banned not in C.FULL_FEATURES


HIGH_CASE = {"Environment": "QA", "Service_Category": "API", "Business_Criticality": "High",
             "Complexity_Level": 4, "Has_DB_Dependency": 1, "DB_Type": "PostgreSQL",
             "Has_Network_Change": 1, "Firewall_Rules_Count": 6, "External_Integrations_Count": 3,
             "Route_Ingress_Changed": 1, "Has_Config_Change": 1, "Owner_Availability": "Delayed",
             "Previous_Issues_Count": 2}


def test_engine_matches_historical_behaviour():
    hi = evaluate(HIGH_CASE, prediction="High")
    ids = [r["rule_id"] for r in hi["recommendations"]]
    assert ids[:3] == ["R1", "R2", "R7"] and set(ids) == {"R1", "R2", "R3", "R4", "R6", "R7"}
    assert [r["rule_id"] for r in hi["not_evaluable_at_this_stage"]] == ["R5"]
    lo = evaluate({"Environment": "Dev", "Has_DB_Dependency": 0, "Has_Network_Change": 0,
                   "Firewall_Rules_Count": 0, "External_Integrations_Count": 0,
                   "Has_Config_Change": 0, "Owner_Availability": "Available"}, prediction="Low")
    assert [r["rule_id"] for r in lo["recommendations"]] == ["R8"]


def test_percase_attribution_is_exact():
    """intercept + sum(contributions) must equal the model's logit for the class."""
    from backend.models.factory import make_model
    from backend.explain.explainer import per_case
    processed, _, _ = run_pipeline(save=False)
    X = processed[C.PRE_EXEC_FEATURES]
    y = processed[C.TARGET_PRIMARY].map({c: i for i, c in enumerate(C.RISK_CLASSES)}).astype(int)
    m = make_model("Logistic Regression", C.PRE_EXEC_FEATURES)
    m.fit(X, y)
    row = pd.DataFrame([HIGH_CASE])[C.PRE_EXEC_FEATURES]
    exp = per_case(m, row, 2)
    logit = m.decision_function(row)[0][2]
    assert np.isclose(exp["intercept"] + sum(c["contribution"] for c in exp["contributions"]),
                      logit, atol=1e-2)


@pytest.fixture(scope="module")
def client():
    from backend.api.main import app
    return TestClient(app)


def test_api_smoke(client):
    assert client.get("/api/health").json()["status"] == "ok"
    s = client.get("/api/dataset/summary").json()
    assert s["rows"] == 176 and s["integrity_checks"]["all_passed"]
    assert len(client.get("/api/recommend/rules").json()["rules"]) == 8
    assert len(client.get("/api/dataset/dictionary").json()["dictionary"]) == 27
    p = client.get("/api/research/progress").json()
    assert 0 < p["overall_pct"] <= 100
    r = client.get("/api/experiments/baseline/results")          # NaN-safety regression
    assert r.status_code == 200
    rows = r.json()["results"]
    assert len(rows) == 12 and all(x is None or isinstance(x, (int, float, str))
                                   for row in rows for x in row.values())
    m = client.get("/api/mode").json()                            # defense stamps
    assert m["mode"] in ("demo", "live_training") and m["records"] == 176
    h = client.get("/api/holdout").json()                         # sealed vault
    assert h["locked"] and h["test_rows"] == 36 and h["test_services"] == 18
    assert h["metrics"]["macro_f1"] == 0.559
    assert client.post("/api/demo/reset").status_code == 400      # reset needs confirm
    rc = client.get("/api/holdout/random_case").json()            # unseen-case tester
    assert rc["vault_size"] == 36 and rc["true"] in ("Low", "Medium", "High")
    assert rc["match"] == (rc["predicted"] == rc["true"])


def test_vault_roundtrip(client):
    import shutil
    from backend.research.vault import BASE
    payload = b"hello research vault"
    r = client.post("/api/vault/upload",
                    files={"file": ("test_doc.txt", payload, "text/plain")},
                    data={"note": "first version"})
    assert r.status_code == 200 and r.json()["n"] == 1
    docs = client.get("/api/vault").json()["docs"]
    assert any(d["name"] == "test_doc.txt" and d["latest"]["note"] == "first version"
               for d in docs)
    dl = client.get("/api/vault/download", params={"name": "test_doc.txt"})
    assert dl.status_code == 200 and dl.content == payload
    shutil.rmtree(BASE / "test_doc.txt")                          # cleanup
