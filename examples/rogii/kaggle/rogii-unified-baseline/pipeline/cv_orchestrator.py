"""CV scheme selection and fold index emission."""

from __future__ import annotations

from typing import Any, Iterator

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, KFold

from pipeline import well_group_detector as wgd


def choose_cv_scheme(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame | None = None,
    *,
    id_column: str = "id",
) -> str:
    key = wgd.recommend_group_key(train_df, test_df, id_column=id_column)
    if key is None:
        return "kfold"
    groups = wgd.provide_groups(train_df, key, id_column=id_column)
    if wgd.count_unique_groups(groups) >= 2:
        return "groupkfold"
    return "kfold"


def emit_fold_indices(
    scheme: str,
    X: pd.DataFrame,
    *,
    n_splits: int = 5,
    groups: np.ndarray | None = None,
    shuffle: bool = True,
    random_state: int = 42,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    n = len(X)
    if scheme == "groupkfold" and groups is not None:
        n_groups = wgd.count_unique_groups(groups)
        n_eff = min(n_splits, n_groups)
        if n_eff >= 2:
            splitter = GroupKFold(n_splits=n_eff)
            yield from splitter.split(X, groups=groups)
            return
    n_eff = min(n_splits, max(2, n // 2))
    splitter = KFold(n_splits=n_eff, shuffle=shuffle, random_state=random_state)
    yield from splitter.split(X)


def subdivide_train_by_well(train_df: pd.DataFrame, group_key: str, *, id_column: str = "id") -> dict:
    groups = wgd.provide_groups(train_df, group_key, id_column=id_column)
    wells = sorted(set(map(str, groups)))
    return {"wells": wells, "n_wells": len(wells)}


def subdivide_train_by_depth_bin(train_df: pd.DataFrame, *, depth_col: str = "MD", q: int = 5) -> dict:
    if depth_col not in train_df.columns:
        return {"bins": [], "note": f"column {depth_col!r} missing"}
    bins = pd.qcut(train_df[depth_col], q=q, labels=False, duplicates="drop")
    return {"n_bins": int(bins.nunique()), "depth_col": depth_col}


def nested_groupkfold_emit_fold_indices(
    X: pd.DataFrame,
    *,
    groups: np.ndarray,
    n_splits: int = 5,
) -> list[dict[str, list[int]]]:
    folds: list[dict[str, list[int]]] = []
    for tr, va in emit_fold_indices("groupkfold", X, n_splits=n_splits, groups=groups):
        folds.append({"train_idx": tr.tolist(), "val_idx": va.tolist()})
    return folds
