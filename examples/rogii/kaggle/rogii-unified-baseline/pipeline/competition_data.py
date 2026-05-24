"""Load ROGII competition data from flat or multi-well Kaggle layouts."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

_WELL_RE = re.compile(r"_?(?:train|test|)_?([0-9a-f]+)_", re.I)


def _well_from_stem(stem: str) -> str:
    m = _WELL_RE.match(stem + "_")
    if m:
        return m.group(1).lower()
    if "__horizontal_well" in stem:
        return stem.split("__")[0].lstrip("_")
    return stem


def _glob_horizontal(dir_path: Path, split: str) -> list[Path]:
    if not dir_path.is_dir():
        return []
    return sorted(dir_path.glob(f"*__horizontal_well.csv")) or sorted(
        dir_path.glob(f"_{split}_*horizontal_well.csv")
    )


def discover_layout(data_dir: Path) -> str:
    data_dir = data_dir.resolve()
    if (data_dir / "train").is_dir() and _glob_horizontal(data_dir / "train", "train"):
        return "kaggle_multiwell"
    if list(data_dir.glob("_train_*horizontal_well.csv")):
        return "flat"
    # Single merged train.csv (must not match *train*.csv — that glob hits train.csv)
    if (data_dir / "train.csv").is_file():
        return "merged_csv"
    return "unknown"


def _read_well_csv(path: Path, *, well_id: str, is_train: bool) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["well_id"] = well_id
    df["is_train"] = is_train
    return df


def load_competition_frames(
    data_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str, str]:
    """Return ``train_df, test_df, sample_sub, id_col, target_col``."""
    data_dir = data_dir.resolve()
    sample_path = data_dir / "sample_submission.csv"
    if not sample_path.is_file():
        raise FileNotFoundError(f"Missing sample_submission.csv under {data_dir}")
    sample_sub = pd.read_csv(sample_path)
    cols = list(sample_sub.columns)
    if len(cols) < 2:
        raise ValueError("sample_submission needs id + target columns")
    id_col, target_col = cols[0], cols[1]

    layout = discover_layout(data_dir)
    train_parts: list[pd.DataFrame] = []
    test_parts: list[pd.DataFrame] = []

    if layout == "kaggle_multiwell":
        for p in _glob_horizontal(data_dir / "train", "train"):
            wid = _well_from_stem(p.stem)
            train_parts.append(_read_well_csv(p, well_id=wid, is_train=True))
        for p in _glob_horizontal(data_dir / "test", "test"):
            wid = _well_from_stem(p.stem)
            test_parts.append(_read_well_csv(p, well_id=wid, is_train=False))
    elif layout == "flat":
        for p in sorted(data_dir.glob("_train_*horizontal_well.csv")):
            wid = _well_from_stem(p.stem)
            train_parts.append(_read_well_csv(p, well_id=wid, is_train=True))
        for p in sorted(data_dir.glob("_test_*horizontal_well.csv")):
            wid = _well_from_stem(p.stem)
            test_parts.append(_read_well_csv(p, well_id=wid, is_train=False))
        if not train_parts:
            tp = data_dir / "train.csv"
            if tp.is_file():
                train_parts.append(_read_well_csv(tp, well_id="default", is_train=True))
        if not test_parts:
            tp = data_dir / "test.csv"
            if tp.is_file():
                test_parts.append(_read_well_csv(tp, well_id="default", is_train=False))
    elif layout == "merged_csv":
        train_parts.append(_read_well_csv(data_dir / "train.csv", well_id="default", is_train=True))
        test_parts.append(_read_well_csv(data_dir / "test.csv", well_id="default", is_train=False))
    else:
        raise FileNotFoundError(f"Unrecognized data layout under {data_dir}")

    if not train_parts or not test_parts:
        raise FileNotFoundError(f"Could not locate train/test CSVs in {data_dir} (layout={layout})")

    train_df = pd.concat(train_parts, ignore_index=True)
    test_df = pd.concat(test_parts, ignore_index=True)

    # Align target column name (TVT vs tvt)
    if target_col not in train_df.columns:
        by_lower = {str(c).lower(): c for c in train_df.columns}
        if target_col.lower() in by_lower:
            train_df = train_df.rename(columns={by_lower[target_col.lower()]: target_col})

    # Synthetic row ids when missing (dev smoke)
    if id_col not in test_df.columns:
        test_df[id_col] = (
            test_df["well_id"].astype(str) + "_" + test_df.groupby("well_id").cumcount().astype(str)
        )
    if id_col not in train_df.columns:
        train_df[id_col] = (
            train_df["well_id"].astype(str) + "_" + train_df.groupby("well_id").cumcount().astype(str)
        )

    # Parse well + row index from submission ids for alignment
    sample_sub = sample_sub.copy()
    if "well_id" not in sample_sub.columns and "_" in str(sample_sub[id_col].iloc[0]):
        parts = sample_sub[id_col].astype(str).str.split("_", n=1, expand=True)
        sample_sub["well_id"] = parts[0]
        sample_sub["row_idx"] = pd.to_numeric(parts[1], errors="coerce").fillna(0).astype(int)

    return train_df, test_df, sample_sub, id_col, target_col


def load_typewell_lookup(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Map well_id → typewell dataframe (may be empty for dev layout)."""
    data_dir = data_dir.resolve()
    out: dict[str, pd.DataFrame] = {}
    candidates = list(data_dir.glob("*__typewell.csv"))
    candidates += list((data_dir / "train").glob("*__typewell.csv")) if (data_dir / "train").is_dir() else []
    for p in candidates:
        # Skip macOS AppleDouble / hidden files (e.g. ._000d7d20__typewell.csv).
        if p.name.startswith("._") or p.name.startswith("."):
            continue
        wid = p.stem.replace("__typewell", "").lstrip("_")
        out[wid] = pd.read_csv(p)
    return out
