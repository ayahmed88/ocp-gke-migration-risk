"""Revision analyses (5 Nov 2026) for the decision-letter items on the two headline comparisons:
- Table 5: Holm and Benjamini-Hochberg adjustments of the 18 corrected-test p values (from r11_presubmission_analyses.json);
- Table 7: the label itself as a flagging policy (ceiling set by the label construction), the criteria-only model at its own flag
  rate, a service-level bootstrap of the LR-minus-rule-count difference in captured failures and delays, and a Logistic Regression
  trained directly on first-attempt failure on the same 25 folds (capture at the same flag rate; ranking of the failure outcome
  against the rule count and against the label-trained P(High), corrected resampled t-test).
Selection pool only (140 records, 70 services), official folds; the holdout is not touched. Gate: the official 25-fold macro-F1
values are reproduced bit for bit before anything else runs.
Writes paper/results/r12_revision_analyses.json.
Run: python paper/r12_revision_analyses.py   (needs the real workbook: MRA_DATASET_XLSX)
"""
import sys, json
from pathlib import Path
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import numpy as np, pandas as pd
from scipy import stats
from scipy.optimize import minimize
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (f1_score, accuracy_score, balanced_accuracy_score, precision_score, recall_score,
                             roc_auc_score, average_precision_score, confusion_matrix, brier_score_loss, log_loss)
from sklearn.utils.class_weight import compute_sample_weight
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve
from backend.models.factory import make_model, needs_sample_weight

OUT = Path(__file__).resolve().parent / "results"; (OUT / "figs").mkdir(exist_ok=True)
CL = C.RISK_CLASSES; code = {c: i for i, c in enumerate(CL)}
FEATS = list(C.PRE_EXEC_FEATURES)
R = {"scope": "selection pool (140 records, 70 services), official 5x5 grouped folds, seed base 42; holdout closed", "date": "2026-11-05"}

P, G, _ = run_pipeline(save=False)
tr_idx, te_idx = vault_carve(P, P[C.TARGET_PRIMARY], G)
pool, gpool = P.iloc[tr_idx].reset_index(drop=True), G.iloc[tr_idx].reset_index(drop=True)
hold, ghold = P.iloc[te_idx].reset_index(drop=True), G.iloc[te_idx].reset_index(drop=True)
assert len(pool) == 140 and len(hold) == 36

# ---------------------------------------------------------------- derived columns
def trig(rid, E):
    return {"R1": E.Has_DB_Dependency == 1,
            "R2": (E.Has_Network_Change == 1) | (E.Firewall_Rules_Count >= 5),
            "R3": E.Owner_Availability.isin(["Delayed", "Unknown"]),
            "R4": (E.Has_Config_Change == 1) & (E.Environment == "QA"),
            "R5": (E.Image_Build_Issue == 1) & (E.Environment == "QA"),
            "R6": E.External_Integrations_Count >= 3}[rid]
PRE_RULES = ["R1", "R2", "R3", "R4", "R6"]
for df, g in ((P, G), (pool, gpool), (hold, ghold)):
    df["Rule_Score"] = sum(trig(r, df).astype(int) for r in PRE_RULES)
    df["BC_num"] = df.Business_Criticality.map({"Low": 0, "Medium": 1, "High": 2}).astype(float)
    dev_lab = df.assign(_s=g.values)[lambda d: d.Environment == "Dev"].set_index("_s").Risk_Level
    df["Dev_Label"] = np.where(df.Environment == "QA", g.map(dev_lab).fillna("none").values, "none")
# permutation-importance gate runs before the feature list is extended (the app's function re-runs the pipeline)
from backend.explain import explainer as EXX
stored = {r["feature"]: r["f1_drop_mean"] for r in json.loads((APP / "data/results/xai_global.json").read_text())["permutation_importance"]}
regen = {r["feature"]: r["f1_drop_mean"] for r in EXX._grouped_permutation_importance()}
assert all(abs(stored[f] - regen[f]) < 1e-9 for f in stored), "permutation-importance gate failed"
C.NOMINAL_COLS = list(C.NOMINAL_COLS) + ["Dev_Label"]          # one-hot encode the prior-level feature

ye = pool[C.TARGET_PRIMARY].map(code).astype(int)
FOLDS = []
for rep in range(C.CV_N_REPEATS):
    skf = StratifiedGroupKFold(n_splits=C.CV_N_SPLITS, shuffle=True, random_state=C.SEED + rep)
    for a, b in skf.split(pool[FEATS], ye, gpool):
        FOLDS.append((rep, a, b))
assert len(FOLDS) == 25
n_te = np.array([len(b) for _, _, b in FOLDS]); n_tr = np.array([len(a) for _, a, _ in FOLDS])
RATIO = float(n_te.mean() / n_tr.mean())

def fit_predict(model_name, feats, a, b, y=None, X=None):
    X = pool if X is None else X
    y = ye if y is None else y
    m = make_model(model_name, feats)
    kw = {"clf__sample_weight": compute_sample_weight("balanced", y.iloc[a])} if needs_sample_weight(model_name) else {}
    m.fit(X[feats].iloc[a], y.iloc[a], **kw)
    k = int(y.max()) + 1
    raw = m.predict_proba(X[feats].iloc[b]); pr = np.zeros((len(b), k))
    for j, cc in enumerate(m.classes_): pr[:, int(cc)] = raw[:, j]
    return m, m.predict(X[feats].iloc[b]).astype(int), pr

def f1m(yt, pe, labels): return f1_score(yt, pe, labels=labels, average="macro", zero_division=0)

def fold_metrics(yt, pe, pr):
    out = {"f1_macro": f1m(yt, pe, [0, 1, 2]), "f1_present": f1m(yt, pe, sorted(set(yt.tolist()))),
           "accuracy": accuracy_score(yt, pe), "n": len(yt), "n_low": int((yt == 0).sum())}
    out["auc_ovr_macro"] = roc_auc_score(yt, pr, multi_class="ovr", average="macro", labels=[0, 1, 2]) if len(set(yt)) == 3 else np.nan
    for c in range(3):
        yb = (yt == c).astype(int)
        out[f"auc_{CL[c]}"] = roc_auc_score(yb, pr[:, c]) if 0 < yb.sum() < len(yb) else np.nan
    yh = (yt == 2).astype(int)
    out["high_ap"] = average_precision_score(yh, pr[:, 2]) if 0 < yh.sum() < len(yh) else np.nan
    out["high_recall"] = recall_score(yh, (pe == 2).astype(int), zero_division=0)
    out["high_precision"] = precision_score(yh, (pe == 2).astype(int), zero_division=0)
    out["low_recall"] = recall_score((yt == 0).astype(int), (pe == 0).astype(int), zero_division=0) if (yt == 0).any() else np.nan
    return out

def run_cv(model_name, feats):
    rows, oof_p, oof_c = [], np.zeros((5, len(pool), 3)), np.zeros((5, len(pool)), dtype=int)
    for (rep, a, b) in FOLDS:
        _, pe, pr = fit_predict(model_name, feats, a, b)
        yt = ye.iloc[b].to_numpy()
        rows.append({"rep": rep, **fold_metrics(yt, pe, pr)})
        oof_p[rep, b] = pr; oof_c[rep, b] = pe
    return pd.DataFrame(rows), oof_p, oof_c

def msd(s):
    s = pd.Series(s).dropna()
    return {"mean": round(float(s.mean()), 6), "sd": round(float(s.std(ddof=1)), 6), "sd_pop": round(float(s.std(ddof=0)), 6), "n": int(len(s))}

def paired(da, db):
    d = np.asarray(da) - np.asarray(db); J = len(d); var = d.var(ddof=1)
    se = np.sqrt((1 / J + RATIO) * var) if var > 0 else 0.0
    t = d.mean() / se if se > 0 else np.inf
    tc = stats.t.ppf(0.975, J - 1)
    return {"mean": round(float(d.mean()), 6), "sd": round(float(d.std(ddof=1)), 6), "sd_pop": round(float(d.std(ddof=0)), 6),
            "ahead": int((d > 0).sum()), "tied": int((d == 0).sum()), "behind": int((d < 0).sum()),
            "p_corrected": round(float(2 * stats.t.sf(abs(t), J - 1)), 4) if se > 0 else None,
            "ci95_corrected": [round(float(d.mean() - tc * se), 4), round(float(d.mean() + tc * se), 4)]}


# ---------------------------------------------------------------- GATE: official figures
CV = {n: run_cv(n, FEATS) for n in ["Logistic Regression", "Random Forest", "XGBoost"]}
gate = {n: float(CV[n][0].f1_macro.mean()) for n in CV}
assert gate["Logistic Regression"] == 0.6339526050735212, gate
assert gate["XGBoost"] == 0.5915302092371963, gate
assert gate["Random Forest"] == 0.5386608264991757, gate
R["gate_official_cv"] = gate
lrf, lr_p, lr_c = CV["Logistic Regression"]

# ---------------------------------------------------------------- Table 5: multiplicity adjustments of the 18 corrected tests
r11 = json.loads((OUT / "r11_presubmission_analyses.json").read_text())
T5 = r11["cv_table"]
comparators = ["XGBoost", "Random Forest", "LR: documented criteria + Previous_Issues_Count", "LR: documented criteria (5 planning attributes)",
               "LR: rule-trigger count", "LR: Complexity + Criticality", "LR: Complexity_Level only", "LR: Business_Criticality only", "LR: Previous_Issues_Count only"]
tests = []
for c in comparators:
    for metric, key in (("macro-F1", "LR13_minus_this_f1"), ("High-vs-rest ROC-AUC", "LR13_minus_this_highAUC")):
        tests.append({"comparator": c, "metric": metric, "p": T5[c][key]["p_corrected"], "ci95_corrected": T5[c][key]["ci95_corrected"], "mean_diff": T5[c][key]["mean"]})
def holm(ps):
    m = len(ps); order = np.argsort(ps); adj = np.empty(m); running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * ps[i]); adj[i] = min(1.0, running)
    return adj
def bh(ps):
    m = len(ps); order = np.argsort(ps); adj = np.empty(m); running = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]; running = min(running, m / (rank + 1) * ps[i]); adj[i] = min(1.0, running)
    return adj
ps = np.array([t["p"] for t in tests]); h18 = holm(ps); b18 = bh(ps)
for t, a, b2 in zip(tests, h18, b18):
    t["holm_18"] = round(float(a), 4); t["bh_18"] = round(float(b2), 4)
for metric in ("macro-F1", "High-vs-rest ROC-AUC"):
    idx = [i for i, t in enumerate(tests) if t["metric"] == metric]
    h9 = holm(ps[idx]); b9 = bh(ps[idx])
    for j, i in enumerate(idx):
        tests[i]["holm_9_within_metric"] = round(float(h9[j]), 4); tests[i]["bh_9_within_metric"] = round(float(b9[j]), 4)
R["table5_multiplicity"] = {"tests": tests, "n_tests": 18,
                            "significant_holm_18": [f'{t["comparator"]} | {t["metric"]}' for t in tests if t["holm_18"] < 0.05],
                            "significant_bh_18": [f'{t["comparator"]} | {t["metric"]}' for t in tests if t["bh_18"] < 0.05],
                            "note": "p values are the corrected resampled t-test values of r11_presubmission_analyses.json (rounded to 4 decimals there); Holm controls the family-wise error rate, Benjamini-Hochberg the false discovery rate"}

# ---------------------------------------------------------------- Table 7 additions (seed base 42, out-of-fold)
fail = (pool.Validation_Result == "Fail").to_numpy(); delay = (pool.Outcome == "Delayed").to_numpy(); prob = (pool.Outcome != "Success").to_numpy()
def policy_stats(flag):
    flag = np.asarray(flag, dtype=bool)
    return {"flag_rate": round(float(flag.mean()), 3), "flagged": int(flag.sum()),
            "failures_captured": round(float(flag[fail].mean()), 3), "failures_captured_n": int(flag[fail].sum()),
            "delays_captured": round(float(flag[delay].mean()), 3), "delays_captured_n": int(flag[delay].sum()),
            "any_problem_captured": round(float(flag[prob].mean()), 3), "any_problem_precision": round(float(prob[flag].mean()), 3) if flag.any() else None}
def over_reps(fn):
    rs = [fn(r) for r in range(5)]
    return {k: {"mean": round(float(np.mean([x[k] for x in rs])), 3), "min": round(float(np.min([x[k] for x in rs])), 3),
                "max": round(float(np.max([x[k] for x in rs])), 3)} for k in rs[0] if rs[0][k] is not None}
CRIT5 = ["Complexity_Level", "Owner_Availability", "Has_DB_Dependency", "Has_Network_Change", "External_Integrations_Count"]
crit = run_cv("Logistic Regression", CRIT5); crit_c, crit_p = crit[2], crit[1]
assert abs(float(crit[0].f1_macro.mean()) - 0.627023) < 1e-5, float(crit[0].f1_macro.mean())
T7 = {"label_High_as_policy (ceiling set by the label construction)": policy_stats(pool.Risk_Level == "High"),
      "criteria-only LR (5 attributes) predicts High": over_reps(lambda r: policy_stats(crit_c[r] == 2)),
      "LR13 predicts High (reference)": over_reps(lambda r: policy_stats(lr_c[r] == 2)),
      "rule-trigger count >= 3 (reference)": policy_stats(pool.Rule_Score >= 3)}
# service-level bootstrap of the difference in captured failures and delays: LR13-High (per repeat) minus rule count >= 3
svc = gpool.to_numpy(); us = np.unique(svc); rng = np.random.default_rng(20261105)
rule3 = (pool.Rule_Score >= 3).to_numpy()
def captured(flag, mask, idx):
    f, m = flag[idx], mask[idx]
    return float(f[m].mean()) if m.any() else np.nan
diffs = {"failures": [], "delays": [], "failures_crit": []}
for _ in range(5000):
    pick = rng.choice(us, size=len(us), replace=True)
    idx = np.concatenate([np.where(svc == s)[0] for s in pick])
    d_f = np.nanmean([captured(lr_c[r] == 2, fail, idx) - captured(rule3, fail, idx) for r in range(5)])
    d_d = np.nanmean([captured(lr_c[r] == 2, delay, idx) - captured(rule3, delay, idx) for r in range(5)])
    d_c = np.nanmean([captured(lr_c[r] == 2, fail, idx) - captured(crit_c[r] == 2, fail, idx) for r in range(5)])
    diffs["failures"].append(d_f); diffs["delays"].append(d_d); diffs["failures_crit"].append(d_c)
def summ(v):
    v = np.array(v); v = v[~np.isnan(v)]
    return {"point_mean_over_repeats": None, "ci95": [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)],
            "share_of_draws_le_0": round(float((v <= 0).mean()), 3), "draws": int(len(v))}
BS = {k: summ(v) for k, v in diffs.items()}
BS["failures"]["point_mean_over_repeats"] = round(float(np.mean([captured(lr_c[r] == 2, fail, np.arange(140)) - captured(rule3, fail, np.arange(140)) for r in range(5)])), 3)
BS["delays"]["point_mean_over_repeats"] = round(float(np.mean([captured(lr_c[r] == 2, delay, np.arange(140)) - captured(rule3, delay, np.arange(140)) for r in range(5)])), 3)
BS["failures_crit"]["point_mean_over_repeats"] = round(float(np.mean([captured(lr_c[r] == 2, fail, np.arange(140)) - captured(crit_c[r] == 2, fail, np.arange(140)) for r in range(5)])), 3)
BS["note"] = "5000 resamples of the 70 pool services with replacement (seed 20261105); each draw averages the difference over the five repeats of seed base 42; 'failures' = LR13-High minus rule count >= 3, 'failures_crit' = LR13-High minus criteria-only-High, 'delays' = LR13-High minus rule count >= 3"
T7["bootstrap_differences"] = BS
# direct failure model on the same folds: LR13 and rule count trained on first-attempt failure
yfail = pd.Series(fail.astype(int))
rows = []; oof_fail = np.zeros((5, 140))
for (rep, a, b) in FOLDS:
    for name, feats in [("LR13 trained on failure", FEATS), ("rule count trained on failure", ["Rule_Score"])]:
        _, pe, pr = fit_predict("Logistic Regression", feats, a, b, y=yfail)
        yt = yfail.iloc[b].to_numpy()
        if name.startswith("LR13"):
            oof_fail[rep, b] = pr[:, 1]
        rows.append({"rep": rep, "model": name, "auc_fail": roc_auc_score(yt, pr[:, 1]) if 0 < yt.sum() < len(yt) else np.nan,
                     "ap_fail": average_precision_score(yt, pr[:, 1]) if 0 < yt.sum() < len(yt) else np.nan})
    # label-trained P(High) and the raw rule count as rankers of the failure outcome, same folds
    yt = yfail.iloc[b].to_numpy()
    rows.append({"rep": rep, "model": "label-trained LR13 P(High)", "auc_fail": roc_auc_score(yt, lr_p[rep, b, 2]) if 0 < yt.sum() < len(yt) else np.nan,
                 "ap_fail": average_precision_score(yt, lr_p[rep, b, 2]) if 0 < yt.sum() < len(yt) else np.nan})
    rows.append({"rep": rep, "model": "raw rule count", "auc_fail": roc_auc_score(yt, pool.Rule_Score.iloc[b]) if 0 < yt.sum() < len(yt) else np.nan,
                 "ap_fail": average_precision_score(yt, pool.Rule_Score.iloc[b]) if 0 < yt.sum() < len(yt) else np.nan})
fd = pd.DataFrame(rows)
FM = {m: {k: msd(fd[fd.model == m][k]) for k in ["auc_fail", "ap_fail"]} for m in fd.model.unique()}
FM["folds_with_defined_auc"] = int(fd[fd.model == "LR13 trained on failure"].auc_fail.notna().sum())
def pair_models(m1, m2, k="auc_fail"):
    x = fd[fd.model == m1].sort_values("rep", kind="stable")[k].to_numpy(); y = fd[fd.model == m2].sort_values("rep", kind="stable")[k].to_numpy()
    ok = ~np.isnan(x) & ~np.isnan(y); return paired(x[ok], y[ok])
FM["LR13-fail minus rule-count-fail (AUC)"] = pair_models("LR13 trained on failure", "rule count trained on failure")
FM["LR13-fail minus raw rule count (AUC)"] = pair_models("LR13 trained on failure", "raw rule count")
FM["label-trained P(High) minus raw rule count (AUC)"] = pair_models("label-trained LR13 P(High)", "raw rule count")
FM["LR13-fail minus label-trained P(High) (AUC)"] = pair_models("LR13 trained on failure", "label-trained LR13 P(High)")
# capture at the same flag rate as LR13-High (per repeat: flag the same number of records, ranked by OOF P(fail))
def topk_policy(r):
    k = int((lr_c[r] == 2).sum()); thr = np.sort(oof_fail[r])[::-1][k - 1]
    return policy_stats(oof_fail[r] >= thr)
FM["LR13-fail flags at the LR13-High flag rate"] = over_reps(topk_policy)
FM["prevalence_fail_pool"] = round(float(fail.mean()), 3)
T7["direct_failure_model"] = FM
R["table7_additions"] = T7
R["spearman_from_r11"] = r11["operational"]["spearman"]
(OUT / "r12_revision_analyses.json").write_text(json.dumps(R, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
print(json.dumps({"gate": gate, "holm18_significant": R["table5_multiplicity"]["significant_holm_18"], "bh18_significant": R["table5_multiplicity"]["significant_bh_18"],
                  "T7": {k: v for k, v in T7.items() if k != "direct_failure_model"}, "direct_failure": FM}, indent=1, default=str))
print("DONE")
