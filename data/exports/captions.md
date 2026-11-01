# Thesis figures & tables — suggested captions

**fig_risk_distribution** — Distribution of the primary target Risk_Level across the full dataset (n = 176).

**fig_model_comparison_preexec** — Model comparison on the official pre-execution configuration (selection pool: 140 records / 70 services; StratifiedGroupKFold 5x5).

**fig_confusion_winner_oof** — Out-of-fold confusion matrix of the winning model (Logistic Regression) on the 140-record selection pool; grouped 5-fold, single repeat (seed 42).

**fig_confusion_holdout** — Confusion matrix on the sealed holdout vault (18 services / 36 records); the final model was trained on the 140-record pool only. 22/36 correct, Macro-F1 = 0.559.

**fig_roc_winner** — One-vs-rest ROC curves of the winning model per class: mean ROC with a ±1 std band across the 25 grouped folds (5x5) on the 140-record pool; macro mean AUC = 0.859. Note: the rare Low class attains the highest AUC — ranking quality is strong even where threshold recall is unstable.

**fig_seed_stability** — Seed-stability of the four models across four seed bases (42/7/100/2026): Macro-F1 mean ± std over 25 grouped folds each, on the 140-record pool. Logistic Regression leads at every base.

**fig_top_drivers_high** — Top learned drivers toward the High class (Logistic Regression coefficients); model fit on the 140-record selection pool — the same scope as every evaluation figure (A2, option 1).

**fig_permutation_importance** — Grouped permutation importance of the winning model across the 25 evaluation folds (pool 140): mean Macro-F1 drop when each feature is shuffled.
