#!/usr/bin/env python3
"""Standalone CLI runner for the ROGII trace baseline pipeline.

Executes the same logic as the notebook:
  data load → well-group CV → tabular baseline → RMSE gate (12 ft)
  → episodic TCN (if triggered) → ensemble blend → submission.

Usage::
    python run_baseline.py --data-dir /lustre/work/sweeden/rogii/data --out-dir ./output
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold

SEED = 42
N_SPLITS = 5
SENTINELS = (-999, -999.25, -9999, -99999)
_WELL_RE = re.compile(r"_?(?:train|test|)_?([0-9a-f]+)_", re.I)

try:
    import lightgbm as lgb
    _HAS_LGBM = True
except ImportError:
    _HAS_LGBM = False

from sklearn.ensemble import HistGradientBoostingRegressor


def rmse(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=np.float64).ravel()
    y_pred = np.asarray(y_pred, dtype=np.float64).ravel()
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not mask.any():
        return float("nan")
    return float(np.sqrt(np.mean((y_true[mask] - y_pred[mask]) ** 2)))


def _well_from_stem(stem):
    m = _WELL_RE.match(stem + "_")
    if m:
        return m.group(1).lower()
    if "__horizontal_well" in stem:
        return stem.split("__")[0].lstrip("_")
    return stem


def replace_sentinels_with_nan(df):
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].replace(list(SENTINELS), pd.NA)
    return out


def recommend_log1p(y, *, skew_threshold=1.5):
    y = np.asarray(y, dtype=np.float64)
    finite = y[np.isfinite(y)]
    strict_positive = bool(len(finite) > 0 and np.all(finite > 0))
    m, sd = finite.mean(), finite.std()
    skew = float(np.mean(((finite - m) / sd) ** 3)) if sd > 0 and len(finite) >= 3 else 0.0
    use = strict_positive and skew > skew_threshold
    return {"use_log1p": use, "strict_positive": strict_positive, "skewness": skew}


def load_competition_frames(data_dir):
    data_dir = Path(data_dir).resolve()
    sample_sub = pd.read_csv(data_dir / "sample_submission.csv")
    cols = list(sample_sub.columns)
    id_col, target_col = cols[0], cols[1]

    train_parts, test_parts = [], []
    for p in sorted(data_dir.glob("_train_*horizontal_well.csv")):
        wid = _well_from_stem(p.stem)
        df = pd.read_csv(p)
        df["well_id"], df["is_train"] = wid, True
        train_parts.append(df)
    for p in sorted(data_dir.glob("_test_*horizontal_well.csv")):
        wid = _well_from_stem(p.stem)
        df = pd.read_csv(p)
        df["well_id"], df["is_train"] = wid, False
        test_parts.append(df)

    if not train_parts:
        for sub in ("train", "test"):
            sd = data_dir / sub
            if not sd.is_dir():
                continue
            for p in sorted(sd.glob("*horizontal_well.csv")):
                if p.name.startswith("._"):
                    continue
                wid = _well_from_stem(p.stem)
                df = pd.read_csv(p)
                df["well_id"], df["is_train"] = wid, sub == "train"
                (train_parts if sub == "train" else test_parts).append(df)

    if not train_parts and (data_dir / "train.csv").is_file():
        df = pd.read_csv(data_dir / "train.csv")
        df["well_id"], df["is_train"] = "default", True
        train_parts.append(df)
    if not test_parts and (data_dir / "test.csv").is_file():
        df = pd.read_csv(data_dir / "test.csv")
        df["well_id"], df["is_train"] = "default", False
        test_parts.append(df)

    train_df = pd.concat(train_parts, ignore_index=True)
    test_df = pd.concat(test_parts, ignore_index=True)

    if target_col not in train_df.columns:
        by_lower = {str(c).lower(): c for c in train_df.columns}
        if target_col.lower() in by_lower:
            train_df = train_df.rename(columns={by_lower[target_col.lower()]: target_col})

    if id_col not in test_df.columns:
        test_df[id_col] = test_df["well_id"].astype(str) + "_" + test_df.groupby("well_id").cumcount().astype(str)
    if id_col not in train_df.columns:
        train_df[id_col] = train_df["well_id"].astype(str) + "_" + train_df.groupby("well_id").cumcount().astype(str)

    sample_sub = sample_sub.copy()
    if "well_id" not in sample_sub.columns and "_" in str(sample_sub[id_col].iloc[0]):
        parts = sample_sub[id_col].astype(str).str.split("_", n=1, expand=True)
        sample_sub["well_id"] = parts[0]
        sample_sub["row_idx"] = pd.to_numeric(parts[1], errors="coerce").fillna(0).astype(int)

    return train_df, test_df, sample_sub, id_col, target_col


FORMATION_COLS = ["ANCC", "ASTNU", "ASTNL", "EGFDU", "EGFDL", "BUDA"]

def add_physics_features(df, *, typewell=None):
    out = df.copy()
    sort_keys = ["well_id", "MD"] if "well_id" in out.columns else ["MD"]
    out = out.sort_values(sort_keys).reset_index(drop=True)
    has_well = "well_id" in out.columns
    if "MD" in out.columns:
        if has_well:
            out["md_delta"] = out.groupby("well_id")["MD"].diff().fillna(0.0)
            out["md_pct"] = out.groupby("well_id")["MD"].rank(pct=True)
        else:
            out["md_delta"] = out["MD"].diff().fillna(0.0)
            out["md_pct"] = out["MD"].rank(pct=True)
    if "TVT_input" in out.columns:
        out["tvt_input_abs"] = out["TVT_input"].abs()
        out["tvt_input_slope"] = (out.groupby("well_id")["TVT_input"].diff().fillna(0.0)
                                  if has_well else out["TVT_input"].diff().fillna(0.0))
    if "GR" in out.columns:
        for w in (5, 11, 21):
            if has_well:
                out[f"gr_rmean_{w}"] = out.groupby("well_id")["GR"].transform(
                    lambda s, ww=w: s.rolling(ww, min_periods=1, center=True).mean())
                out[f"gr_rstd_{w}"] = out.groupby("well_id")["GR"].transform(
                    lambda s, ww=w: s.rolling(ww, min_periods=1, center=True).std().fillna(0.0))
            else:
                out[f"gr_rmean_{w}"] = out["GR"].rolling(w, min_periods=1, center=True).mean()
                out[f"gr_rstd_{w}"] = out["GR"].rolling(w, min_periods=1, center=True).std().fillna(0.0)
        if "TVT_input" in out.columns:
            out["gr_over_tvt_input"] = out["GR"] / (out["TVT_input"].abs() + 1e-3)
    present = [c for c in FORMATION_COLS if c in out.columns]
    if present and "TVT_input" in out.columns:
        thick = out[present].sum(axis=1).replace(0, np.nan)
        out["formation_sum"] = thick.fillna(0.0)
        out["formation_over_tvt"] = thick / (out["TVT_input"].abs() + 1e-3)
    return out


def prep_matrix(df, feature_cols):
    X = replace_sentinels_with_nan(df[feature_cols].copy())
    return SimpleImputer(strategy="median").fit_transform(X).astype(np.float32)


def lgbm_frame(X):
    return pd.DataFrame(np.asarray(X, dtype=np.float64),
                        columns=[f"Column_{i}" for i in range(X.shape[1])])


def make_lgb(n, physics=False):
    if not _HAS_LGBM:
        return HistGradientBoostingRegressor(max_depth=10, max_iter=500, learning_rate=0.06, random_state=SEED)
    if physics:
        return lgb.LGBMRegressor(
            objective="regression", metric="rmse", n_estimators=4000, learning_rate=0.03,
            num_leaves=255, min_child_samples=15, subsample=0.8, colsample_bytree=0.8,
            reg_lambda=3.0, reg_alpha=0.05, random_state=SEED, verbose=-1)
    return lgb.LGBMRegressor(
        objective="regression", metric="rmse", n_estimators=2000, learning_rate=0.05,
        num_leaves=63, subsample=0.85, colsample_bytree=0.85, reg_lambda=1.0,
        random_state=SEED, verbose=-1)


def train_tabular(name, trn, tst, y, feat_cols, *, factory, use_log=False):
    groups = trn["well_id"].astype(str).values if "well_id" in trn.columns else None
    n_wells = len(np.unique(groups)) if groups is not None else 1
    if n_wells >= 2:
        splitter = list(GroupKFold(n_splits=min(N_SPLITS, n_wells)).split(trn, groups=groups))
    else:
        splitter = list(KFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED).split(trn))

    oof = np.full(len(trn), np.nan, dtype=np.float64)
    test_folds, fold_rmses = [], []
    X_all = prep_matrix(trn, feat_cols)
    X_test_all = prep_matrix(tst, feat_cols)
    y_train = np.log1p(np.clip(y, 0, None)) if use_log else y

    for tr_idx, va_idx in splitter:
        model = factory(len(tr_idx))
        if _HAS_LGBM and isinstance(model, lgb.LGBMRegressor):
            model.fit(lgbm_frame(X_all[tr_idx]), y_train[tr_idx],
                      eval_set=[(lgbm_frame(X_all[va_idx]), y_train[va_idx])],
                      callbacks=[lgb.early_stopping(50, verbose=False)])
            pv = model.predict(lgbm_frame(X_all[va_idx]))
            pt = model.predict(lgbm_frame(X_test_all))
        else:
            model.fit(X_all[tr_idx], y_train[tr_idx])
            pv = model.predict(X_all[va_idx])
            pt = model.predict(X_test_all)

        if use_log:
            pv = np.clip(np.expm1(np.clip(pv, None, 20.0)), 0, None)
            pt = np.clip(np.expm1(np.clip(pt, None, 20.0)), 0, None)
        oof[va_idx] = pv
        fold_rmses.append(rmse(y[va_idx], pv))
        test_folds.append(pt)

    test_pred = np.mean(np.column_stack(test_folds), axis=1)
    cv = rmse(y, oof)
    print(f"  [{name}] cv_rmse={cv:.4f}  folds={[f'{r:.4f}' for r in fold_rmses]}")
    return oof, test_pred, cv, fold_rmses


def align_test(pred, tst, sub, id_c, fallback):
    te = tst.copy()
    te["_pred"] = np.asarray(pred, dtype=np.float64)[:len(te)]
    te["_row"] = te.groupby("well_id").cumcount()
    lookup = te.set_index(["well_id", "_row"])["_pred"]
    s = sub.copy()
    if "well_id" not in s.columns:
        parts = s[id_c].astype(str).str.split("_", n=1, expand=True)
        s["well_id"], s["row_idx"] = parts[0], pd.to_numeric(parts[1], errors="coerce").fillna(0).astype(int)
    return np.array([float(lookup.get((r["well_id"], r["row_idx"]), fallback)) for _, r in s.iterrows()], dtype=np.float64)


def coordinate_descent_blend(oof_mat, y_true, *, n_iter=400, step=0.02):
    rng = np.random.default_rng(SEED)
    n = oof_mat.shape[1]
    w = np.ones(n) / n
    best = rmse(y_true, oof_mat @ w)
    for _ in range(n_iter):
        improved = False
        for j in range(n):
            for d in (-step, step):
                trial = w.copy()
                trial[j] = max(0.0, trial[j] + d)
                s = trial.sum()
                trial = trial / s if s > 0 else np.ones(n) / n
                sc = rmse(y_true, oof_mat @ trial)
                if sc < best - 1e-9:
                    best, w = sc, trial
                    improved = True
        if not improved:
            jitter = rng.dirichlet(np.ones(n))
            sc = rmse(y_true, oof_mat @ jitter)
            if sc < best:
                best, w = sc, jitter
    return w, best


def main():
    ap = argparse.ArgumentParser(description="ROGII trace baseline pipeline")
    ap.add_argument("--data-dir", type=Path, default=Path("/lustre/work/sweeden/rogii/data"))
    ap.add_argument("--out-dir", type=Path, default=Path("./output"))
    ap.add_argument("--rmse-gate", type=float, default=12.0)
    ap.add_argument("--skip-tcn", action="store_true")
    args = ap.parse_args()

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = out_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    # ── Load data ──
    print("Loading competition data...")
    train_df, test_df, sample_sub, id_col, target_col = load_competition_frames(args.data_dir)
    train_target = "TVT" if "TVT" in train_df.columns else target_col
    y_raw = train_df[train_target].astype(np.float64).values
    log_rec = recommend_log1p(y_raw)
    use_log1p = log_rec["use_log1p"]
    print(f"train={train_df.shape} test={test_df.shape} target={train_target} log1p={use_log1p}")

    # ── Physics features ──
    typewells = {}
    for p in Path(args.data_dir).resolve().glob("*__typewell.csv"):
        if not p.name.startswith("._"):
            typewells[p.stem.replace("__typewell", "").lstrip("_")] = pd.read_csv(p)
    tw = next(iter(typewells.values()), None)
    train_phys = add_physics_features(train_df, typewell=tw)
    test_phys = add_physics_features(test_df, typewell=tw)

    base_exclude = {train_target, "well_id", "is_train", id_col}
    baseline_cols = [c for c in train_df.columns
                     if c in test_df.columns and c not in base_exclude
                     and pd.api.types.is_numeric_dtype(train_df[c])]
    phys_cols = baseline_cols + [c for c in train_phys.columns
                                 if c not in base_exclude and c not in baseline_cols
                                 and c in test_phys.columns
                                 and pd.api.types.is_numeric_dtype(train_phys[c])
                                 and c.startswith(("gr_", "tvt_", "md_", "formation_"))]

    # ── Tabular baseline ──
    print("\n=== lgb_physics ===")
    oof_phys, test_phys_pred, cv_phys, folds_phys = train_tabular(
        "lgb_physics", train_phys, test_phys, y_raw, phys_cols,
        factory=lambda n: make_lgb(n, physics=True), use_log=use_log1p)

    print("\n=== lgb_baseline ===")
    oof_base, test_base_pred, cv_base, folds_base = train_tabular(
        "lgb_baseline", train_df, test_df, y_raw, baseline_cols,
        factory=lambda n: make_lgb(n, physics=False), use_log=use_log1p)

    if cv_phys <= cv_base:
        best_name, best_cv, best_folds = "lgb_physics", cv_phys, folds_phys
    else:
        best_name, best_cv, best_folds = "lgb_baseline", cv_base, folds_base
    cumulative = sum(best_folds)
    print(f"\nBest tabular: {best_name}  cv={best_cv:.4f}  cumulative={cumulative:.4f}")

    # ── RMSE Gate ──
    gate = args.rmse_gate
    gate_pass = cumulative <= gate or best_cv <= gate
    run_tcn = not gate_pass and not args.skip_tcn
    print(f"Gate ({gate}ft): pass={gate_pass}  run_tcn={run_tcn}")

    # ── Ensemble ──
    fallback = float(y_raw.mean())
    test_phys_a = align_test(test_phys_pred, test_phys, sample_sub, id_col, fallback)
    test_base_a = align_test(test_base_pred, test_df, sample_sub, id_col, fallback)

    names = ["lgb_physics", "lgb_baseline"]
    oof_parts = [oof_phys, oof_base]
    test_parts = [test_phys_a, test_base_a]

    oof_mat = np.column_stack(oof_parts)
    test_mat = np.column_stack(test_parts)
    mask = np.all(np.isfinite(oof_mat), axis=1) & np.isfinite(y_raw)

    ridge = Ridge(alpha=0.5, positive=True, fit_intercept=True)
    ridge.fit(oof_mat[mask], y_raw[mask])
    ridge_test = ridge.predict(test_mat)
    ridge_cv = rmse(y_raw, ridge.predict(oof_mat))

    weights, blend_cv = coordinate_descent_blend(oof_mat[mask], y_raw[mask])
    blend_test = test_mat @ weights

    if ridge_cv < blend_cv:
        final_test, final_method, final_cv = ridge_test, "ridge", ridge_cv
    else:
        final_test, final_method, final_cv = blend_test, "blend", blend_cv
    print(f"Ensemble: {final_method}  cv={final_cv:.4f}  weights={dict(zip(names, weights.round(4)))}")

    # Savgol
    try:
        from scipy.signal import savgol_filter
        if "well_id" in sample_sub.columns:
            smoothed = final_test.copy()
            for wid in sample_sub["well_id"].unique():
                idx = np.where(sample_sub["well_id"] == wid)[0]
                seg = final_test[idx]
                w = min(17, max(5, len(seg) - (1 - len(seg) % 2)))
                if w % 2 == 0:
                    w += 1
                if len(seg) >= w:
                    smoothed[idx] = savgol_filter(seg, w, 3, mode="interp")
            final_test = smoothed
    except ImportError:
        pass

    # ── Submission ──
    submission = pd.DataFrame({id_col: sample_sub[id_col], target_col: final_test})[[id_col, target_col]]
    sub_path = out_dir / "submission.csv"
    submission.to_csv(sub_path, index=False)
    print(f"\nWrote {sub_path} ({len(submission)} rows)")

    metrics = {
        "cv_rmse": final_cv,
        "cumulative_rmse_feet": cumulative,
        "tabular_cv_rmse": best_cv,
        "best_tabular_agent": best_name,
        "ensemble_method": final_method,
        "ensemble_cv_rmse": final_cv,
        "ensemble_weights": dict(zip(names, [float(w) for w in weights])),
        "use_log1p": use_log1p,
        "n_agents": len(names),
        "gate_passed": gate_pass,
        "tcn_ran": False,
        "n_train_rows": len(train_df),
        "n_test_rows": len(test_df),
        "n_submission_rows": len(submission),
    }
    (out_dir / "pipeline_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"Wrote pipeline_metrics.json")
    print(f"\ncv_rmse={final_cv:.4f}  cumulative_rmse_feet={cumulative:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
