"""Stage 1 of the external check (paper/external_check/PROTOCOL.md): freeze predictions for new, unseen services
BEFORE their ratings are requested.

Input: a workbook or CSV with one row per record (Dev and QA of each new service) and exactly these columns:
  Migration_ID, Service_Code, Environment, Service_Category, Business_Criticality, Complexity_Level,
  Has_DB_Dependency, DB_Type, Has_Network_Change, Firewall_Rules_Count, External_Integrations_Count,
  Route_Ingress_Changed, Has_Config_Change, Owner_Availability, Previous_Issues_Count
  (Source_Platform / Target_Platform may be present and are ignored). Any label or execution-phase column
  (Risk_Level, Outcome, Recommended_Action, Validation_Result, Validation_Attempts, DB_Access_Issue,
  Network_Access_Issue, Image_Build_Issue, Migration_Duration_Hours, Cutover_Delay_Days) makes the script stop.

The 176-record research workbook must be the real one (MRA_DATASET_XLSX or data/raw/...REAL_176.xlsx); the
synthetic example is accepted only with --allow-synthetic, for a dry run.

Run (from the repository root):
  python paper/external_check/stage1_freeze_predictions.py path/to/new_services.xlsx [--sheet NAME] [--allow-synthetic]
Writes paper/external_check/predictions_frozen.csv and paper/external_check/freeze_manifest.json.
"""
import sys, json, hashlib, argparse, datetime, platform, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
APP = HERE.parents[1]
sys.path.insert(0, str(APP))
import numpy as np, pandas as pd
import sklearn, xgboost
from sklearn.utils.class_weight import compute_sample_weight
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline, load_raw
from backend.models.factory import make_model, needs_sample_weight
from backend.recommend.engine import evaluate as recommend

FORBIDDEN = {C.TARGET_PRIMARY, C.TARGET_SECONDARY, C.DERIVED_LABEL} | set(C.EXEC_PHASE_FEATURES)
FEATS = list(C.PRE_EXEC_FEATURES)
CL = C.RISK_CLASSES
CRITERIA5 = ["Complexity_Level", "Owner_Availability", "Has_DB_Dependency", "Has_Network_Change", "External_Integrations_Count"]
PRE_RULES = ["R1", "R2", "R3", "R4", "R6"]

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def trig(rid, E):
    return {"R1": E.Has_DB_Dependency == 1,
            "R2": (E.Has_Network_Change == 1) | (E.Firewall_Rules_Count >= 5),
            "R3": E.Owner_Availability.isin(["Delayed", "Unknown"]),
            "R4": (E.Has_Config_Change == 1) & (E.Environment == "QA"),
            "R6": E.External_Integrations_Count >= 3}[rid]

def fit_all(name, feats, X, y):
    m = make_model(name, feats)
    kw = {"clf__sample_weight": compute_sample_weight("balanced", y)} if needs_sample_weight(name) else {}
    m.fit(X[feats], y, **kw)
    return m

def proba_aligned(m, X, feats):
    raw = m.predict_proba(X[feats]); pr = np.zeros((len(X), 3))
    for j, cc in enumerate(m.classes_): pr[:, int(cc)] = raw[:, j]
    return pr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("--sheet", default=None); ap.add_argument("--allow-synthetic", action="store_true")
    a = ap.parse_args()
    inp = Path(a.input).resolve()
    if C.IS_SYNTHETIC_DATA and not a.allow_synthetic:
        sys.exit("The 176-record workbook in use is the synthetic example; point MRA_DATASET_XLSX at the real file (or pass --allow-synthetic for a dry run).")

    # ---- new records: read, refuse labels, clean exactly as the pipeline does
    new = pd.read_csv(inp) if inp.suffix.lower() == ".csv" else pd.read_excel(inp, sheet_name=a.sheet or 0)
    bad = sorted(set(new.columns) & FORBIDDEN)
    if bad:
        sys.exit(f"REFUSED: the input contains label or execution-phase columns {bad}. Request the 13 planning attributes only.")
    need = C.ID_COLS + FEATS
    missing = [c for c in need if c not in new.columns]
    if missing:
        sys.exit(f"missing columns: {missing}")
    new = new[need].copy()
    assert new.Migration_ID.is_unique, "Migration_ID must be unique"
    new["DB_Type"] = new["DB_Type"].fillna(C.DB_TYPE_FILL)
    assert new[FEATS].isna().sum().sum() == 0, "missing values in the planning attributes"
    assert set(new.Environment) <= {"Dev", "QA"}
    new["Rule_Score"] = sum(trig(r, new).astype(int) for r in PRE_RULES)

    # ---- identifiers: the tracker's Migration_IDs may repeat numbers used in the 176-record extract; the study uses
    #      its own identifiers for the new records (MIG-X01 ...), and the private mapping stays next to the input file
    raw176 = load_raw()
    overlap = sorted(set(new.Migration_ID) & set(raw176.Migration_ID))
    svc_overlap = sorted(set(new.Service_Code) & set(raw176[C.GROUP_COL]))
    if svc_overlap:
        sys.exit(f"ABORT: Service_Code values already exist in the 176-record extract: {svc_overlap}")
    new = new.sort_values(["Service_Code", "Environment"]).reset_index(drop=True)
    new["Original_Migration_ID"] = new.Migration_ID
    new["Migration_ID"] = [f"MIG-X{i + 1:02d}" for i in range(len(new))]
    map_path = inp.with_name("id_mapping_private.csv")
    new[["Original_Migration_ID", "Migration_ID", "Service_Code", "Environment"]].to_csv(map_path, index=False)
    unseen = {c: sorted(set(new[c].astype(str)) - set(raw176[c].fillna(C.DB_TYPE_FILL).astype(str)))
              for c in ["Service_Category", "DB_Type", "Owner_Availability", "Business_Criticality", "Environment"]}
    unseen = {c: v for c, v in unseen.items() if v}

    # ---- 176-record research data and serving fits (all records, as the registry does)
    P, G, meta = run_pipeline(save=False)
    assert meta["integrity"]["all_passed"], "integrity checks of the 176-record workbook failed"
    assert len(P) == 176
    P["Rule_Score"] = sum(trig(r, P).astype(int) for r in PRE_RULES)
    y = P[C.TARGET_PRIMARY].map({c: i for i, c in enumerate(CL)}).astype(int)
    models = {
        "LR13": fit_all("Logistic Regression", FEATS, P, y),
        "RF13": fit_all("Random Forest", FEATS, P, y),
        "XGB13": fit_all("XGBoost", FEATS, P, y),
        "LR_rulecount": fit_all("Logistic Regression", ["Rule_Score"], P, y),
        "LR_criteria5": fit_all("Logistic Regression", CRITERIA5, P, y),
    }
    feats_of = {"LR13": FEATS, "RF13": FEATS, "XGB13": FEATS, "LR_rulecount": ["Rule_Score"], "LR_criteria5": CRITERIA5}

    out = new[C.ID_COLS + ["Environment", "Rule_Score"]].copy()
    for k, m in models.items():
        pr = proba_aligned(m, new, feats_of[k])
        out[f"{k}_pred"] = [CL[i] for i in pr.argmax(1)]
        if k == "LR13":
            for i, c in enumerate(CL): out[f"LR13_p{c}"] = pr[:, i].round(4)
    out["flag_rule_ge3"] = (new.Rule_Score >= 3).astype(int)
    fired = []
    for i, row in new.iterrows():
        feats = {f: (row[f].item() if hasattr(row[f], "item") else row[f]) for f in FEATS}
        rec = recommend(feats, prediction=out.loc[i, "LR13_pred"])
        fired.append(";".join(r["rule_id"] for r in rec["recommendations"]))
    out["rules_fired_LR13"] = fired

    pred_path = HERE / "predictions_frozen.csv"
    out.to_csv(pred_path, index=False)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=APP, capture_output=True, text=True).stdout.strip() or None
    except Exception:
        commit = None
    manifest = {
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "protocol": "paper/external_check/PROTOCOL.md", "protocol_sha256": sha256(HERE / "PROTOCOL.md"),
        "input_file": inp.name, "input_sha256": sha256(inp), "n_records": int(len(out)),
        "n_services": int(out.Service_Code.nunique()),
        "predictions_file": pred_path.name, "predictions_sha256": sha256(pred_path),
        "research_workbook": C.RAW_XLSX.name, "research_workbook_sha256": sha256(C.RAW_XLSX),
        "research_workbook_is_synthetic": bool(C.IS_SYNTHETIC_DATA),
        "serving_fit": "all 176 records, class_weight balanced, declared configurations (backend/models/factory.py), seed %d" % C.SEED,
        "models": {k: str(m.named_steps["clf"]) for k, m in models.items()},
        "features_13": FEATS, "criteria5": CRITERIA5, "pre_exec_rules_counted": PRE_RULES,
        "identifiers": {"study_ids_assigned": True, "original_ids_overlapping_176_extract": overlap,
                        "private_mapping_file": map_path.name, "service_codes": sorted(out.Service_Code.unique())},
        "categories_unseen_in_176_extract": unseen,
        "repository_version": C.APP_VERSION, "git_commit": commit,
        "python": platform.python_version(), "scikit_learn": sklearn.__version__, "xgboost": xgboost.__version__,
        "numpy": np.__version__, "pandas": pd.__version__,
    }
    (HERE / "freeze_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"frozen {len(out)} records of {manifest['n_services']} services at {manifest['frozen_at_utc']}")
    print("predictions_frozen.csv sha256:", manifest["predictions_sha256"])
    print("input sha256:", manifest["input_sha256"])
    print(f"study identifiers MIG-X01..MIG-X{len(out):02d} assigned; private mapping written to {map_path} (do not commit)")
    if unseen: print("NOTE: categories unseen in the 176-record extract:", unseen)
    if C.IS_SYNTHETIC_DATA:
        print("WARNING: dry run on the synthetic workbook; not a freeze.")

if __name__ == "__main__":
    main()
