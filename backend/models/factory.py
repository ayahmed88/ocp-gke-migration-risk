"""Model + preprocessing factory.

All encoding/scaling lives INSIDE sklearn Pipelines so it is fitted on the
training fold only (no statistical leakage across CV folds) — decision F5.
Class imbalance is handled with balanced class weights (decision F4):
LR / RF via class_weight='balanced'; XGBoost via balanced sample_weight
passed at fit time (computed on the training fold only).
"""
from __future__ import annotations
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from xgboost import XGBClassifier

from backend.core import config as C

MODEL_ORDER = ["Dummy (prior)", "Logistic Regression", "Random Forest", "XGBoost"]


def _split_cols(features: list[str]):
    nominal = [c for c in features if c in C.NOMINAL_COLS]
    ordinal = [c for c in features if c in C.ORDINAL_MAPS]
    numeric = [c for c in features if c not in nominal and c not in ordinal]
    return nominal, ordinal, numeric


def make_preprocessor(features: list[str], scale_numeric: bool) -> ColumnTransformer:
    nominal, ordinal, numeric = _split_cols(features)
    transformers = [
        ("nom", OneHotEncoder(handle_unknown="ignore"), nominal),
        ("ord", OrdinalEncoder(categories=[C.ORDINAL_MAPS[c] for c in ordinal]), ordinal),
        ("num", StandardScaler() if scale_numeric else "passthrough", numeric),
    ]
    return ColumnTransformer(transformers, verbose_feature_names_out=True)


def make_model(name: str, features: list[str]) -> Pipeline:
    if name == "Dummy (prior)":
        est, scale = DummyClassifier(strategy="prior"), False
    elif name == "Logistic Regression":
        est, scale = LogisticRegression(max_iter=5000, class_weight="balanced",
                                        random_state=C.SEED), True
    elif name == "Random Forest":
        est, scale = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                            random_state=C.SEED, n_jobs=-1), False
    elif name == "XGBoost":
        est, scale = XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.1,
            subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
            objective="multi:softprob", eval_metric="mlogloss",
            random_state=C.SEED, n_jobs=-1), False
    else:
        raise ValueError(name)
    return Pipeline([("prep", make_preprocessor(features, scale)), ("clf", est)])


def needs_sample_weight(name: str) -> bool:
    """XGBClassifier has no class_weight — balanced sample_weight at fit time (F4)."""
    return name == "XGBoost"
