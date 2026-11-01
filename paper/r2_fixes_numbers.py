from pathlib import Path
"""Numbers needed for the round-2 fixes: Dev-subset Low counts per fold; Owner_Availability paired-difference interval and win/tie/loss."""
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve
from backend.models.factory import make_model
P, G, _ = run_pipeline(save=False)
tr, te = vault_carve(P, P[C.TARGET_PRIMARY], G)
pool, gp = P.iloc[tr].reset_index(drop=True), G.iloc[tr].reset_index(drop=True)
y = pool[C.TARGET_PRIMARY].map({c: i for i, c in enumerate(C.RISK_CLASSES)}).astype(int)
F13 = C.PRE_EXEC_FEATURES; F12 = [f for f in F13 if f != "Owner_Availability"]
low_dev, diffs = [], []
for rep in range(5):
    for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=42 + rep).split(pool, y, gp):
        te_rows = pool.iloc[b]
        low_dev.append(int(((te_rows["Environment"] == "Dev") & (te_rows[C.TARGET_PRIMARY] == "Low")).sum()))
        m13 = make_model("Logistic Regression", F13).fit(pool.iloc[a][F13], y.iloc[a])
        m12 = make_model("Logistic Regression", F12).fit(pool.iloc[a][F12], y.iloc[a])
        f13 = f1_score(y.iloc[b], m13.predict(pool.iloc[b][F13]), average="macro", zero_division=0)
        f12 = f1_score(y.iloc[b], m12.predict(pool.iloc[b][F12]), average="macro", zero_division=0)
        diffs.append(f13 - f12)
d = np.array(diffs); J = len(d); v = np.var(d, ddof=1); se = np.sqrt((1 / J + 28 / 112) * v); tcrit = stats.t.ppf(0.975, J - 1)
out = {"low_dev_per_fold": low_dev, "folds_with_zero_low_dev": int(sum(1 for x in low_dev if x == 0)),
       "low_dev_min_max": [min(low_dev), max(low_dev)], "pool_low_dev_total": int(((pool["Environment"] == "Dev") & (pool[C.TARGET_PRIMARY] == "Low")).sum()),
       "owner_diff_mean": round(float(d.mean()), 4), "owner_diff_sd": round(float(d.std(ddof=1)), 4),
       "owner_ci95_nb": [round(float(d.mean() - tcrit * se), 3), round(float(d.mean() + tcrit * se), 3)],
       "wins_13": int((d > 1e-12).sum()), "ties": int((abs(d) <= 1e-12).sum()), "losses_13": int((d < -1e-12).sum())}
print(json.dumps(out, indent=1)); json.dump(out, open("r2_fixes_numbers.json", "w"), indent=1)
