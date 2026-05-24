"""Well / group detection for leak-safe GroupKFold."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

_WELL_HINTS = ("well", "hole", "pad", "well_id", "wellid", "api")


def scan_for_well_columns(df: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for c in df.columns:
        cl = str(c).lower()
        if any(h in cl for h in _WELL_HINTS):
            out.append(c)
    return out


def recommend_group_key(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame | None = None,
    *,
    id_column: str = "id",
) -> str | None:
    frames: list[pd.DataFrame] = [train_df]
    if test_df is not None:
        frames.append(test_df)
    for df in frames:
        for c in scan_for_well_columns(df):
            if df[c].nunique(dropna=False) >= 1:
                return c
    if id_column in train_df.columns:
        sample = train_df[id_column].astype(str).head(100)
        if sample.str.contains("_").any():
            return f"__derived_well_from_{id_column}"
    return None


def provide_groups(df: pd.DataFrame, group_key: str, *, id_column: str = "id") -> np.ndarray:
    if group_key.startswith("__derived_well_from_"):
        col = group_key.replace("__derived_well_from_", "", 1)
        if col not in df.columns:
            raise ValueError(f"derived group column {col!r} missing")
        return df[col].astype(str).str.split("_").str[0].values
    if group_key not in df.columns:
        raise ValueError(f"group_key {group_key!r} not in dataframe")
    return df[group_key].astype(str).values


def count_unique_groups(groups: np.ndarray) -> int:
    return int(pd.Series(groups).nunique(dropna=False))


def check_train_test_overlap(
    train_groups: np.ndarray,
    test_groups: np.ndarray,
) -> dict[str, Any]:
    tr = set(map(str, train_groups))
    te = set(map(str, test_groups))
    overlap = tr & te
    return {"n_train_groups": len(tr), "n_test_groups": len(te), "overlap_count": len(overlap)}
