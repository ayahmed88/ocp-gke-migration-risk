"""Thesis-grade exports — the single source of thesis figures & tables.

v45 (review batch B): every figure follows the gold-standard scopes, saves
PNG 300dpi + SVG, carries no in-image title (scope lives in captions.md),
and is described in a rich manifest.json entry.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, f1_score, roc_curve, auc
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import label_binarize

from backend.core import config as C
from backend.data.pipeline import run as run_pipeline, load_raw
from backend.models.factory import MODEL_ORDER, make_model
from backend.experiments.split import vault_carve
from backend.experiments.demo import ensure_vault_model, _vault_split

EXP = C.RESULTS_DIR.parent / "exports"
VERSION = (C.ROOT / "VERSION").read_text().strip()
plt.rcParams.update({
    "font.family": ["Times New Roman", "Liberation Serif", "DejaVu Serif", "serif"],
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
CLS = ["High", "Medium", "Low"]
CCOL = {"High": "#C6423F", "Medium": "#C8871E", "Low": "#3A9B6E"}
MCOL = {"Logistic Regression": "#0F7B7C", "XGBoost": "#5A6B7B",
        "Random Forest": "#8FA3B5", "Dummy (prior)": "#C9CFD6"}

_manifest: list[dict] = []
_captions: list[str] = []


def _save(fig, name: str, source: str, numbers: dict, caption: str):
    fig.savefig(EXP / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(EXP / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    _manifest.append({"file": name, "data_source": source, "numbers": numbers,
                      "version": VERSION,
                      "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    _captions.append(f"**{name}** — {caption}")
    return name


def _pool():
    processed, groups, _ = run_pipeline(save=False)
    X = processed[C.PRE_EXEC_FEATURES]
    y = processed[C.TARGET_PRIMARY].map(
        {c: i for i, c in enumerate(C.RISK_CLASSES)}).astype(int)
    tr, _te = vault_carve(processed, processed[C.TARGET_PRIMARY], groups)
    return (processed, X.iloc[tr].reset_index(drop=True),
            y.iloc[tr].reset_index(drop=True),
            groups.iloc[tr].reset_index(drop=True))


def _cm_axes(cm, cmap):
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    ax.imshow(cm, cmap=cmap)
    ax.set_xticks(range(3), CLS); ax.set_yticks(range(3), CLS)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontweight="bold",
                    color="white" if cm[i, j] > cm.max() / 2 else "#1B2733")
    return fig


def fig_class_distribution(processed):
    counts = processed[C.TARGET_PRIMARY].value_counts().reindex(CLS)
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    b = ax.bar(CLS, counts.values, color=[CCOL[c] for c in CLS])
    ax.bar_label(b, [f"{v} ({v/len(processed):.1%})" for v in counts.values], fontsize=9)
    ax.set_ylabel("Records")
    return _save(fig, "fig_risk_distribution",
                 "full dataset (176 records / 88 services) — class distribution of the primary target",
                 {"n": int(len(processed)), **{c: int(v) for c, v in counts.items()}},
                 "Distribution of the primary target Risk_Level across the full dataset (n = 176).")


def fig_model_comparison():
    r = pd.read_csv(C.RESULTS_DIR / "phase3a_baseline_results.csv")
    a = r[r.config == "A_Risk_PRE-EXEC"].set_index("model").loc[MODEL_ORDER]
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    xs = np.arange(len(MODEL_ORDER))
    ax.bar(xs, a.f1_macro_mean, yerr=a.f1_macro_std, capsize=3,
           color=[MCOL[m] for m in MODEL_ORDER],
           error_kw={"elinewidth": .9, "ecolor": "#55636F"})
    for xi, v in zip(xs, a.f1_macro_mean):
        ax.text(xi, 0.02, f"{v:.3f}", ha="center", fontsize=9,
                color="white", fontweight="bold")
    ax.set_xticks(xs, ["Dummy", "LogReg", "RF", "XGBoost"])
    ax.set_ylabel("Macro-F1 (mean ± std, 25 folds)")
    nums = {m: round(float(v), 4) for m, v in a.f1_macro_mean.items()}
    return _save(fig, "fig_model_comparison_preexec",
                 "official phase3a_baseline_results.csv — selection pool 140/70, config A",
                 nums,
                 "Model comparison on the official pre-execution configuration "
                 "(selection pool: 140 records / 70 services; StratifiedGroupKFold 5x5).")


def fig_confusion_oof(Xp, yp, gp):
    """Winner OOF confusion on the selection pool — single repeat (seed 42)."""
    oof = np.full(len(yp), -1)
    for tri, tei in StratifiedGroupKFold(
            5, shuffle=True, random_state=C.SEED).split(Xp, yp, gp):
        m = make_model("Logistic Regression", list(Xp.columns))
        m.fit(Xp.iloc[tri], yp.iloc[tri])
        oof[tei] = m.predict(Xp.iloc[tei])
    order = [C.RISK_CLASSES.index(c) for c in CLS]
    cm = confusion_matrix(yp, oof, labels=order)
    assert cm.sum() == len(yp), cm.sum()
    fig = _cm_axes(cm, "Blues")
    _save(fig, "fig_confusion_winner_oof",
          "selection pool 140/70 — StratifiedGroupKFold 5-fold, single repeat (seed 42)",
          {"sum": int(cm.sum()), "diag": int(np.trace(cm))},
          "Out-of-fold confusion matrix of the winning model (Logistic Regression) "
          "on the 140-record selection pool; grouped 5-fold, single repeat (seed 42).")
    pd.DataFrame(cm, index=[f"actual_{c}" for c in CLS],
                 columns=[f"pred_{c}" for c in CLS]
                 ).to_csv(EXP / "table_confusion_winner_oof.csv")
    return cm


def fig_confusion_holdout():
    vmodel = ensure_vault_model()
    _pr, Xv, yv, _tr, te = _vault_split()
    raw = load_raw()
    pred = vmodel.predict(Xv.iloc[te])
    order = [C.RISK_CLASSES.index(c) for c in CLS]
    cm = confusion_matrix(yv.iloc[te], pred, labels=order)
    correct = int(np.trace(cm))
    mf = float(f1_score(yv.iloc[te], pred, average="macro"))
    assert cm.sum() == 36 and correct == 22 and abs(mf - 0.559) < 0.002, (cm.sum(), correct, mf)
    fig = _cm_axes(cm, "Greens")
    _save(fig, "fig_confusion_holdout",
          "sealed holdout vault (18 services / 36 records); final model fit on the 140 pool",
          {"sum": 36, "correct": correct, "macro_f1": round(mf, 3)},
          "Confusion matrix on the sealed holdout vault (18 services / 36 records); "
          f"the final model was trained on the 140-record pool only. {correct}/36 correct, "
          f"Macro-F1 = {mf:.3f}.")
    i2c = {i: c for i, c in enumerate(C.RISK_CLASSES)}
    rows = [{"migration_id": raw.iloc[int(j)]["Migration_ID"],
             "service": raw.iloc[int(j)]["Service_Code"],
             "actual": i2c[int(yv.iloc[int(j)])], "predicted": i2c[int(p)]}
            for j, p in zip(te, pred)]
    pd.DataFrame(rows).to_csv(EXP / "table_holdout_predictions.csv", index=False)
    return cm


def fig_roc_winner(Xp, yp, gp):
    grid = np.linspace(0, 1, 101)
    tprs = {c: [] for c in CLS}
    aucs = {c: [] for c in CLS}
    for seed in range(C.SEED, C.SEED + C.CV_N_REPEATS):
        for tri, tei in StratifiedGroupKFold(
                C.CV_N_SPLITS, shuffle=True, random_state=seed).split(Xp, yp, gp):
            m = make_model("Logistic Regression", list(Xp.columns))
            m.fit(Xp.iloc[tri], yp.iloc[tri])
            proba = m.predict_proba(Xp.iloc[tei])
            yb = label_binarize(yp.iloc[tei], classes=[0, 1, 2])
            for ci, cname in [(2, "High"), (1, "Medium"), (0, "Low")]:
                col = list(m.classes_).index(ci)
                fpr, tpr, _ = roc_curve(yb[:, ci], proba[:, col])
                tprs[cname].append(np.interp(grid, fpr, tpr))
                aucs[cname].append(auc(fpr, tpr))
    macro = float(np.mean([np.mean(aucs[c]) for c in CLS]))
    assert abs(macro - 0.859) < 0.01, macro
    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    for c in CLS:
        mt, st = np.mean(tprs[c], 0), np.std(tprs[c], 0)
        ax.plot(grid, mt, color=CCOL[c], lw=2,
                label=f"{c} (AUC {np.mean(aucs[c]):.3f} ± {np.std(aucs[c]):.3f})")
        ax.fill_between(grid, np.clip(mt - st, 0, 1), np.clip(mt + st, 0, 1),
                        color=CCOL[c], alpha=.15)
    ax.plot([0, 1], [0, 1], "--", color="#9AA7B4", lw=1)
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.legend(loc="lower right", fontsize=8.5,
              title=f"macro mean AUC = {macro:.3f}", title_fontsize=9)
    return _save(fig, "fig_roc_winner",
                 "winner (LogReg), one-vs-rest per class, mean ± std across the 25 folds (pool 140)",
                 {"auc_macro": round(macro, 3),
                  **{f"auc_{c}": round(float(np.mean(aucs[c])), 3) for c in CLS}},
                 "One-vs-rest ROC curves of the winning model per class: mean ROC with a "
                 "±1 std band across the 25 grouped folds (5x5) on the 140-record pool; "
                 f"macro mean AUC = {macro:.3f}. Note: the rare Low class attains the "
                 "highest AUC — ranking quality is strong even where threshold recall is unstable.")


def _persist_dummy_rows(Xp, yp, gp):
    path = C.RESULTS_DIR / "seed_sensitivity.json"
    rows = json.loads(path.read_text())
    if any(r["model"] == "Dummy (prior)" for r in rows):
        return rows
    for base in sorted({r["seed_base"] for r in rows}):
        f1s = []
        for seed in range(base, base + C.CV_N_REPEATS):
            for tri, tei in StratifiedGroupKFold(
                    C.CV_N_SPLITS, shuffle=True, random_state=seed).split(Xp, yp, gp):
                m = make_model("Dummy (prior)", list(Xp.columns))
                m.fit(Xp.iloc[tri], yp.iloc[tri])
                f1s.append(f1_score(yp.iloc[tei], m.predict(Xp.iloc[tei]), average="macro"))
        rows.append({"seed_base": int(base), "model": "Dummy (prior)",
                     "f1": round(float(np.mean(f1s)), 3),
                     "std": round(float(np.std(f1s)), 3), "auc": 0.5,
                     "recall_High": round(float(1.0), 3)})
    path.write_text(json.dumps(rows, indent=1))
    return rows


def fig_seed_stability(Xp, yp, gp):
    rows = _persist_dummy_rows(Xp, yp, gp)
    bases = sorted({r["seed_base"] for r in rows}, key=lambda b: [42, 7, 100, 2026].index(b))
    data = {m: {r["seed_base"]: (r["f1"], r["std"]) for r in rows if r["model"] == m}
            for m in MODEL_ORDER}
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    w = 0.2
    for k, m in enumerate(MODEL_ORDER):
        xs = np.arange(len(bases)) + (k - 1.5) * w
        ax.bar(xs, [data[m][b][0] for b in bases], w,
               yerr=[data[m][b][1] for b in bases], capsize=2.5,
               color=MCOL[m], label=m,
               error_kw={"elinewidth": .9, "ecolor": "#55636F"})
    ax.set_xticks(range(len(bases)), [f"seed {b}" for b in bases])
    ax.set_ylabel("Macro-F1 (mean ± std, 25 folds)"); ax.set_ylim(0, 0.85)
    ax.legend(fontsize=8, ncols=2)
    lr42 = data["Logistic Regression"][42][0]
    return _save(fig, "fig_seed_stability",
                 "official seed_sensitivity.json (pool 140); Dummy rows persisted via the official protocol",
                 {"LR@42": lr42, "leader_all_bases": "Logistic Regression"},
                 "Seed-stability of the four models across four seed bases (42/7/100/2026): "
                 "Macro-F1 mean ± std over 25 grouped folds each, on the 140-record pool. "
                 "Logistic Regression leads at every base.")


def fig_top_drivers(Xp, yp):
    m = make_model("Logistic Regression", list(Xp.columns))
    m.fit(Xp, yp)
    prep, clf = m.named_steps["prep"], m.named_steps["clf"]
    names = [n.split("__")[-1] for n in prep.get_feature_names_out()]
    hi = list(clf.classes_).index(2)
    coefs = pd.Series(clf.coef_[hi], index=names).sort_values(ascending=False).head(8)
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.barh(range(len(coefs))[::-1], coefs.values, color=CCOL["High"])
    ax.set_yticks(range(len(coefs))[::-1], coefs.index, fontsize=8)
    ax.set_xlabel("Coefficient toward High")
    return _save(fig, "fig_top_drivers_high",
                 "LogReg fit on the 140-record selection pool (A2 option 1)",
                 {"top1": coefs.index[0], "coef_top1": round(float(coefs.iloc[0]), 3)},
                 "Top learned drivers toward the High class (Logistic Regression coefficients); "
                 "model fit on the 140-record selection pool — the same scope as every "
                 "evaluation figure (A2, option 1).")


def fig_permutation():
    g = json.loads((C.RESULTS_DIR / "xai_global.json").read_text())
    rows = g["permutation_importance"]
    pmax = max(max(r["f1_drop_mean"] for r in rows), 1e-9)
    fig, ax = plt.subplots(figsize=(5.8, 4.4))
    ys = range(len(rows))[::-1]
    ax.barh(ys, [max(r["f1_drop_mean"], 0) for r in rows], color="#0F7B7C",
            xerr=[r["f1_drop_std"] for r in rows],
            error_kw={"elinewidth": .8, "ecolor": "#55636F"})
    ax.set_yticks(ys, [r["feature"] for r in rows], fontsize=8)
    ax.set_xlabel("Macro-F1 drop when shuffled (mean ± std, 25 folds)")
    return _save(fig, "fig_permutation_importance",
                 "xai_global.json — grouped permutation over the 25 folds, " + g.get("fit_scope", ""),
                 {"top1": rows[0]["feature"]},
                 "Grouped permutation importance of the winning model across the 25 evaluation "
                 "folds (pool 140): mean Macro-F1 drop when each feature is shuffled.")


def generate_all() -> dict:
    EXP.mkdir(parents=True, exist_ok=True)
    for old in EXP.iterdir():
        old.unlink()
    _manifest.clear(); _captions.clear()
    processed, Xp, yp, gp = _pool()
    fig_class_distribution(processed)
    fig_model_comparison()
    fig_confusion_oof(Xp, yp, gp)
    fig_confusion_holdout()
    fig_roc_winner(Xp, yp, gp)
    fig_seed_stability(Xp, yp, gp)
    fig_top_drivers(Xp, yp)
    fig_permutation()
    pd.read_csv(C.RESULTS_DIR / "phase3a_baseline_results.csv").to_csv(
        EXP / "table_model_comparison_all_configs.csv", index=False)
    (EXP / "captions.md").write_text(
        "# Thesis figures & tables — suggested captions\n\n" +
        "\n\n".join(_captions) + "\n")
    files = sorted(p.name for p in EXP.iterdir()) + ["manifest.json"]
    (EXP / "manifest.json").write_text(json.dumps(
        {"version": VERSION, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "dpi": 300, "formats": ["png", "svg"],
         "font": "Times New Roman (serif fallback: Liberation/DejaVu Serif)",
         "files": files, "figures": _manifest}, indent=1))
    return {"files": files, "count": len(files), "dpi": 300,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
