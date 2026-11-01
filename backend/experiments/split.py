"""Single source of truth for the vault carve (decision B, v34).

The 20% service-level holdout is carved deterministically BEFORE any model
comparison; all selection experiments run on the remaining 80% only.
"""
from __future__ import annotations
from sklearn.model_selection import GroupShuffleSplit

from backend.core import config as C


def vault_carve(X, y, groups):
    """Return (train_idx, vault_idx) — deterministic from the declared seed."""
    return next(GroupShuffleSplit(n_splits=1, test_size=0.2,
                                  random_state=C.SEED).split(X, y, groups))
