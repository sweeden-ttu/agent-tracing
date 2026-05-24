#!/usr/bin/env python3
"""RMSE-oriented baseline for Kaggle *ROGII - Wellbore Geology Prediction*.

Leaderboard metric::

    RMSE = sqrt( (1/n) * sum_i (y_hat_i - y_i)^2 )

Training may use ``log1p(y)`` when the target is strictly positive and skewed; local
**OOF RMSE** is reported on the **original target scale** (after ``expm1`` when
applicable) to match Kaggle. Prefer **GroupKFold** on a well-like column or on a
prefix derived from ``id`` when no dedicated well column exists.

Usage::

    python train_predict.py --data-dir data --out submission.csv

Dependencies: pandas, numpy, scikit-learn; optional lightgbm (recommended).
Run from the competition directory (the folder that contains ``pipeline/``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.cv_orchestrator import choose_cv_scheme, emit_fold_indices
from pipeline.nb_support import ensure_id_column
from pipeline.preprocessor import replace_sentinels_with_nan
from pipeline.target_diagnostician import recommend_log1p
from pipeline import well_group_detector as wgd

try:
    import lightgbm as lgb

    _HAS_LGBM = True
except ImportError:
    _HAS_LGBM = False

from sklearn.ensemble import HistGradientBoostingRegressor

_SENTINELS = (-999, -999.25, -9999, -99999)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root mean squared error (matches Kaggle definition for vector errors)."""
    y_true = np.asarray(y_true, dtype=np.float64).ravel()
    y_pred = np.asarray(y_pred, dtype=np.float64).ravel()
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _find_default_csv(data_dir: Path, stem: str) -> Path:
    for name in (f"{stem}.csv", f"{stem.capitalize()}.csv"):
        p = data_dir / name
        if p.is_file():
            return p
    for p in sorted(data_dir.glob("*.csv")):
        if p.name.startswith(".") or p.name.startswith("._"):
            continue
        if stem.lower() in p.stem.lower():
            return p
    raise FileNotFoundError(f"No {stem} CSV under {data_dir}")


def infer_columns(sample_submission: pd.DataFrame) -> tuple[str, list[str]]:
    cols = list(sample_submission.columns)
    if len(cols) < 2:
        raise ValueError("sample_submission needs at least id + one target column")
    id_col = cols[0]
    target_cols = cols[1:]
    return id_col, target_cols


def align_train_target_to_schema(train_df: pd.DataFrame, target_name: str) -> pd.DataFrame:
    """Rename train target column to match ``sample_submission`` (handles ``TVT`` vs ``tvt``)."""
    if target_name in train_df.columns:
        return train_df
    by_lower = {str(c).lower(): c for c in train_df.columns}
    key = str(target_name).lower()
    if key not in by_lower:
        raise ValueError(
            f"Target {target_name!r} not in train columns and no case-insensitive match. "
            f"Train columns: {list(train_df.columns)}"
        )
    actual = by_lower[key]
    out = train_df.rename(columns={actual: target_name})
    return out


def build_feature_matrix(
    X: pd.DataFrame,
    *,
    numeric_cols: list[str],
    low_card_cols: list[str],
    high_card_cols: list[str],
) -> ColumnTransformer:
    """Preprocessing: median imputation + one-hot / ordinal encoders."""
    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric_cols:
        transformers.append(
            (
                "num",
                Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                numeric_cols,
            )
        )
    if low_card_cols:
        transformers.append(
            (
                "cat_low",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "oh",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False, max_categories=50),
                        ),
                    ]
                ),
                low_card_cols,
            )
        )
    if high_card_cols:
        transformers.append(
            (
                "cat_high",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("ord", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
                    ]
                ),
                high_card_cols,
            )
        )
    if not transformers:
        raise ValueError("No feature columns after excluding id/target")
    return ColumnTransformer(transformers=transformers, remainder="drop", verbose_feature_names_out=False)


def categorize_columns(
    df: pd.DataFrame,
    *,
    id_col: str,
    target_cols: list[str],
    max_card_for_onehot: int = 32,
) -> tuple[list[str], list[str], list[str]]:
    exclude = {id_col, *target_cols}
    numeric: list[str] = []
    low_card: list[str] = []
    high_card: list[str] = []
    for c in df.columns:
        if c in exclude:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            numeric.append(c)
            continue
        nuniq = df[c].astype(str).nunique(dropna=False)
        if nuniq <= max_card_for_onehot:
            low_card.append(c)
        else:
            high_card.append(c)
    return numeric, low_card, high_card


def _configure_preprocessor_output(preprocessor: ColumnTransformer) -> None:
    """Prefer pandas transform output when the sklearn version supports it."""
    try:
        preprocessor.set_output(transform="pandas")
    except Exception:
        pass


def _prepare_lgbm_features(preprocessor: ColumnTransformer, X: pd.DataFrame) -> pd.DataFrame:
    """LightGBM sklearn API always records ``feature_names_in_``; use named columns.

    Without this, ``fit`` on a bare ndarray still sets names like ``Column_0`` and
    ``predict`` on ndarray triggers sklearn's feature-name validation warning.
    """
    Xt = preprocessor.transform(X)
    names = list(preprocessor.get_feature_names_out())
    if isinstance(Xt, pd.DataFrame):
        if list(Xt.columns) != names:
            Xt = Xt.set_axis(names, axis=1)
        return Xt
    return pd.DataFrame(Xt, columns=names, index=X.index)


def make_estimator(n_rows: int):
    if _HAS_LGBM:
        return lgb.LGBMRegressor(
            objective="regression",
            metric="rmse",
            n_estimators=2000,
            learning_rate=0.05,
            num_leaves=63,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=1.0,
            random_state=42,
            verbose=-1,
        )
    return HistGradientBoostingRegressor(
        max_depth=10,
        max_iter=500,
        learning_rate=0.06,
        random_state=42,
    )


def _effective_cv(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    id_col: str,
    n_splits_req: int,
) -> tuple[str, np.ndarray | None, int]:
    """Return ``(scheme, groups_or_none, n_splits)`` for CV."""
    scheme = choose_cv_scheme(train_df, test_df, id_column=id_col)
    group_key = wgd.recommend_group_key(train_df, test_df, id_column=id_col)
    if scheme != "groupkfold" or group_key is None:
        return "kfold", None, n_splits_req
    groups = wgd.provide_groups(train_df, group_key, id_column=id_col)
    n_groups = wgd.count_unique_groups(groups)
    if n_groups < 2:
        return "kfold", None, n_splits_req
    n_splits_eff = min(n_splits_req, n_groups)
    if n_splits_eff < 2:
        return "kfold", None, min(n_splits_req, max(2, len(train_df) // 2))
    return "groupkfold", groups, n_splits_eff


def cross_val_and_predict(
    X: pd.DataFrame,
    y_fit: np.ndarray,
    y_original: np.ndarray,
    X_test: pd.DataFrame,
    preprocessor: ColumnTransformer,
    *,
    scheme: str,
    groups: np.ndarray | None,
    n_splits: int,
    use_log1p: bool,
    val_row_mask: np.ndarray | None = None,
) -> tuple[float, list[float], np.ndarray, np.ndarray]:
    """OOF RMSE on **original** scale, per-fold RMSEs, stacked test preds per fold, OOF predictions in fit space."""
    fold_iter = emit_fold_indices(
        scheme if scheme == "groupkfold" else "kfold",
        X,
        n_splits=n_splits,
        groups=groups,
        shuffle=True,
        random_state=42,
    )
    oof_fit = np.full(len(X), np.nan, dtype=np.float64)
    test_blocks: list[np.ndarray] = []
    fold_rmses: list[float] = []

    for train_idx, val_idx in fold_iter:
        if val_row_mask is not None and len(val_row_mask) == len(X):
            val_idx = val_idx[val_row_mask[val_idx]]
            if len(val_idx) == 0:
                continue

        if scheme == "groupkfold" and groups is not None:
            g_tr = set(np.asarray(groups)[train_idx].astype(str))
            g_va = set(np.asarray(groups)[val_idx].astype(str))
            assert not (g_tr & g_va), "GroupKFold leak: train and val share a group id"

        prep: ColumnTransformer = clone(preprocessor)
        if _HAS_LGBM:
            _configure_preprocessor_output(prep)
        X_tr, X_va = X.iloc[train_idx], X.iloc[val_idx]
        y_tr_fit = y_fit[train_idx]
        y_va_orig = y_original[val_idx]
        prep.fit(X_tr, y_tr_fit)
        if _HAS_LGBM:
            Xtr_t = _prepare_lgbm_features(prep, X_tr)
            Xva_t = _prepare_lgbm_features(prep, X_va)
            Xte_t = _prepare_lgbm_features(prep, X_test)
        else:
            Xtr_t = prep.transform(X_tr)
            Xva_t = prep.transform(X_va)
            Xte_t = prep.transform(X_test)
        est = make_estimator(len(X_tr))
        if _HAS_LGBM and isinstance(est, lgb.LGBMRegressor):
            est.fit(
                Xtr_t,
                y_tr_fit,
                eval_set=[(Xva_t, y_fit[val_idx])],
                callbacks=[lgb.early_stopping(50, verbose=False)],
            )
        else:
            est.fit(Xtr_t, y_tr_fit)
        pred_va_fit = est.predict(Xva_t)
        oof_fit[val_idx] = pred_va_fit
        if use_log1p:
            pred_va = np.expm1(np.clip(pred_va_fit, a_min=None, a_max=20.0))
            pred_va = np.clip(pred_va, a_min=0.0, a_max=None)
            fold_rmses.append(rmse(y_va_orig, pred_va))
        else:
            fold_rmses.append(rmse(y_va_orig, pred_va_fit))
        test_blocks.append(est.predict(Xte_t))

    mean_rmse = float(np.mean(fold_rmses)) if fold_rmses else float("nan")
    test_mat = np.column_stack(test_blocks) if test_blocks else np.zeros((len(X_test), 0))
    return mean_rmse, fold_rmses, test_mat, oof_fit


def main() -> int:
    parser = argparse.ArgumentParser(description="ROGII Wellbore Geology — RMSE baseline")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Directory with train/test/sample_submission")
    parser.add_argument("--out", type=Path, default=Path("submission.csv"))
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--metrics-json", type=Path, default=None, help="Optional path to write CV metrics JSON")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="If set, write transform.json and test_preds_per_fold.npy (notebook-compatible artifacts)",
    )
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    if not data_dir.is_dir():
        print(f"data-dir not found: {data_dir}", file=sys.stderr)
        return 1

    try:
        train_path = _find_default_csv(data_dir, "train")
        test_path = _find_default_csv(data_dir, "test")
        sample_path = _find_default_csv(data_dir, "sample_submission")
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    sample_sub = pd.read_csv(sample_path, nrows=0)
    id_col, target_cols = infer_columns(sample_sub)

    if len(target_cols) != 1:
        print(
            "This baseline supports exactly one prediction column after the id. "
            f"Found: {target_cols}. Extend train_predict.py for multi-target.",
            file=sys.stderr,
        )
        return 1
    target = target_cols[0]
    try:
        train_df = align_train_target_to_schema(train_df, target)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    train_df = ensure_id_column(train_df, id_col)
    test_df = ensure_id_column(test_df, id_col)

    y_raw = train_df[target].astype(np.float64).values
    log_rec = recommend_log1p(y_raw, skew_threshold=1.5)
    use_log1p = bool(log_rec["use_log1p"])
    is_positive = bool(log_rec["strict_positivity"]["strict_positive"])
    y_fit = np.log1p(np.clip(y_raw, a_min=0.0, a_max=None)) if use_log1p else y_raw
    y_original = y_raw

    feature_cols = [c for c in train_df.columns if c not in (id_col, target) and c in test_df.columns]
    if not feature_cols:
        print("No overlapping feature columns between train and test (excluding id/target).", file=sys.stderr)
        return 1

    X_train = replace_sentinels_with_nan(train_df[feature_cols].copy(), sentinel_values=_SENTINELS)
    X_test = replace_sentinels_with_nan(test_df[feature_cols].copy(), sentinel_values=_SENTINELS)

    num, low_c, high_c = categorize_columns(
        pd.concat([X_train, X_test], axis=0, ignore_index=True),
        id_col=id_col,
        target_cols=[target],
    )

    preprocessor = build_feature_matrix(
        X_train,
        numeric_cols=num,
        low_card_cols=low_c,
        high_card_cols=high_c,
    )
    if _HAS_LGBM:
        _configure_preprocessor_output(preprocessor)

    scheme, groups, n_splits = _effective_cv(train_df, test_df, id_col=id_col, n_splits_req=args.n_splits)
    group_key = wgd.recommend_group_key(train_df, test_df, id_column=id_col)
    print(f"CV scheme: {scheme} (n_splits={n_splits})" + (f", group_key={group_key!r}" if group_key else ""))

    cv_rmse, fold_rmses, test_mat, oof_fit = cross_val_and_predict(
        X_train,
        y_fit,
        y_original,
        X_test,
        preprocessor,
        scheme=scheme,
        groups=groups,
        n_splits=n_splits,
        use_log1p=use_log1p,
    )

    cv_rmse_transformed = (
        float(np.sqrt(np.nanmean((y_fit - oof_fit) ** 2))) if np.any(np.isfinite(oof_fit)) else None
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

    print(f"OOF RMSE (original target scale, mean over folds): {cv_rmse:.6f}")
    if cv_rmse_transformed is not None and use_log1p:
        print(f"OOF RMSE (log1p training scale): {cv_rmse_transformed:.6f}")
    print(f"use_log1p={use_log1p}; backend={'lightgbm' if _HAS_LGBM else 'sklearn HistGradientBoostingRegressor'}")

    out_df = pd.DataFrame({id_col: test_df[id_col], target: test_pred})
    out_df = out_df[[c for c in sample_sub.columns if c in out_df.columns]]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False)
    print(f"Wrote {args.out.resolve()} ({len(out_df)} rows)")

    if args.metrics_json:
        payload = {
            "cv_rmse": cv_rmse,
            "cv_rmse_transformed": cv_rmse_transformed,
            "fold_rmses": fold_rmses,
            "n_folds": n_splits,
            "cv_scheme": scheme,
            "group_key": group_key,
            "backend": "lightgbm" if _HAS_LGBM else "sklearn.hist_gradient_boosting",
            "id_column": id_col,
            "target_column": target,
            "use_log1p": use_log1p,
            "is_positive": is_positive,
        }
        args.metrics_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if args.artifacts_dir is not None:
        ad = args.artifacts_dir.resolve()
        ad.mkdir(parents=True, exist_ok=True)
        transform = {
            "use_log1p": use_log1p,
            "is_positive": is_positive,
            "target_column": target,
            "id_column": id_col,
            "cv_rmse": cv_rmse,
            "cv_rmse_transformed": cv_rmse_transformed,
            "fold_rmses": fold_rmses,
            "group_col": None if group_key is None or str(group_key).startswith("__derived") else group_key,
            "group_key_resolved": group_key,
            "n_folds": n_splits,
            "cv_scheme": scheme,
            "paths": {
                "train_csv": str(train_path.resolve()),
                "test_csv": str(test_path.resolve()),
                "sample_submission": str(sample_path.resolve()),
            },
        }
        (ad / "transform.json").write_text(json.dumps(transform, indent=2) + "\n", encoding="utf-8")
        np.save(ad / "test_preds_per_fold.npy", test_mat)
        print(f"Wrote {ad / 'transform.json'} and test_preds_per_fold.npy")

    try:
        from pipeline.tcn_runner import write_artifacts_index

        write_artifacts_index(_ROOT)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
