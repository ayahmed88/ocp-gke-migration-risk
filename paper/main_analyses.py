"""Additional analyses (basket B) for the manuscript, on the official v45 pipeline.

Runs on the pinned environment. Re-uses the app's pipeline, vault carve and model
factory unchanged. Gate: the LR fold loop must reproduce the official 25-fold
macro-F1 exactly, and the holdout refit must reproduce the locked confusion matrix.
Writes results/main_analyses.json and figure mocks to figs/.
"""
import sys, json, itertools
from pathlib import Path
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import numpy as np, pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (f1_score, accuracy_score, balanced_accuracy_score,
                             precision_score, recall_score, roc_auc_score,
                             confusion_matrix, cohen_kappa_score, brier_score_loss)
from sklearn.utils.class_weight import compute_sample_weight
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve
from backend.models.factory import make_model, needs_sample_weight

OUT = Path(__file__).resolve().parent / "results"; (OUT / "figs").mkdir(exist_ok=True)
CL = C.RISK_CLASSES                       # ['Low','Medium','High'] -> 0,1,2 (ordinal)
code = {c: i for i, c in enumerate(CL)}
R = {}

P, G, _ = run_pipeline(save=False)
tr, te = vault_carve(P, P[C.TARGET_PRIMARY], G)
pool, gpool = P.iloc[tr].reset_index(drop=True), G.iloc[tr].reset_index(drop=True)
hold, ghold = P.iloc[te].reset_index(drop=True), G.iloc[te].reset_index(drop=True)
assert len(pool) == 140 and len(hold) == 36

# rule-trigger helpers (same definitions as tests/test_rules_evidence.py)
PHRASE = {"R1": "validate db connectivity", "R2": "verify firewall/network rules",
          "R3": "confirm owner availability", "R4": "review environment-specific configuration",
          "R5": "review image build pipeline", "R6": "test external integrations",
          "R7": "schedule extended validation window", "R8": "standard validation and cutover checklist"}
def trig(rid, E):
    return {"R1": E.Has_DB_Dependency == 1,
            "R2": (E.Has_Network_Change == 1) | (E.Firewall_Rules_Count >= 5),
            "R3": E.Owner_Availability.isin(["Delayed", "Unknown"]),
            "R4": (E.Has_Config_Change == 1) & (E.Environment == "QA"),
            "R5": (E.Image_Build_Issue == 1) & (E.Environment == "QA"),
            "R6": E.External_Integrations_Count >= 3}[rid]
PRE_RULES = ["R1", "R2", "R3", "R4", "R6"]   # pre-execution triggers usable as a scorecard (R5 is execution-stage)
for df in (P, pool, hold):
    df["Rule_Score"] = sum(trig(r, df).astype(int) for r in PRE_RULES)

# ---------------------------------------------------------------- fold engine
def folds(X, y_enc, groups, base):
    for rep in range(C.CV_N_REPEATS):
        skf = StratifiedGroupKFold(n_splits=C.CV_N_SPLITS, shuffle=True, random_state=base + rep)
        for a, b in skf.split(X, y_enc, groups):
            yield rep, a, b

def run_cv(model_name, feats, base=C.SEED, keep_oof=False):
    X = pool[feats]; y = pool[C.TARGET_PRIMARY]; ye = y.map(code).astype(int)
    rows, oof = [], {}
    for rep, a, b in folds(X, ye, gpool, base):
        m = make_model(model_name, feats)
        kw = {"clf__sample_weight": compute_sample_weight("balanced", ye.iloc[a])} if needs_sample_weight(model_name) else {}
        m.fit(X.iloc[a], ye.iloc[a], **kw)
        raw = m.predict_proba(X.iloc[b]); pr = np.zeros((len(b), 3))
        for j, cc in enumerate(m.classes_): pr[:, int(cc)] = raw[:, j]
        pe = m.predict(X.iloc[b]); yt = ye.iloc[b].to_numpy()
        yt_l = [CL[i] for i in yt]; pe_l = [CL[i] for i in pe]
        try: auc = roc_auc_score(yt, pr, multi_class="ovr", average="macro", labels=[0, 1, 2])
        except ValueError: auc = np.nan
        rows.append({"rep": rep, "n_test": len(b), "n_train": len(a),
                     "f1_macro": f1_score(yt_l, pe_l, average="macro", zero_division=0),
                     "accuracy": accuracy_score(yt, pe),
                     "auc": auc,
                     "low_in_test": int((yt == 0).sum()), "low_predicted": int((pe == 0).sum()),
                     "high_precision": precision_score(yt, pe, labels=[2], average="macro", zero_division=0),
                     "high_recall": recall_score(yt, pe, labels=[2], average="macro", zero_division=0),
                     "high_f1": f1_score(yt, pe, labels=[2], average="macro", zero_division=0),
                     "qwk": cohen_kappa_score(yt, pe, labels=[0, 1, 2], weights="quadratic"),
                     "mad": float(np.mean(np.abs(yt - pe)))})
        if keep_oof and rep == 0:
            for i, idx in enumerate(b): oof[int(idx)] = (int(yt[i]), int(pe[i]), pr[i].tolist())
    return pd.DataFrame(rows), oof

def ms(s): return {"mean": round(float(np.nanmean(s)), 4), "sd": round(float(np.nanstd(s)), 4)}

# --------------------------------------------------- GATE: reproduce officials
off = {}
for name in ["Dummy (prior)", "Logistic Regression", "Random Forest", "XGBoost"]:
    f, oof = run_cv(name, C.PRE_EXEC_FEATURES, keep_oof=True)
    off[name] = (f, oof)
gate = {n: float(off[n][0].f1_macro.mean()) for n in off}
assert gate["Logistic Regression"] == 0.6339526050735212, gate
assert gate["XGBoost"] == 0.5915302092371963, gate
assert gate["Random Forest"] == 0.5386608264991757, gate
R["gate_official_reproduced"] = gate

# ------------------------------------------------------- B1 criterion validity
def ct(a, b, order_b):
    t = pd.crosstab(P[a], P[b]).reindex(index=["High", "Medium", "Low"], columns=order_b, fill_value=0)
    return t.to_dict(orient="index")
risk_ord = P.Risk_Level.map(code)
out_ord = P.Outcome.map({"Success": 0, "Delayed": 1, "Failed": 2})
val_ord = P.Validation_Result.map({"Pass": 0, "Partial": 1, "Fail": 2})
med = P.groupby("Risk_Level")[["Cutover_Delay_Days", "Validation_Attempts", "Migration_Duration_Hours"]].median()
iqr = P.groupby("Risk_Level")[["Cutover_Delay_Days", "Validation_Attempts", "Migration_Duration_Hours"]].quantile([.25, .75])
R["B1"] = {
    "risk_x_outcome": ct("Risk_Level", "Outcome", ["Success", "Delayed", "Failed"]),
    "risk_x_validation": ct("Risk_Level", "Validation_Result", ["Pass", "Partial", "Fail"]),
    "kendall_tau_b_risk_outcome": [round(v, 4) for v in stats.kendalltau(risk_ord, out_ord, variant="b")],
    "kendall_tau_b_risk_validation": [round(v, 4) for v in stats.kendalltau(risk_ord, val_ord, variant="b")],
    "medians_by_risk": med.reindex(["Low", "Medium", "High"]).to_dict(orient="index"),
    "iqr_by_risk": {f"{k[0]}|q{k[1]}": v for k, v in iqr.to_dict(orient="index").items()},
    "kendall_tau_b_risk_vs": {c: [round(v, 4) for v in stats.kendalltau(risk_ord, P[c], variant="b")]
                              for c in ["Cutover_Delay_Days", "Validation_Attempts", "Migration_Duration_Hours"]},
}
# what do the pre-execution features predict on the objective outcome vs the label (CV on pool, same protocol)
# (Outcome already reported in the official run: LR 0.395; dummy 0.198)

# ------------------------------------------------------- B2 heuristic baselines
base_specs = {
    "LR: Complexity_Level only": ["Complexity_Level"],
    "LR: Business_Criticality only": ["Business_Criticality"],
    "LR: Complexity + Criticality": ["Complexity_Level", "Business_Criticality"],
    "LR: rule-trigger count scorecard": ["Rule_Score"],
    "LR: Previous_Issues_Count only": ["Previous_Issues_Count"],
}
B2 = {}
fits_hold = {}
def holdout_eval(model_name, feats):
    Xp, yp = pool[feats], pool[C.TARGET_PRIMARY].map(code).astype(int)
    m = make_model(model_name, feats)
    kw = {"clf__sample_weight": compute_sample_weight("balanced", yp)} if needs_sample_weight(model_name) else {}
    m.fit(Xp, yp, **kw)
    yt = hold[C.TARGET_PRIMARY].map(code).astype(int).to_numpy()
    raw = m.predict_proba(hold[feats]); pr = np.zeros((36, 3))
    for j, cc in enumerate(m.classes_): pr[:, int(cc)] = raw[:, j]
    pe = m.predict(hold[feats])
    return m, yt, pe, pr
def hold_metrics(yt, pe, pr):
    yl = [CL[i] for i in yt]; pl = [CL[i] for i in pe]
    return {"f1_macro": round(f1_score(yl, pl, average="macro", zero_division=0), 4),
            "accuracy": round(accuracy_score(yt, pe), 4),
            "balanced_accuracy": round(balanced_accuracy_score(yt, pe), 4),
            "auc": round(roc_auc_score(yt, pr, multi_class="ovr", average="macro", labels=[0, 1, 2]), 4),
            "correct": int((yt == pe).sum())}
for lbl, feats in base_specs.items():
    f, _ = run_cv("Logistic Regression", feats)
    _, yt, pe, pr = holdout_eval("Logistic Regression", feats)
    B2[lbl] = {"cv_f1": ms(f.f1_macro), "cv_auc": ms(f.auc), "cv_acc": ms(f.accuracy),
               "holdout": hold_metrics(yt, pe, pr), "fold_f1": f.f1_macro.tolist()}
lr_f = off["Logistic Regression"][0]
for lbl in base_specs:
    d = lr_f.f1_macro.to_numpy() - np.array(B2[lbl]["fold_f1"])
    B2[lbl]["lr13_minus_baseline"] = {"mean": round(d.mean(), 4), "sd": round(d.std(), 4),
                                      "lr_wins_of_25": int((d > 0).sum()), "ties": int((d == 0).sum())}
    del B2[lbl]["fold_f1"]
# Dev label -> QA label (no fitting); valid only if Dev precedes QA
def devqa(df, g):
    d = df.assign(svc=g.values)
    piv = d.pivot_table(index="svc", columns="Environment", values="Risk_Level", aggfunc="first")
    return piv
for nm, df, g in [("pool_70", pool, gpool), ("holdout_18", hold, ghold), ("all_88", P, G)]:
    piv = devqa(df, g)
    B2[f"QA_label_from_Dev_label_{nm}"] = {
        "agree": int((piv.Dev == piv.QA).sum()), "n_services": int(len(piv)),
        "f1_macro": round(f1_score(piv.QA, piv.Dev, average="macro", zero_division=0), 4),
        "accuracy": round(float((piv.Dev == piv.QA).mean()), 4)}
R["B2"] = B2

# ------------------------------------------------------- B3 paired comparison
def nb_ttest(d, n_tr, n_te):
    J = len(d); var = np.var(d, ddof=1)
    t = d.mean() / np.sqrt((1 / J + n_te / n_tr) * var)
    return float(t), float(2 * stats.t.sf(abs(t), df=J - 1))
B3 = {}
wins = {"XGBoost": 0, "Random Forest": 0}; tot = 0
for base in [42, 7, 100, 2026]:
    fl, _ = (off["Logistic Regression"][0], None) if base == 42 else run_cv("Logistic Regression", C.PRE_EXEC_FEATURES, base)
    row = {}
    for other in ["XGBoost", "Random Forest"]:
        fo = off[other][0] if base == 42 else run_cv(other, C.PRE_EXEC_FEATURES, base)[0]
        d = fl.f1_macro.to_numpy() - fo.f1_macro.to_numpy()
        t, p = nb_ttest(d, fl.n_train.mean(), fl.n_test.mean())
        row[f"LR_minus_{other}"] = {"mean": round(d.mean(), 4), "sd": round(d.std(ddof=1), 4),
                                    "lr_wins_of_25": int((d > 0).sum()),
                                    "nadeau_bengio_t": round(t, 3), "p_two_sided": round(p, 4)}
        wins[other] += int((d > 0).sum())
    tot += 25
    row["LR_mean"] = round(float(fl.f1_macro.mean()), 4)
    B3[f"seed_base_{base}"] = row
B3["lr_wins_over_100_folds"] = {k: f"{v}/{tot}" for k, v in wins.items()}
R["B3"] = B3

# ------------------------------------------------------- B4 holdout uncertainty
m_lr, yt, pe, pr = holdout_eval("Logistic Regression", C.PRE_EXEC_FEATURES)
cm = confusion_matrix(yt, pe, labels=[0, 1, 2]).tolist()
assert cm == [[2, 1, 0], [4, 11, 3], [2, 4, 9]], cm        # locked matrix (Low, Medium, High)
pcls = {CL[i]: {"precision": round(precision_score(yt, pe, labels=[i], average="macro", zero_division=0), 4),
                "recall": round(recall_score(yt, pe, labels=[i], average="macro", zero_division=0), 4),
                "f1": round(f1_score(yt, pe, labels=[i], average="macro", zero_division=0), 4)} for i in range(3)}
svc = ghold.to_numpy(); us = np.unique(svc); rng = np.random.default_rng(20261031)
boot = {"f1_macro": [], "accuracy": [], "balanced_accuracy": [], "auc": []}; auc_skipped = 0
for _ in range(5000):
    pick = rng.choice(us, size=len(us), replace=True)
    idx = np.concatenate([np.where(svc == s)[0] for s in pick])
    a, b, c = yt[idx], pe[idx], pr[idx]
    boot["f1_macro"].append(f1_score([CL[i] for i in a], [CL[i] for i in b], average="macro", zero_division=0))
    boot["accuracy"].append(accuracy_score(a, b))
    boot["balanced_accuracy"].append(balanced_accuracy_score(a, b))
    if len(np.unique(a)) == 3:
        boot["auc"].append(roc_auc_score(a, c, multi_class="ovr", average="macro", labels=[0, 1, 2]))
    else: auc_skipped += 1
R["B4"] = {"holdout_point": hold_metrics(yt, pe, pr), "confusion_LowMedHigh": cm,
           "predicted_counts": {CL[i]: int((pe == i).sum()) for i in range(3)},
           "actual_counts": {CL[i]: int((yt == i).sum()) for i in range(3)},
           "per_class": pcls,
           "two_step_errors": {"High_pred_Low": int(((yt == 2) & (pe == 0)).sum()),
                               "Low_pred_High": int(((yt == 0) & (pe == 2)).sum())},
           "cluster_bootstrap_95CI": {k: [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]
                                      for k, v in boot.items()},
           "bootstrap_draws": 5000, "auc_draws_skipped_missing_class": auc_skipped,
           "one_low_flip": "computed below"}
# sensitivity: one Low record flips
def f1m(a, b): return f1_score([CL[i] for i in a], [CL[i] for i in b], average="macro", zero_division=0)
low_hit = np.where((yt == 0) & (pe == 0))[0]; low_miss = np.where((yt == 0) & (pe != 0))[0]
pe2 = pe.copy(); pe2[low_hit[0]] = 1; pe3 = pe.copy(); pe3[low_miss[0]] = 0
R["B4"]["one_low_flip"] = {"one_fewer_low_hit": round(f1m(yt, pe2), 4), "one_more_low_hit": round(f1m(yt, pe3), 4)}
# within-1-SD check per metric
cvm = {"f1_macro": (0.634, 0.109), "accuracy": (0.709, 0.075), "auc": (0.859, 0.060), "balanced_accuracy": (0.6706, 0.1184)}
hp = R["B4"]["holdout_point"]
R["B4"]["gap_in_cv_sd"] = {k: round((cvm[k][0] - hp[k]) / cvm[k][1], 2) for k in cvm}

# ------------------------------------------------------- B5 rules 2x2 + R7 end-to-end
ra = P.Recommended_Action.fillna("").str.lower()
B5 = {}
others = pd.Series(False, index=P.index)
for rid in ["R1", "R2", "R3", "R4", "R5", "R6"]:
    others = others | trig(rid, P)
masks = {r: trig(r, P) for r in ["R1", "R2", "R3", "R4", "R5", "R6"]}
masks["R7 (recorded High)"] = P.Risk_Level == "High"
masks["R8 (fallback)"] = ~others
ph = dict(PHRASE); ph["R7 (recorded High)"] = PHRASE["R7"]; ph["R8 (fallback)"] = PHRASE["R8"]
for r, m in masks.items():
    an = ra.str.contains(ph[r], regex=False)
    a, b, c, d = int((m & an).sum()), int((m & ~an).sum()), int((~m & an).sum()), int((~m & ~an).sum())
    B5[r] = {"trig&annot": a, "trig&no_annot": b, "no_trig&annot": c, "no_trig&no_annot": d,
             "P(annot|trig)": round(a / (a + b), 3) if a + b else None,
             "P(trig|annot)": round(a / (a + c), 3) if a + c else None}
# R7 end-to-end with classifier predictions
an7_h = hold.Recommended_Action.fillna("").str.lower().str.contains(PHRASE["R7"], regex=False).to_numpy()
pH = pe == 2
B5["R7_end_to_end_holdout"] = {"predicted_High": int(pH.sum()), "predicted_High_with_annot": int((pH & an7_h).sum()),
                               "annotated_total": int(an7_h.sum()), "annotated_and_predicted_High": int((pH & an7_h).sum())}
oof = off["Logistic Regression"][1]
idx = np.array(sorted(oof)); pred_oof = np.array([oof[i][1] for i in idx])
an7_p = pool.Recommended_Action.fillna("").str.lower().str.contains(PHRASE["R7"], regex=False).to_numpy()[idx]
pHo = pred_oof == 2
B5["R7_end_to_end_pool_OOF_seed42"] = {"n": len(idx), "predicted_High": int(pHo.sum()),
    "predicted_High_with_annot": int((pHo & an7_p).sum()), "annotated_total": int(an7_p.sum()),
    "P(annot|predHigh)": round((pHo & an7_p).sum() / pHo.sum(), 3), "P(predHigh|annot)": round((pHo & an7_p).sum() / an7_p.sum(), 3)}
# what the 25 High records without the R7 annotation carried
hi_no = P[(P.Risk_Level == "High") & ~ra.str.contains(PHRASE["R7"], regex=False)]
B5["High_without_R7_annot"] = {"n": int(len(hi_no)),
    "carried": {k: int(hi_no.Recommended_Action.str.lower().str.contains(v, regex=False).sum()) for k, v in PHRASE.items() if k != "R7"}}
R7_nonhigh = P[(P.Risk_Level != "High") & ra.str.contains(PHRASE["R7"], regex=False)]
B5["R7_annot_on_non_High"] = int(len(R7_nonhigh))
B5["recommended_action_format"] = "semicolon-separated list of fixed action phrases (e.g. 'Validate db connectivity; verify firewall/network rules.')"
R["B5"] = B5

# ------------------------------------------------------- B6 descriptives
lf = off["Logistic Regression"][0]
B6 = {"low_test_per_fold": {"min": int(lf.low_in_test.min()), "median": float(lf.low_in_test.median()), "max": int(lf.low_in_test.max())},
      "folds_without_low_in_test": int((lf.low_in_test == 0).sum()),
      "LR_folds_without_low_prediction": int((lf.low_predicted == 0).sum()),
      "auc_folds_valid": int(lf.auc.notna().sum())}
piv = devqa(P, G)
B6["dev_qa_label_agreement"] = f"{int((piv.Dev == piv.QA).sum())}/88"
d = P.assign(svc=G.values)
varies = {}
for f in C.PRE_EXEC_FEATURES:
    if f == "Environment": continue
    pv = d.pivot_table(index="svc", columns="Environment", values=f, aggfunc="first")
    varies[f] = int((pv.Dev.astype(str) != pv.QA.astype(str)).sum())
B6["services_where_feature_differs_Dev_vs_QA"] = varies
B6["class_by_environment"] = pd.crosstab(P.Environment, P.Risk_Level)[["Low", "Medium", "High"]].to_dict(orient="index")
R["B6"] = B6

# ------------------------------------------------------- B7 High-vs-rest + threshold
B7 = {}
for n in ["Logistic Regression", "Random Forest", "XGBoost"]:
    f = off[n][0]
    B7[n] = {"high_precision": ms(f.high_precision), "high_recall": ms(f.high_recall), "high_f1": ms(f.high_f1)}
B7["LR_holdout_High"] = pcls["High"]
yo = np.array([oof[i][0] for i in idx]); po = np.array([oof[i][2] for i in idx])
thr = {}
for t in [0.30, 0.35, 0.40, 0.45, 0.50]:
    flag = po[:, 2] >= t
    thr[str(t)] = {"high_recall": round(float((flag & (yo == 2)).sum() / (yo == 2).sum()), 3),
                   "high_precision": round(float((flag & (yo == 2)).sum() / max(flag.sum(), 1)), 3),
                   "flagged": int(flag.sum())}
B7["LR_OOF_seed42_threshold_on_P(High)"] = thr
B7["LR_OOF_brier_High_vs_rest"] = round(brier_score_loss((yo == 2).astype(int), po[:, 2]), 4)
R["B7"] = B7

# ------------------------------------------------------- B8 coefficients
pre = m_lr.named_steps["prep"]; clf = m_lr.named_steps["clf"]
names = list(pre.get_feature_names_out())
coef = pd.DataFrame(clf.coef_, index=[CL[int(c)] for c in clf.classes_], columns=names).T.round(3)
R["B8_LR_coefficients_pool140"] = coef.to_dict(orient="index")
R["B8_note"] = "standardized numeric inputs; one-hot nominal; Business_Criticality ordinal (0,1,2) not scaled"

# ------------------------------------------------------- B9 ordinal measures
B9 = {n: {"qwk": ms(off[n][0].qwk), "mean_abs_class_distance": ms(off[n][0].mad)} for n in off}
B9["LR_holdout"] = {"qwk": round(cohen_kappa_score(yt, pe, labels=[0, 1, 2], weights="quadratic"), 4),
                    "mean_abs_class_distance": round(float(np.mean(np.abs(yt - pe))), 4)}
R["B9"] = B9

(OUT / "main_analyses.json").write_text(json.dumps(R, indent=1, default=float))

# ------------------------------------------------------- figure mock: class by environment
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "serif", "font.serif": ["Liberation Serif", "DejaVu Serif"], "font.size": 11})
cbe = pd.crosstab(P.Environment, P.Risk_Level)[["High", "Medium", "Low"]]
fig, ax = plt.subplots(figsize=(5.6, 3.6), dpi=600)
cols = {"High": "#C8443F", "Medium": "#C8861F", "Low": "#3A9A6C"}
x = np.arange(2); w = 0.26
for k, cls in enumerate(["High", "Medium", "Low"]):
    vals = cbe[cls].reindex(["Dev", "QA"]).to_numpy()
    bars = ax.bar(x + (k - 1) * w, vals, w, label=cls, color=cols[cls])
    for bx, v in zip(bars, vals): ax.text(bx.get_x() + bx.get_width() / 2, v + 0.8, str(v), ha="center", fontsize=9)
ax.set_xticks(x, ["Development (Dev)", "Quality Assurance (QA)"]); ax.set_ylabel("Records")
ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))
fig.savefig(OUT / "figs" / "fig1_class_by_environment_MOCK.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
print(json.dumps({k: R[k] for k in ["gate_official_reproduced"]}, indent=1))
print("DONE")
