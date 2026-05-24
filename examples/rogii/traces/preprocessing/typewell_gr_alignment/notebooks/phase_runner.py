"""Phase notebook runner: artifact handoffs for baseline_column_transformer.

Each phase reads ``artifacts/<prior_phase>/phase_manifest.json`` and writes
outputs under ``artifacts/<this_phase>/``.

Regenerate trace index: ``python examples/rogii/scripts/write_trace_row_index.py``
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

VARIANT_DIR = Path(__file__).resolve().parents[1]
ROGII_ROOT = Path("/lustre/work/sweeden/rogii")
ARTIFACTS_ROOT = VARIANT_DIR / "artifacts"
TRACE_INDEX = VARIANT_DIR / "trace_row_index.csv"

PHASE_ORDER = [
    "01_data_analysis",
    "02_statistical_framework",
    "03_feature_engineering",
    "04_model_training",
    "05_evaluation",
    "06_submission",
]

PRIOR_PHASE = {PHASE_ORDER[i]: (PHASE_ORDER[i - 1] if i else None) for i in range(len(PHASE_ORDER))}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_train_predict():
    if str(ROGII_ROOT) not in sys.path:
        sys.path.insert(0, str(ROGII_ROOT))
    import train_predict as tp  # noqa: WPS433

    return tp


def _phase_dir(phase: str) -> Path:
    d = ARTIFACTS_ROOT / phase
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel_path(path: str | Path) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.relative_to(VARIANT_DIR))
    except ValueError:
        return str(path_obj)


def _resolve_path(path: str | Path) -> Path:
    path_obj = Path(path)
    return path_obj if path_obj.is_absolute() else (VARIANT_DIR / path_obj)


def _latest_completed_phase() -> str | None:
    latest = None
    for phase in PHASE_ORDER:
        if (ARTIFACTS_ROOT / phase / "phase_manifest.json").is_file():
            latest = phase
    return latest


def _align_predictions_to_sample_submission(
    sample_sub: pd.DataFrame,
    test_df: pd.DataFrame,
    test_pred: np.ndarray,
    *,
    id_col: str,
    target: str,
    train_target_mean: float,
    well_id: str | None = None,
) -> pd.DataFrame:
    """Map per-row test predictions onto ``sample_submission`` ids (well_row format)."""
    ss = sample_sub.copy()
    if id_col not in ss.columns:
        raise ValueError(f"id column {id_col!r} missing from sample_submission")

    test_n = test_df.copy()
    if len(test_pred) != len(test_n):
        raise ValueError(f"test_pred length {len(test_pred)} != test rows {len(test_n)}")

    if "_well_id" not in test_n.columns:
        test_n["_well_id"] = well_id or _well_from_csv_path_or_df(test_n)
    test_n["_pred"] = test_pred
    test_n["_row_within_well"] = test_n.groupby("_well_id").cumcount()

    ss["_well_id"] = ss[id_col].astype(str).str.split("_").str[0]
    ss["_row_idx"] = ss[id_col].astype(str).str.split("_").str[1].astype(int)

    lookup = test_n.set_index(["_well_id", "_row_within_well"])["_pred"]

    def _lookup(row: pd.Series) -> float:
        try:
            return float(lookup.loc[(row["_well_id"], row["_row_idx"])])
        except KeyError:
            return float(train_target_mean)

    out = pd.DataFrame({
        id_col: ss[id_col],
        target: ss.apply(_lookup, axis=1),
    })
    return out[[c for c in sample_sub.columns if c in out.columns]]


def _well_from_csv_path_or_df(test_df: pd.DataFrame) -> str:
    for col in test_df.columns:
        if str(col).lower() in ("well_id", "well"):
            return test_df[col].astype(str).iloc[0]
    return "000d7d20"


def _well_from_train_path(train_csv: str) -> str:
    import re

    m = re.search(r"_train_([0-9a-f]+)_", Path(train_csv).name)
    return m.group(1) if m else "000d7d20"


def require_prior_phase(phase: str) -> dict | None:
    prior = PRIOR_PHASE[phase]
    if prior is None:
        return None
    manifest = ARTIFACTS_ROOT / prior / "phase_manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(
            f"Missing prior phase artifacts: {manifest}. Run phase {prior} first."
        )
    return _read_json(manifest)


def load_phase_manifest(phase: str) -> dict:
    path = ARTIFACTS_ROOT / phase / "phase_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Phase manifest not found: {path}")
    return _read_json(path)


def trace_steps_for_phase(phase: str) -> list[dict]:
    rows: list[dict] = []
    with TRACE_INDEX.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["phase"] == phase and not row["token"].startswith("type3_consumer"):
                if row["token"] == "declare_envelope":
                    continue
                if row["token"].startswith("cd ") or "sbatch" in row["token"]:
                    continue
                rows.append(row)
    return rows


def finalize_phase(
    phase: str,
    outputs: dict[str, str | Path],
    extra: dict | None = None,
) -> dict:
    prior = PRIOR_PHASE[phase]
    normalized_outputs = {key: _rel_path(value) for key, value in outputs.items()}
    manifest = {
        "variant": "baseline_column_transformer",
        "phase": phase,
        "completed_at": _utc_now(),
        "prior_phase": prior,
        "outputs": normalized_outputs,
        "trace_steps_executed": len(trace_steps_for_phase(phase)),
    }
    if extra:
        manifest.update(extra)
    out_path = _phase_dir(phase) / "phase_manifest.json"
    _write_json(out_path, manifest)
    completed = _latest_completed_phase()
    _write_json(ARTIFACTS_ROOT / "pipeline_state.json", {
        "last_completed_phase": completed if completed else phase,
        "updated_at": _utc_now(),
        "phases": {p: (ARTIFACTS_ROOT / p / "phase_manifest.json").is_file() for p in PHASE_ORDER},
    })
    return manifest


def run_01_data_analysis(*, data_dir: Path | None = None) -> dict:
    """Phase 01: schema, EDA summary, well groups, target log1p diagnosis."""
    tp = _load_train_predict()
    from pipeline.agents import SchemaSentinel
    from pipeline import well_group_detector as wgd
    from pipeline.target_diagnostician import recommend_log1p
    from pipeline.nb_support import ensure_id_column

    data_dir = (data_dir or ROGII_ROOT / "data").resolve()
    out = _phase_dir("01_data_analysis")

    train_path = tp._find_default_csv(data_dir, "train")
    test_path = tp._find_default_csv(data_dir, "test")
    sample_path = tp._find_default_csv(data_dir, "sample_submission")

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    sample_sub = pd.read_csv(sample_path, nrows=0)

    schema_agent = SchemaSentinel()
    schema = schema_agent.register_schema(sample_path)
    id_col = schema["id_column"]
    target_cols = schema["target_columns"]
    target = target_cols[0]

    train_df = tp.align_train_target_to_schema(train_df, target)
    train_df = ensure_id_column(train_df, id_col)
    test_df = ensure_id_column(test_df, id_col)

    group_key = wgd.recommend_group_key(train_df, test_df, id_column=id_col)
    groups = wgd.provide_groups(train_df, group_key, id_column=id_col) if group_key else None
    test_groups = (
        wgd.provide_groups(test_df, group_key, id_column=id_col) if group_key else None
    )

    y_raw = train_df[target].astype(np.float64).values
    log_rec = recommend_log1p(y_raw)

    eda = {
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "train_columns": list(train_df.columns),
        "dtypes": {c: str(train_df[c].dtype) for c in train_df.columns},
        "missingness_rate": {c: float(train_df[c].isna().mean()) for c in train_df.columns},
        "target_summary": {
            "min": float(np.nanmin(y_raw)),
            "max": float(np.nanmax(y_raw)),
            "mean": float(np.nanmean(y_raw)),
            "std": float(np.nanstd(y_raw)),
        },
    }

    _write_json(out / "schema.json", schema)
    _write_json(out / "data_paths.json", {
        "data_dir": str(data_dir),
        "train_csv": str(train_path),
        "test_csv": str(test_path),
        "sample_submission_csv": str(sample_path),
    })
    _write_json(out / "well_groups.json", {
        "group_key": group_key,
        "n_unique_groups": wgd.count_unique_groups(groups) if groups is not None else 0,
        "train_test_overlap": (
            wgd.check_train_test_overlap(groups, test_groups)
            if groups is not None and test_groups is not None
            else {}
        ),
    })
    _write_json(out / "target_diagnosis.json", log_rec)
    _write_json(out / "eda_summary.json", eda)

    return finalize_phase(
        "01_data_analysis",
        {
            "schema": out / "schema.json",
            "data_paths": out / "data_paths.json",
            "well_groups": out / "well_groups.json",
            "target_diagnosis": out / "target_diagnosis.json",
            "eda_summary": out / "eda_summary.json",
        },
        extra={"id_column": id_col, "target_column": target},
    )


def run_02_statistical_framework() -> dict:
    """Phase 02: load experiment descriptor, ablation grid, statistical framework."""
    p01 = require_prior_phase("02_statistical_framework")
    out = _phase_dir("02_statistical_framework")

    sys.path.insert(0, str(ROGII_ROOT))
    from pipeline.agents import ExperimentDesignArchitect, ADRRecorder, SeedControlOfficer

    desc = json.loads((VARIANT_DIR / "experiment_descriptor.json").read_text(encoding="utf-8"))
    abl = json.loads((VARIANT_DIR / "ablation_plan.json").read_text(encoding="utf-8"))
    mle = json.loads((VARIANT_DIR / "mle_plan.json").read_text(encoding="utf-8"))
    well_groups = _read_json(_resolve_path(p01["outputs"]["well_groups"]))
    target_diag = _read_json(_resolve_path(p01["outputs"]["target_diagnosis"]))
    eda_summary = _read_json(_resolve_path(p01["outputs"]["eda_summary"]))

    architect = ExperimentDesignArchitect()
    seed_officer = SeedControlOfficer()
    adr = ADRRecorder()

    seed_officer.pin_seed(42)
    factors = {
        f["id"]: f["levels"]
        for f in abl.get("ablation_factors", [])
        if "id" in f and "levels" in f
    }
    recommended_cv = (
        "nested_groupkfold_by_well" if well_groups.get("group_key") else "kfold"
    )
    recommended_target_transform = "log1p" if target_diag.get("use_log1p") else "none"
    hypothesis = desc["experiment"]["hypothesis"]
    if recommended_cv == "kfold":
        hypothesis = hypothesis.replace("nested GroupKFold", "KFold")
    high_missing_features = [
        col
        for col, rate in eda_summary.get("missingness_rate", {}).items()
        if float(rate) >= 0.40
    ]
    framework = architect.define_statistical_framework(
        hypothesis=hypothesis,
        cv=recommended_cv,
        metric="rmse_post_ps",
        smre=desc["experiment"]["smre"],
    )
    framework["phase01_recommendations"] = {
        "target_log1p": recommended_target_transform,
        "group_key": well_groups.get("group_key"),
        "high_missing_features": high_missing_features,
        "strict_positive_target": bool(
            target_diag.get("strict_positivity", {}).get("strict_positive", False)
        ),
    }
    grid = architect.design_ablation_factorial_grid(factors)
    training_plan = architect.design_factorial_and_episodic_training(factors)
    training_plan["recommended_baseline"] = {
        "target_log1p": recommended_target_transform,
        "cv_scheme": recommended_cv,
    }
    citations = architect.cite_base_paper_ablations(desc)

    _write_json(out / "experiment_descriptor_snapshot.json", desc)
    _write_json(out / "ablation_plan_snapshot.json", abl)
    _write_json(out / "mle_plan_snapshot.json", mle)
    _write_json(out / "statistical_framework.json", framework)
    _write_json(out / "ablation_grid.json", {"n_runs": len(grid), "grid": grid})
    _write_json(out / "training_plan.json", training_plan)
    _write_json(out / "paper_citations.json", citations)
    adr.record_initial_adr(
        rationale=(
            "baseline_column_transformer phase 02 bootstrap; "
            f"cv={recommended_cv}; "
            f"target_log1p={recommended_target_transform}; "
            f"high_missing={','.join(high_missing_features) or 'none'}"
        )
    )
    (out / "initial_adr.md").write_text(adr.serialize_markdown(), encoding="utf-8")

    return finalize_phase(
        "02_statistical_framework",
        {
            "statistical_framework": out / "statistical_framework.json",
            "ablation_grid": out / "ablation_grid.json",
            "training_plan": out / "training_plan.json",
            "paper_citations": out / "paper_citations.json",
            "initial_adr": out / "initial_adr.md",
        },
    )


def run_03_feature_engineering(*, n_splits: int = 5) -> dict:
    """Phase 03: ColumnTransformer config, CV scheme, fold indices."""
    require_prior_phase("03_feature_engineering")
    p01 = load_phase_manifest("01_data_analysis")
    tp = _load_train_predict()
    from pipeline.preprocessor import replace_sentinels_with_nan
    from pipeline import well_group_detector as wgd

    paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
    schema = _read_json(_resolve_path(p01["outputs"]["schema"]))
    id_col = schema["id_column"]
    target = p01["target_column"]

    train_df = pd.read_csv(paths["train_csv"])
    test_df = pd.read_csv(paths["test_csv"])
    train_df = tp.align_train_target_to_schema(train_df, target)

    feature_cols = [c for c in train_df.columns if c not in (id_col, target) and c in test_df.columns]
    X_train = replace_sentinels_with_nan(train_df[feature_cols].copy())
    X_test = replace_sentinels_with_nan(test_df[feature_cols].copy())

    num, low_c, high_c = tp.categorize_columns(
        pd.concat([X_train, X_test], ignore_index=True),
        id_col=id_col,
        target_cols=[target],
    )
    tp.build_feature_matrix(
        X_train, numeric_cols=num, low_card_cols=low_c, high_card_cols=high_c
    )

    scheme, groups, n_eff = tp._effective_cv(
        train_df, test_df, id_col=id_col, n_splits_req=n_splits
    )
    group_key = wgd.recommend_group_key(train_df, test_df, id_column=id_col)

    from pipeline.cv_orchestrator import emit_fold_indices, subdivide_train_by_well, subdivide_train_by_depth_bin

    fold_records: list[dict] = []
    for i, (tr, va) in enumerate(
        emit_fold_indices(
            scheme if scheme == "groupkfold" else "kfold",
            X_train,
            n_splits=n_eff,
            groups=groups,
            shuffle=True,
            random_state=42,
        )
    ):
        fold_records.append({"fold": i, "train_idx": tr.tolist(), "val_idx": va.tolist()})

    out = _phase_dir("03_feature_engineering")
    _write_json(out / "feature_config.json", {
        "feature_cols": feature_cols,
        "numeric_cols": num,
        "low_card_cols": low_c,
        "high_card_cols": high_c,
        "n_train_rows": len(X_train),
        "n_test_rows": len(X_test),
    })
    _write_json(out / "cv_config.json", {
        "scheme": scheme,
        "n_splits": n_eff,
        "group_key": group_key,
        "id_column": id_col,
        "target_column": target,
    })
    _write_json(out / "fold_indices.json", {"folds": fold_records})
    if group_key:
        _write_json(out / "subdivision_by_well.json", subdivide_train_by_well(train_df, group_key, id_column=id_col))
    _write_json(out / "subdivision_by_depth.json", subdivide_train_by_depth_bin(train_df))

    return finalize_phase(
        "03_feature_engineering",
        {
            "feature_config": out / "feature_config.json",
            "cv_config": out / "cv_config.json",
            "fold_indices": out / "fold_indices.json",
        },
    )


def run_04_model_training(*, n_splits: int = 5, max_rows: int | None = None) -> dict:
    """Phase 04: LightGBM cross-val training (login-node; use Slurm for full scale)."""
    require_prior_phase("04_model_training")
    p01 = load_phase_manifest("01_data_analysis")
    p03 = load_phase_manifest("03_feature_engineering")
    tp = _load_train_predict()
    from pipeline.preprocessor import replace_sentinels_with_nan
    from pipeline.nb_support import ensure_id_column

    paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
    target_diag = _read_json(_resolve_path(p01["outputs"]["target_diagnosis"]))
    cv_cfg = _read_json(_resolve_path(p03["outputs"]["cv_config"]))
    feat_cfg = _read_json(_resolve_path(p03["outputs"]["feature_config"]))

    id_col = cv_cfg["id_column"]
    target = cv_cfg["target_column"]

    train_df = pd.read_csv(paths["train_csv"])
    test_df = pd.read_csv(paths["test_csv"])
    if max_rows is not None and len(train_df) > max_rows:
        train_df = train_df.iloc[:max_rows].reset_index(drop=True)

    train_df = tp.align_train_target_to_schema(train_df, target)
    train_df = ensure_id_column(train_df, id_col)
    test_df = ensure_id_column(test_df, id_col)

    y_raw = train_df[target].astype(np.float64).values
    use_log1p = bool(target_diag.get("use_log1p", False))
    is_positive = bool(target_diag.get("strict_positivity", {}).get("strict_positive", False))
    y_fit = np.log1p(np.clip(y_raw, 0, None)) if use_log1p else y_raw

    feature_cols = feat_cfg["feature_cols"]
    X_train = replace_sentinels_with_nan(train_df[feature_cols].copy())
    X_test = replace_sentinels_with_nan(test_df[feature_cols].copy())

    preprocessor = tp.build_feature_matrix(
        X_train,
        numeric_cols=feat_cfg["numeric_cols"],
        low_card_cols=feat_cfg["low_card_cols"],
        high_card_cols=feat_cfg["high_card_cols"],
    )

    scheme = cv_cfg["scheme"]
    groups = None
    if scheme == "groupkfold" and cv_cfg.get("group_key"):
        from pipeline import well_group_detector as wgd

        groups = wgd.provide_groups(train_df, cv_cfg["group_key"], id_column=id_col)
    n_eff = cv_cfg["n_splits"]

    cv_rmse, fold_rmses, test_mat, oof_fit = tp.cross_val_and_predict(
        X_train,
        y_fit,
        y_raw,
        X_test,
        preprocessor,
        scheme=scheme,
        groups=groups,
        n_splits=n_eff,
        use_log1p=use_log1p,
    )

    out = _phase_dir("04_model_training")
    transform = {
        "use_log1p": use_log1p,
        "is_positive": is_positive,
        "target_column": target,
        "id_column": id_col,
        "cv_rmse": cv_rmse,
        "fold_rmses": fold_rmses,
        "cv_scheme": scheme,
        "n_folds": n_eff,
        "group_key": cv_cfg.get("group_key"),
        "n_train_rows": len(train_df),
        "max_rows_applied": max_rows,
        "backend": "lightgbm" if tp._HAS_LGBM else "sklearn.hist_gradient_boosting",
        "feature_config": _rel_path(out.parent / "03_feature_engineering" / "feature_config.json"),
        "paths": paths,
    }
    _write_json(out / "transform.json", transform)
    np.save(out / "test_preds_per_fold.npy", test_mat)
    np.save(out / "oof_predictions.npy", oof_fit)
    _write_json(out / "training_metrics.json", {
        "cv_rmse": cv_rmse,
        "fold_rmses": fold_rmses,
        "mean_fold_rmse": cv_rmse,
        "std_fold_rmse": float(np.std(fold_rmses)) if fold_rmses else None,
    })

    return finalize_phase(
        "04_model_training",
        {
            "transform": out / "transform.json",
            "test_preds_per_fold": out / "test_preds_per_fold.npy",
            "oof_predictions": out / "oof_predictions.npy",
            "training_metrics": out / "training_metrics.json",
        },
        extra={"cv_rmse": cv_rmse},
    )


def run_05_evaluation() -> dict:
    """Phase 05: OOF metrics and residual analysis."""
    require_prior_phase("05_evaluation")
    p01 = load_phase_manifest("01_data_analysis")
    p04 = load_phase_manifest("04_model_training")
    tp = _load_train_predict()

    paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
    transform = _read_json(_resolve_path(p04["outputs"]["transform"]))
    metrics = _read_json(_resolve_path(p04["outputs"]["training_metrics"]))
    oof_fit = np.load(_resolve_path(p04["outputs"]["oof_predictions"]))

    target = transform["target_column"]
    train_df = pd.read_csv(paths["train_csv"])
    train_df = tp.align_train_target_to_schema(train_df, target)
    n_train = int(transform.get("n_train_rows", len(train_df)))
    train_df = train_df.iloc[:n_train].reset_index(drop=True)
    y_true = train_df[target].astype(np.float64).values

    if transform.get("use_log1p"):
        pred_orig = np.expm1(np.clip(oof_fit, None, 20.0))
        pred_orig = np.clip(pred_orig, 0, None)
    else:
        pred_orig = oof_fit

    mask = np.isfinite(oof_fit) & np.isfinite(y_true)
    residuals = y_true[mask] - pred_orig[mask]
    oof_rmse = tp.rmse(y_true[mask], pred_orig[mask])

    out = _phase_dir("05_evaluation")
    eval_metrics = {
        **metrics,
        "oof_rmse_recomputed": oof_rmse,
        "residual_mean": float(np.mean(residuals)),
        "residual_std": float(np.std(residuals)),
        "n_oof_points": int(mask.sum()),
    }
    _write_json(out / "metrics.json", eval_metrics)

    res_df = pd.DataFrame({
        "y_true": y_true[mask],
        "y_pred": pred_orig[mask],
        "residual": residuals,
    })
    res_df.to_csv(out / "residuals.csv", index=False)

    if "MD" in train_df.columns:
        md = train_df.loc[mask, "MD"].values
        by_depth = pd.DataFrame({"MD": md, "abs_residual": np.abs(residuals)})
        depth_summary = (
            by_depth.assign(bin=pd.qcut(by_depth["MD"], q=min(5, len(by_depth)), duplicates="drop"))
            .groupby("bin", observed=True)["abs_residual"]
            .mean()
            .to_dict()
        )
        _write_json(out / "residuals_by_depth.json", {str(k): float(v) for k, v in depth_summary.items()})

    return finalize_phase(
        "05_evaluation",
        {
            "metrics": out / "metrics.json",
            "residuals": out / "residuals.csv",
        },
        extra={"oof_rmse": oof_rmse},
    )


def run_06_submission() -> dict:
    """Phase 06: Build submission.csv and validate envelope."""
    require_prior_phase("06_submission")
    p01 = load_phase_manifest("01_data_analysis")
    p04 = load_phase_manifest("04_model_training")
    tp = _load_train_predict()
    from pipeline.agents import SubmissionEnvelopeValidator

    paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
    schema = _read_json(_resolve_path(p01["outputs"]["schema"]))
    transform = _read_json(_resolve_path(p04["outputs"]["transform"]))
    test_mat = np.load(_resolve_path(p04["outputs"]["test_preds_per_fold"]))

    id_col = schema["id_column"]
    target = transform["target_column"]
    test_df = pd.read_csv(paths["test_csv"])
    sample_sub = pd.read_csv(paths["sample_submission_csv"])
    import re
    m = re.search(r"_test_([0-9a-f]+)_", paths["test_csv"])
    well_id = m.group(1) if m else _well_from_train_path(paths["train_csv"])
    test_df = test_df.copy()
    test_df["_well_id"] = well_id

    test_mean_fit = test_mat.mean(axis=1)
    if transform.get("use_log1p"):
        test_pred = np.expm1(np.clip(test_mean_fit, None, 20.0))
        if transform.get("is_positive"):
            test_pred = np.clip(test_pred, 0, None)
    else:
        test_pred = test_mean_fit
        if transform.get("is_positive"):
            test_pred = np.clip(test_pred, 0, None)

    train_df = pd.read_csv(paths["train_csv"])
    train_df = tp.align_train_target_to_schema(train_df, target)
    n_train = int(transform.get("n_train_rows", len(train_df)))
    fallback = float(train_df[target].iloc[:n_train].mean())

    submission = _align_predictions_to_sample_submission(
        sample_sub,
        test_df,
        test_pred,
        id_col=id_col,
        target=target,
        train_target_mean=fallback,
        well_id=well_id,
    )

    out = _phase_dir("06_submission")
    sub_path = out / "submission.csv"
    submission.to_csv(sub_path, index=False)

    validator = SubmissionEnvelopeValidator(paths["sample_submission_csv"])
    report = validator.validate(submission)
    _write_json(out / "validation_report.json", report)

    if not report.get("ok"):
        raise RuntimeError(f"Submission envelope validation failed: {report}")

    return finalize_phase(
        "06_submission",
        {
            "submission_csv": sub_path,
            "validation_report": out / "validation_report.json",
        },
        extra={"n_rows": len(submission), "columns": list(submission.columns)},
    )


PHASE_RUNNERS = {
    "01_data_analysis": run_01_data_analysis,
    "02_statistical_framework": run_02_statistical_framework,
    "03_feature_engineering": run_03_feature_engineering,
    "04_model_training": run_04_model_training,
    "05_evaluation": run_05_evaluation,
    "06_submission": run_06_submission,
}


def run_phase(phase: str, **kwargs: Any) -> dict:
    if phase not in PHASE_RUNNERS:
        raise ValueError(f"Unknown phase: {phase}")
    return PHASE_RUNNERS[phase](**kwargs)
