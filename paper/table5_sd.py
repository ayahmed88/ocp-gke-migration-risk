from pathlib import Path
"""Table 5 paired differences with a single SD convention (sample SD, ddof=1), same folds/models as main_analyses.py."""
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score
from sklearn.utils.class_weight import compute_sample_weight
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve
from backend.models.factory import make_model, needs_sample_weight
P, G, _ = run_pipeline(save=False)
tr, te = vault_carve(P, P[C.TARGET_PRIMARY], G)
pool, gp = P.iloc[tr].reset_index(drop=True), G.iloc[tr].reset_index(drop=True)
CL = C.RISK_CLASSES; code = {c: i for i, c in enumerate(CL)}
def trig(rid, E):
    return {"R1": E.Has_DB_Dependency == 1, "R2": (E.Has_Network_Change == 1) | (E.Firewall_Rules_Count >= 5),
            "R3": E.Owner_Availability.isin(["Delayed", "Unknown"]), "R4": (E.Has_Config_Change == 1) & (E.Environment == "QA"),
            "R6": E.External_Integrations_Count >= 3}[rid]
pool["Rule_Score"] = sum(trig(r, pool).astype(int) for r in ["R1", "R2", "R3", "R4", "R6"])
ye = pool[C.TARGET_PRIMARY].map(code).astype(int)
def cv(model, feats):
    out = []
    for rep in range(5):
        for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=42 + rep).split(pool[feats], ye, gp):
            m = make_model(model, feats)
            kw = {"clf__sample_weight": compute_sample_weight("balanced", ye.iloc[a])} if needs_sample_weight(model) else {}
            m.fit(pool.iloc[a][feats], ye.iloc[a], **kw)
            pe = m.predict(pool.iloc[b][feats]); yt = ye.iloc[b].to_numpy()
            out.append(f1_score([CL[i] for i in yt], [CL[i] for i in pe], average="macro", zero_division=0))
    return np.array(out)
lr = cv("Logistic Regression", C.PRE_EXEC_FEATURES); assert abs(lr.mean() - 0.6339526050735212) < 1e-9, lr.mean()
specs = {"XGBoost": ("XGBoost", C.PRE_EXEC_FEATURES), "Random Forest": ("Random Forest", C.PRE_EXEC_FEATURES),
         "Rule-trigger count": ("Logistic Regression", ["Rule_Score"]), "Complexity + Criticality": ("Logistic Regression", ["Complexity_Level", "Business_Criticality"]),
         "Complexity only": ("Logistic Regression", ["Complexity_Level"]), "Criticality only": ("Logistic Regression", ["Business_Criticality"]),
         "Previous_Issues only": ("Logistic Regression", ["Previous_Issues_Count"])}
res = {}
for k, (m, f) in specs.items():
    d = lr - cv(m, f); J = len(d); v = np.var(d, ddof=1); t = d.mean() / np.sqrt((1 / J + 28 / 112) * v)
    res[k] = {"mean": round(float(d.mean()), 4), "sd_ddof0": round(float(d.std(ddof=0)), 4), "sd_ddof1": round(float(d.std(ddof=1)), 4),
              "wins": int((d > 0).sum()), "p": round(float(2 * stats.t.sf(abs(t), J - 1)), 4)}
print(json.dumps(res, indent=1)); json.dump(res, open("table5_sd.json", "w"), indent=1)
