#!/usr/bin/env python3
"""Unified ROGII baseline: multi-well load, CV RMSE, Kaggle submission, synthetic holdout RMSE."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_BUNDLE = Path(__file__).resolve().parent
if str(_BUNDLE) not in sys.path:
    sys.path.insert(0, str(_BUNDLE))

from pipeline.competition_data import load_competition_frames  # noqa: E402
from train_predict import (  # noqa: E402
    align_train_target_to_schema,
    build_feature_matrix,
    categorize_columns,
    cross_val_and_predict,
    rmse,
)
from pipeline.preprocessor import replace_sentinels_with_nan  # noqa: E402
from pipeline.target_diagnostician import recommend_log1p  # noqa: E402
from pipeline import well_group_detector as wgd  # noqa: E402
from train_predict import _effective_cv, _HAS_LGBM, _configure_preprocessor_output  # noqa: E402

_SENTINELS = (-999, -999.25, -9999, -99999)


def _submission_id_parts(sample_sub: pd.DataFrame, id_col: str) -> pd.DataFrame:
    sub = sample_sub.copy()
    if "row_idx" not in sub.columns and id_col in sub.columns:
        parts = sub[id_col].astype(str).str.split("_", n=1, expand=True)
        sub["well_id"] = parts[0]
        sub["row_idx"] = pd.to_numeric(parts[1], errors="coerce").fillna(0).astype(int)
    return sub


def align_test_preds_to_submission(
    test_pred: np.ndarray,
    test_df: pd.DataFrame,
    sample_sub: pd.DataFrame,
    id_col: str,
    *,
    fallback: float,
) -> np.ndarray:
    te = test_df.copy()
    te["_pred"] = np.asarray(test_pred, dtype=np.float64)[: len(te)]
    te["_row"] = te.groupby("well_id").cumcount()
    lookup = te.set_index(["well_id", "_row"])["_pred"]
    sub = _submission_id_parts(sample_sub, id_col)
    return np.array(
        [
            float(lookup.get((r["well_id"], int(r["row_idx"])), fallback))
            for _, r in sub.iterrows()
        ],
        dtype=np.float64,
    )


def synthetic_oracle_rmse(
    submission: pd.DataFrame,
    oracle_path: Path,
    *,
    id_col: str,
    target_col: str,
) -> float | None:
    if not oracle_path.is_file():
        return None
    oracle = pd.read_csv(oracle_path)
    sub = submission.copy()
    sub[id_col] = sub[id_col].astype(str)
    oracle[id_col] = oracle[id_col].astype(str)
    merged = sub.merge(oracle, on=id_col, suffixes=("_pred", "_true"))
    if merged.empty:
        return None
    pred_col = f"{target_col}_pred" if f"{target_col}_pred" in merged.columns else target_col
    true_col = f"{target_col}_true" if f"{target_col}_true" in merged.columns else target_col
    if pred_col == true_col:
        cols = [c for c in merged.columns if c.endswith("_pred")]
        pred_col = cols[0] if cols else target_col
        true_col = pred_col.replace("_pred", "_true")
    return rmse(merged[true_col].values, merged[pred_col].values)


def resolve_data_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    kaggle = Path("/kaggle/input/rogii-wellbore-geology-prediction")
    if kaggle.is_dir():
        return kaggle
  # Dev fallback: rogii repo synthetic flat layout
    dev = Path("/lustre/work/sweeden/rogii/data")
    if dev.is_dir() and (dev / "sample_submission.csv").is_file():
        return dev
    local = _BUNDLE / "data"
    if local.is_dir():
        return local.resolve()
    raise FileNotFoundError("No competition data directory found (set --data-dir)")


def run(
    data_dir: Path,
    work_dir: Path,
    *,
    n_splits: int = 5,
) -> dict:
    work_dir.mkdir(parents=True, exist_ok=True)
    train_df, test_df, sample_sub, id_col, target_col = load_competition_frames(data_dir)
    sample_sub = _submission_id_parts(sample_sub, id_col)

    train_target = "TVT" if "TVT" in train_df.columns else target_col
    train_df = align_train_target_to_schema(train_df, train_target)
    target = train_target

    y_raw = train_df[target].astype(np.float64).values
    log_rec = recommend_log1p(y_raw, skew_threshold=1.5)
    use_log1p = bool(log_rec["use_log1p"])
    is_positive = bool(log_rec["strict_positivity"]["strict_positive"])
    y_fit = np.log1p(np.clip(y_raw, a_min=0.0, a_max=None)) if use_log1p else y_raw
    y_original = y_raw

    base_exclude = {target, "well_id", "is_train", id_col}
    feature_cols = [
        c
        for c in train_df.columns
        if c not in base_exclude and c in test_df.columns and pd.api.types.is_numeric_dtype(train_df[c])
    ]
    if not feature_cols:
        raise ValueError("No overlapping numeric feature columns between train and test")

    X_train = replace_sentinels_with_nan(train_df[feature_cols].copy(), sentinel_values=_SENTINELS)
    X_test = replace_sentinels_with_nan(test_df[feature_cols].copy(), sentinel_values=_SENTINELS)

    num, low_c, high_c = categorize_columns(
        pd.concat([X_train, X_test], axis=0, ignore_index=True),
        id_col=id_col,
        target_cols=[target],
    )
    preprocessor = build_feature_matrix(
        X_train, numeric_cols=num, low_card_cols=low_c, high_card_cols=high_c
    )
    if _HAS_LGBM:
        _configure_preprocessor_output(preprocessor)

    scheme, groups, n_splits_eff = _effective_cv(train_df, test_df, id_col=id_col, n_splits_req=n_splits)
    group_key = wgd.recommend_group_key(train_df, test_df, id_column=id_col)

    cv_rmse, fold_rmses, test_mat, oof_fit = cross_val_and_predict(
        X_train,
        y_fit,
        y_original,
        X_test,
        preprocessor,
        scheme=scheme,
        groups=groups,
        n_splits=n_splits_eff,
        use_log1p=use_log1p,
    )

    test_mean_fit = test_mat.mean(axis=1)
    if use_log1p:
        test_pred = np.expm1(np.clip(test_mean_fit, a_min=None, a_max=20.0))
        if is_positive:
            test_pred = np.clip(test_pred, a_min=0.0, a_max=None)
    else:
        test_pred = test_mean_fit
        if is_positive:
            test_pred = np.clip(test_pred, a_min=0.0, a_max=None)

    pred_fallback = float(np.nanmean(y_raw))
    aligned = align_test_preds_to_submission(
        test_pred, test_df, sample_sub, id_col, fallback=pred_fallback
    )

    out_df = pd.DataFrame({id_col: sample_sub[id_col].astype(str), target_col: aligned})
    out_cols = [c for c in sample_sub.columns if c in out_df.columns]
    out_df = out_df[out_cols]
    sub_path = work_dir / "submission.csv"
    out_df.to_csv(sub_path, index=False)

    oracle_path = data_dir / "submission_samples" / "submission.csv"
    holdout_rmse = synthetic_oracle_rmse(out_df, oracle_path, id_col=id_col, target_col=target_col)

    cumulative_rmse_feet = float(sum(fold_rmses)) if fold_rmses else float("nan")

    metrics = {
        "cv_rmse": cv_rmse,
        "cv_rmse_feet": cv_rmse,
        "cumulative_rmse_feet": cumulative_rmse_feet,
        "fold_rmses": fold_rmses,
        "n_folds": n_splits_eff,
        "cv_scheme": scheme,
        "group_key": group_key,
        "id_column": id_col,
        "target_column": target_col,
        "backend": "lightgbm" if _HAS_LGBM else "sklearn.hist_gradient_boosting",
        "use_log1p": use_log1p,
        "n_train_rows": len(train_df),
        "n_test_rows": len(test_df),
        "n_submission_rows": len(out_df),
        "n_wells_train": int(train_df["well_id"].nunique()),
        "n_wells_test": int(test_df["well_id"].nunique()),
        "data_dir": str(data_dir),
        "holdout_rmse_synthetic": holdout_rmse,
    }
    metrics_path = work_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    print(f"OOF CV RMSE (original scale): {cv_rmse:.6f}")
    if holdout_rmse is not None:
        print(f"Synthetic holdout RMSE (submission vs oracle): {holdout_rmse:.6f}")
    print(f"Wrote {sub_path} ({len(out_df)} rows)")
    print(f"Wrote {metrics_path}")
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="ROGII unified baseline runner")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--work-dir", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--n-splits", type=int, default=5)
    args = ap.parse_args()
    try:
        data_dir = resolve_data_dir(args.data_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    run(data_dir, args.work_dir.resolve(), n_splits=args.n_splits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
