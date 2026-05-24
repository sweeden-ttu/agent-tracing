"""Shared path resolution for Rogii Jupyter notebooks (cwd-safe)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def competition_root() -> Path:
    """Directory that contains ``pipeline/`` and ``data/`` (Rogii competition folder)."""
    here = Path.cwd().resolve()
    for base in (here, *here.parents):
        if (base / "pipeline").is_dir() and (base / "data").is_dir():
            return base
    # Fallback: parent of notebooks/
    if (here / "pipeline").is_dir():
        return here
    return here.parent


def load_train_predict():
    root = competition_root()
    path = root / "train_predict.py"
    spec = importlib.util.spec_from_file_location("rogii_train_predict_nb", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve_tabular_csvs(data_dir: Path | None = None) -> tuple[Path, Path, Path]:
    """Return ``(train_path, test_path, sample_submission_path)`` using ``train_predict`` heuristics."""
    tp = load_train_predict()
    d = (data_dir or competition_root() / "data").resolve()
    return (
        tp._find_default_csv(d, "train"),
        tp._find_default_csv(d, "test"),
        tp._find_default_csv(d, "sample_submission"),
    )


def ensure_id_column(df: Any, id_col: str) -> Any:
    """If ``id_col`` is missing, add a synthetic id for offline notebook smoke (not for Kaggle)."""
    import numpy as np

    if id_col in df.columns:
        return df
    out = df.copy()
    out.insert(0, id_col, np.arange(len(out), dtype=np.int64).astype(str))
    return out


def build_aligned_sample_submission(
    sample_sub: Any,
    test_df: Any,
    *,
    id_col: str,
    target_col: str,
    out_path: Path,
) -> Path:
    """Build a ``sample_submission``-shaped frame with one row per test row (for envelope validator)."""
    import pandas as pd

    aligned = pd.DataFrame({id_col: test_df[id_col].values})
    for c in sample_sub.columns:
        if c == id_col:
            continue
        aligned[c] = 0.0 if c == target_col else 0.0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(out_path, index=False)
    return out_path
