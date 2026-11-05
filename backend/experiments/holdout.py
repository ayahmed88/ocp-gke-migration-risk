"""Reserved grouped holdout — single post-selection evaluation (Phase 5).

GroupShuffleSplit 80/20 (seed 42) by Service_Code: the winner (Logistic
Regression, defaults) is trained on ~80% of services and evaluated EXACTLY
ONCE on the reserved 20% (18 services, 36 records) — no fold averaging, one
confusion matrix for the committee. Deterministic and reproducible.
"""
import json, datetime
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                             recall_score, roc_auc_score, confusion_matrix)
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.models.factory import make_model

OUT = C.RESULTS_DIR / "holdout_report.json"
FIG = C.ROOT / "data" / "exports" / "fig_confusion_holdout.png"


def run(force: bool = False) -> dict:
    if OUT.exists() and not force:
        return json.loads(OUT.read_text())
    processed, groups, _ = run_pipeline(save=False)
    X = processed[C.PRE_EXEC_FEATURES]
    y = processed[C.TARGET_PRIMARY].map({c: i for i, c in enumerate(C.RISK_CLASSES)}).astype(int)
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.2,
                                    random_state=C.SEED).split(X, y, groups))
    m = make_model("Logistic Regression", C.PRE_EXEC_FEATURES)
    m.fit(X.iloc[tr], y.iloc[tr])
    proba = m.predict_proba(X.iloc[te]); pred = m.predict(X.iloc[te])
    yt = y.iloc[te]
    cm = confusion_matrix(yt, pred, labels=[0, 1, 2]).tolist()
    try:
        auc = float(roc_auc_score(yt, proba, multi_class="ovr", average="macro",
                                  labels=[0, 1, 2]))
    except ValueError:
        auc = None
    rep = {
        "locked": True, "seed": C.SEED, "model": "Logistic Regression (declared winner, defaults)",
        "split": "GroupShuffleSplit 80/20 by Service_Code — evaluated once",
        "train_rows": int(len(tr)), "test_rows": int(len(te)),
        "train_services": int(groups.iloc[tr].nunique()),
        "test_services": int(groups.iloc[te].nunique()),
        "test_class_counts": {C.RISK_CLASSES[k]: int(v) for k, v in
                              zip(*np.unique(yt, return_counts=True))},
        "metrics": {
            "macro_f1": round(float(f1_score(yt, pred, average="macro", zero_division=0)), 3),
            "accuracy": round(float(accuracy_score(yt, pred)), 3),
            "balanced_accuracy": round(float(balanced_accuracy_score(yt, pred)), 3),
            "auc_ovr_macro": round(auc, 3) if auc is not None else None,
            "recall_per_class": {c: round(float(recall_score(yt, pred, labels=[i],
                                 average="macro", zero_division=0)), 3)
                                 for i, c in enumerate(C.RISK_CLASSES)},
        },
        "confusion": {"labels": C.RISK_CLASSES, "matrix": cm},
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": "Single evaluation on the reserved holdout; the headline result remains the 25-fold grouped CV. The holdout services took part in an exploratory full-data round before the protocol was fixed (paper, Section 3.4): a post-selection check, not an independent confirmation.",
    }
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1))
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(3.9, 3.4))
    arr = np.array(cm); im = ax.imshow(arr, cmap="Blues")
    ax.set_xticks(range(3), C.RISK_CLASSES); ax.set_yticks(range(3), C.RISK_CLASSES)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title(f"Reserved grouped holdout ({len(te)} records, post-selection check)")
    for i in range(3):
        for jx in range(3):
            ax.text(jx, i, arr[i, jx], ha="center", va="center", fontweight="bold",
                    color="white" if arr[i, jx] > arr.max()/2 else "#1B2733")
    fig.colorbar(im, shrink=.8); fig.savefig(FIG, dpi=300, bbox_inches="tight"); plt.close(fig)
    return rep
