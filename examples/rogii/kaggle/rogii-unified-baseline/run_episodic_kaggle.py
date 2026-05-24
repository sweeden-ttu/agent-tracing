#!/usr/bin/env python3
"""Episodic TCN + checkpoint manifest for Kaggle (multi-well, GroupKFold by well_id)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from pipeline.competition_data import load_competition_frames
from pipeline.episodic_benchmark import EpisodicBenchmark
from pipeline.target_diagnostician import recommend_log1p
from pipeline import well_group_detector as wgd
from pipeline.temporal_cnn import (
    TemporalCNN,
    make_sequences,
    predict_windows,
    reassemble,
    rmse,
    train_one_fold,
)
from run_baseline import _submission_id_parts, align_test_preds_to_submission


def _fit_target_transform(
    y_raw: np.ndarray,
    *,
    use_log1p: bool,
) -> tuple[np.ndarray, dict]:
    """Map TVT (feet) to a zero-mean unit-variance training scale for the TCN head."""
    y = np.asarray(y_raw, dtype=np.float64)
    if use_log1p:
        y = np.log1p(np.clip(y, 0.0, None))
    mu = float(np.mean(y))
    sd = float(np.std(y))
    if sd <= 0.0:
        sd = 1.0
    return (y - mu) / sd, {"use_log1p": use_log1p, "target_mean": mu, "target_std": sd}


def _invert_target_transform(pred_scaled: np.ndarray, meta: dict) -> np.ndarray:
    """Undo z-score (and optional log1p) back to feet."""
    fit = np.asarray(pred_scaled, dtype=np.float64) * meta["target_std"] + meta["target_mean"]
    if meta["use_log1p"]:
        fit = np.expm1(np.clip(fit, None, 20.0))
        return np.clip(fit, 0.0, None)
    return fit


def _zscore_per_well(df: pd.DataFrame, cols: list[str], well_col: str = "well_id") -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        g = out.groupby(well_col)[c]
        mu = g.transform("mean")
        sd = g.transform("std").replace(0, 1)
        out[c] = (out[c] - mu) / sd
    return out


def _build_splits(
    train_n: pd.DataFrame,
    target_col: str,
    *,
    n_splits: int,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], str, str | None]:
    """GroupKFold on well_id when possible; else depth-block CV within wells."""
    group_key = wgd.recommend_group_key(train_n, id_column="id")
    n_wells = int(train_n["well_id"].nunique())
    if n_wells >= 2 and group_key:
        groups = (
            wgd.provide_groups(train_n, group_key, id_column="id")
            if not group_key.startswith("__derived")
            else train_n["well_id"].astype(str).values
        )
        n_eff = min(n_splits, wgd.count_unique_groups(groups))
        splits = list(
            GroupKFold(n_splits=n_eff).split(
                train_n, train_n[target_col], groups=groups
            )
        )
        scheme = f"groupkfold(n_splits={n_eff})"
        return splits, scheme, group_key if not group_key.startswith("__") else "well_id"

    qbins = pd.qcut(train_n["MD"], q=n_splits, labels=False, duplicates="drop")
    splits = []
    for fold in sorted(qbins.unique()):
        va = np.where(qbins == fold)[0]
        tr = np.where(qbins != fold)[0]
        splits.append((tr, va))
    return splits, f"depth_block_cv(n_splits={n_splits})", "MD"


def run_episodic(
    data_dir: Path,
    work_dir: Path,
    *,
    n_splits: int = 5,
    episodes_per_fold: int = 2,
    max_epochs: int = 30,
    patience: int = 6,
    window_len: int = 128,
    stride: int = 64,
    hidden: int = 64,
    n_blocks: int = 4,
    batch_size: int = 64,
    seed: int = 42,
) -> dict:
    """Train episodic TCN; write checkpoints, benchmark JSON, and submission CSV."""
    import torch

    work_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir = work_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    train_df, test_df, sample_sub, id_col, target_col = load_competition_frames(data_dir)
    sample_sub = _submission_id_parts(sample_sub, id_col)

    train_target = "TVT" if "TVT" in train_df.columns else target_col
    if train_target not in train_df.columns:
        by_lower = {str(c).lower(): c for c in train_df.columns}
        train_target = by_lower.get(train_target.lower(), train_target)

    y_raw = train_df[train_target].astype(np.float64).values
    log_rec = recommend_log1p(y_raw, skew_threshold=1.5)
    use_log1p = bool(log_rec["use_log1p"])
    y_fit, target_meta = _fit_target_transform(y_raw, use_log1p=use_log1p)
    train_df = train_df.copy()
    train_df[train_target] = y_fit
    print(
        "episodic target: "
        f"{'log1p + ' if use_log1p else ''}global z-score "
        f"(mean={target_meta['target_mean']:.4f}, std={target_meta['target_std']:.4f})"
    )

    exclude = {train_target, "well_id", "is_train", id_col}
    feature_cols = [
        c
        for c in train_df.columns
        if c not in exclude and c in test_df.columns and pd.api.types.is_numeric_dtype(train_df[c])
    ]
    if "MD" not in feature_cols:
        raise ValueError("Episodic TCN requires MD in train and test")

    train_n = _zscore_per_well(train_df, feature_cols).sort_values(["well_id", "MD"]).reset_index(drop=True)
    test_n = _zscore_per_well(test_df, feature_cols).sort_values(["well_id", "MD"]).reset_index(drop=True)

    splits, cv_scheme, group_key = _build_splits(train_n, train_target, n_splits=n_splits)
    overlap = wgd.check_train_test_overlap(
        train_n["well_id"].astype(str).values,
        test_n["well_id"].astype(str).values,
    )

    X_test_seq, _, test_seq_map = make_sequences(
        test_n,
        well_col="well_id",
        depth_col="MD",
        feature_cols=feature_cols,
        target_col=None,
        window_len=window_len,
        stride=stride,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"episodic device: {device}  cv: {cv_scheme}  group_key: {group_key}")

    benchmark = EpisodicBenchmark(
        variant="kaggle_unified",
        approach="episodic TCN (Kaggle trigger)",
        eval_mask="full_well",
        use_log1p=use_log1p,
        feature_cols=feature_cols,
        episodes_per_fold=episodes_per_fold,
        max_epochs=max_epochs,
        patience=patience,
    )
    benchmark.cv_scheme = cv_scheme

    oof = np.full(len(train_n), np.nan, dtype=np.float64)
    fold_rmses: list[float] = []
    test_preds_per_fold = np.zeros((len(test_n), len(splits)), dtype=np.float64)
    best_checkpoints: list[dict] = []
    t0 = time.time()

    for fold, (tr_idx, va_idx) in enumerate(splits):
        best_ep_rmse = float("inf")
        best_ep_path: Path | None = None
        for ep in range(episodes_per_fold):
            ep_seed = seed + fold * 1000 + ep * 17
            torch.manual_seed(ep_seed)
            np.random.seed(ep_seed)

            tr_df = train_n.iloc[tr_idx].reset_index(drop=True)
            va_df = train_n.iloc[va_idx].reset_index(drop=True)
            X_tr, y_tr, _ = make_sequences(
                tr_df,
                well_col="well_id",
                depth_col="MD",
                feature_cols=feature_cols,
                target_col=train_target,
                window_len=window_len,
                stride=stride,
            )
            X_va, y_va, va_map = make_sequences(
                va_df,
                well_col="well_id",
                depth_col="MD",
                feature_cols=feature_cols,
                target_col=train_target,
                window_len=window_len,
                stride=stride,
            )
            model, best_win_rmse, hist = train_one_fold(
                X_tr,
                y_tr,
                X_va,
                y_va,
                n_features=len(feature_cols),
                hidden=hidden,
                n_blocks=n_blocks,
                max_epochs=max_epochs,
                patience=patience,
                batch_size=batch_size,
                verbose=False,
            )
            model = model.to(device)

            ckpt_path = ckpt_dir / f"fold_{fold}_ep_{ep}.pt"
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "fold": fold,
                    "episode": ep,
                    "val_rmse": best_win_rmse,
                    "feature_cols": feature_cols,
                    "window_len": window_len,
                    "hidden": hidden,
                    "n_blocks": n_blocks,
                    "target_meta": target_meta,
                },
                ckpt_path,
            )

            va_win = predict_windows(model, X_va, batch_size=batch_size)
            va_row = reassemble(va_win, va_map)
            va_fit = va_row[: len(va_df)]
            y_va_feet = y_raw[va_idx]
            ep_val_feet = rmse(y_va_feet, _invert_target_transform(va_fit, target_meta))

            benchmark.record_episode(
                fold=fold,
                episode=ep,
                seed=ep_seed,
                val_rmse=ep_val_feet,
                best_window_rmse=best_win_rmse,
                checkpoint=str(ckpt_path.name),
                n_epochs=len(hist),
            )
            print(f"  fold {fold} ep {ep}: val_rmse={ep_val_feet:.4f} ft")

            if ep_val_feet < best_ep_rmse:
                best_ep_rmse = ep_val_feet
                best_ep_path = ckpt_path
                oof[va_idx] = va_fit

        if best_ep_path is None:
            raise RuntimeError(f"No episodic checkpoint for fold {fold}")

        fold_rmses.append(best_ep_rmse)
        benchmark.set_fold_best(fold, best_ep_path.name, best_ep_rmse)
        best_checkpoints.append(
            {"fold": fold, "checkpoint": best_ep_path.name, "val_rmse": best_ep_rmse}
        )

        ckpt = torch.load(best_ep_path, map_location=device, weights_only=False)
        model = TemporalCNN(
            len(feature_cols),
            hidden=hidden,
            n_blocks=n_blocks,
        ).to(device)
        model.load_state_dict(ckpt["state_dict"])
        te_win = predict_windows(model, X_test_seq, batch_size=batch_size)
        test_preds_per_fold[:, fold] = reassemble(te_win, test_seq_map)

    elapsed = time.time() - t0
    mask = ~np.isnan(oof)
    oof_feet = _invert_target_transform(oof[mask], target_meta)
    oof_rmse = rmse(y_raw[mask], oof_feet)
    cumulative_rmse_feet = float(sum(fold_rmses))

    test_pred = _invert_target_transform(test_preds_per_fold.mean(axis=1), target_meta)
    fallback = float(np.mean(y_raw))
    aligned = align_test_preds_to_submission(
        test_pred, test_n, sample_sub, id_col, fallback=fallback
    )
    sub = pd.DataFrame({id_col: sample_sub[id_col].astype(str), target_col: aligned})
    out_cols = [c for c in sample_sub.columns if c in sub.columns]
    sub = sub[out_cols]
    sub_path = work_dir / "submission_episodic.csv"
    sub.to_csv(sub_path, index=False)

    benchmark.finalize(
        oof_rmse=oof_rmse,
        fold_rmses=fold_rmses,
        elapsed_seconds=elapsed,
        oof_rmse_raw_scale=oof_rmse,
    )
    benchmark.write_json(work_dir / "episodic_benchmark.json")

    manifest = {
        "cv_scheme": cv_scheme,
        "group_key": group_key,
        "well_group_overlap": overlap,
        "target_transform": target_meta,
        "oof_rmse_feet": oof_rmse,
        "cumulative_rmse_feet": cumulative_rmse_feet,
        "fold_rmses": fold_rmses,
        "best_checkpoints": best_checkpoints,
        "checkpoints_dir": str(ckpt_dir),
        "elapsed_seconds": elapsed,
        "device": str(device),
    }
    (ckpt_dir / "episode_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (work_dir / "ensemble_manifest.json").write_text(
        json.dumps(
            {
                "models": ["tabular_baseline", "episodic_tcn"],
                "checkpoints": best_checkpoints,
                "episodic_oof_rmse_feet": oof_rmse,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Episodic OOF RMSE: {oof_rmse:.4f} ft  cumulative_fold_sum: {cumulative_rmse_feet:.4f}")
    print(f"Wrote {sub_path} and checkpoints under {ckpt_dir}")

    return {
        "oof_rmse_feet": oof_rmse,
        "cumulative_rmse_feet": cumulative_rmse_feet,
        "fold_rmses": fold_rmses,
        "cv_scheme": cv_scheme,
        "group_key": group_key,
        "target_transform": target_meta,
        "submission_path": str(sub_path),
        "checkpoints": best_checkpoints,
        "elapsed_seconds": elapsed,
    }
