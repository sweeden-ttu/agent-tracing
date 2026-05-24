"""Preprocessor helpers for Rogii baseline (Pedregosa ColumnTransformer path)."""

from __future__ import annotations

from typing import Any

import pandas as pd


def replace_sentinels_with_nan(
    df: pd.DataFrame,
    *,
    sentinel_values: tuple[float, ...] = (-999, -999.25, -9999, -99999),
) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].replace(list(sentinel_values), pd.NA)
    return out
