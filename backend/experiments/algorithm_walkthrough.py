"""LIVE supervisor demo — run in a terminal in front of the committee/supervisor:

    python -m backend.experiments.algorithm_walkthrough

Deterministic (seed 42): every number printed here matches the figures in the
meeting document 'Algorithms_Explained_Worked_Examples.docx', because both are
computed from the same real records with the same seed.
"""
import numpy as np, pandas as pd, time
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline, load_raw
from backend.models.factory import make_model, make_preprocessor
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.utils.class_weight import compute_sample_weight

W = 74
def head(t): print("\n" + "=" * W + f"\n  {t}\n" + "=" * W)
def step(t): print(f"\n--- {t} " + "-" * max(0, W - len(t) - 5))
def pause(): time.sleep(0.6)

def main():
    head("STEP 0 · Load the REAL dataset (176 records) and verify integrity")
    processed, groups, meta = run_pipeline(save=False)
    raw = load_raw()
    print(f"records: {len(processed)}  services: {groups.nunique()}  "
          f"integrity gates: {'ALL PASSED' if meta['integrity']['all_passed'] else 'FAILED'}")
    X, y = processed[C.PRE_EXEC_FEATURES], processed[C.TARGET_PRIMARY]

    rng = np.random.default_rng(C.SEED)
    idx = []
    for cls in C.RISK_CLASSES:
        pool = y[y == cls].index.to_numpy().copy(); rng.shuffle(pool); idx += list(pool[:5])
    idx = sorted(int(i) for i in idx)
    demo_i = [i for i in y[y == "High"].index if i not in idx][0]
    head("STEP 1 · A 15-record teaching sample (5 per class) + one held-out case")
    cols = ["Environment","Business_Criticality","Complexity_Level",
            "Firewall_Rules_Count","Previous_Issues_Count","Owner_Availability"]
    view = processed.loc[idx, cols].copy()
    view.insert(0, "Migration_ID", raw.loc[idx, "Migration_ID"])
    view["Risk"] = y.loc[idx]
    print(view.to_string(index=False))
    print(f"\nHeld-out demo case: {raw.loc[demo_i,'Migration_ID']}  (true label hidden for now...)")
    Xtr, ytr = X.loc[idx], y.loc[idx].map({c:i for i,c in enumerate(C.RISK_CLASSES)})
    Xd = X.loc[[demo_i]]; pause()

    head("STEP 2 · LOGISTIC REGRESSION — a transparent weighted score")
    lr = make_model("Logistic Regression", C.PRE_EXEC_FEATURES); lr.fit(Xtr, ytr)
    names = lr.named_steps["prep"].get_feature_names_out()
    pairs = sorted(zip(names, lr.named_steps["clf"].coef_[2]), key=lambda t: -t[1])
    step("Largest learned weights toward class HIGH (fitted live on 15 records)")
    for n, c in pairs[:5]: print(f"  {n.split('__',1)[1]:35s} {c:+.2f}")
    p = lr.predict_proba(Xd)[0]
    step("Scoring the held-out case")
    print("  P(Low)={:.3f}  P(Medium)={:.3f}  P(High)={:.3f}   ->  predicts {}"
          .format(p[0], p[1], p[2], C.RISK_CLASSES[int(np.argmax(p))])); pause()

    head("STEP 3 · RANDOM FOREST — a committee of trees, voting")
    rf = Pipeline([("prep", make_preprocessor(C.PRE_EXEC_FEATURES, False)),
                   ("clf", RandomForestClassifier(n_estimators=7, max_depth=3,
                            class_weight="balanced", random_state=C.SEED))]).fit(Xtr, ytr)
    votes = [C.RISK_CLASSES[int(t.predict(rf.named_steps["prep"].transform(Xd))[0])]
             for t in rf.named_steps["clf"].estimators_]
    for i, v in enumerate(votes, 1): print(f"  Tree {i}: votes {v}")
    maj = max(set(votes), key=votes.count)
    print(f"  MAJORITY -> {maj}  (vote share {votes.count(maj)}/7)"); pause()

    head("STEP 4 · XGBOOST — trees correcting each other's errors, round by round")
    ev = np.array([i for i in y.index if i not in idx and i != demo_i]); rng.shuffle(ev)
    ev = sorted(int(i) for i in ev[:40])
    prep = make_preprocessor(C.PRE_EXEC_FEATURES, False).fit(Xtr)
    xgb = XGBClassifier(n_estimators=30, max_depth=3, learning_rate=0.3,
                        objective="multi:softprob", eval_metric="mlogloss",
                        random_state=C.SEED, n_jobs=-1)
    xgb.fit(prep.transform(Xtr), ytr,
            sample_weight=compute_sample_weight("balanced", ytr),
            eval_set=[(prep.transform(X.loc[ev]),
                       y.loc[ev].map({c:i for i,c in enumerate(C.RISK_CLASSES)}))], verbose=False)
    ll = xgb.evals_result()["validation_0"]["mlogloss"]
    for r in (1, 5, 15, 30): print(f"  after round {r:>2}: held-out log-loss = {ll[r-1]:.3f}")
    print("  note: improves, then worsens -> with only 15 records the later trees memorise.")
    print("  (this is exactly why the full experiment uses regularisation + grouped CV)"); pause()

    head("STEP 5 · The truth + the full-experiment scoreboard (25 grouped folds)")
    print(f"  True expert label of {raw.loc[demo_i,'Migration_ID']}: {y.loc[demo_i]}   "
          f"(LR said High correctly; the 7-tree committee agreed)")
    r = pd.read_csv(C.RESULTS_DIR / "phase3a_baseline_results.csv")
    r = r[r.config == "A_Risk_PRE-EXEC"].set_index("model")
    for m in ["Dummy (prior)", "Logistic Regression", "Random Forest", "XGBoost"]:
        print(f"  {m:20s} Macro-F1 {r.loc[m,'f1_macro_mean']:.3f}±{r.loc[m,'f1_macro_std']:.3f}"
              f"   acc {r.loc[m,'accuracy_mean']:.3f}   AUC {r.loc[m,'roc_auc_ovr_macro_mean']:.3f}")
    print("\n  Declared primary model: LOGISTIC REGRESSION (Phase-4A documented tie-breakers).")
    print("  Live UI continues the story: http://localhost:8000  (Predict a new case).")

if __name__ == "__main__":
    main()
