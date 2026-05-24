#!/usr/bin/env python3
"""Emit trace_row_index.csv: trace row → agent → phase → paper → train_predict.py.

Usage::

    python examples/rogii/scripts/write_trace_row_index.py
    python examples/rogii/scripts/write_trace_row_index.py --variant baseline_column_transformer
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACES = REPO_ROOT / "traces" / "preprocessing"

LANE_TO_PHASE: dict[str, str] = {
    "data_downloader": "01_data_analysis",
    "schema-sentinel": "01_data_analysis",
    "eda_profiler": "01_data_analysis",
    "well_group_detector": "01_data_analysis",
    "target_diagnostician": "01_data_analysis",
    "experiment-design-architect": "02_statistical_framework",
    "architecture-decision-recorder": "02_statistical_framework",
    "seed-control-officer": "02_statistical_framework",
    "dependency-graph-orchestrator": "02_statistical_framework",
    "feature_engineer": "03_feature_engineering",
    "preprocessor": "03_feature_engineering",
    "cv_orchestrator": "03_feature_engineering",
    "model_trainer": "04_model_training",
    "model_ensembler": "04_model_training",
    "predictor": "04_model_training",
    "oof_evaluator": "05_evaluation",
    "error_analyzer": "05_evaluation",
    "submission_formatter": "06_submission",
    "submission_validator": "06_submission",
    "kaggle_submitter": "06_submission",
}

GOVERNANCE_TOKENS = {
    "pin_seed",
    "design_factorial_and_episodic_training",
    "record_initial_adr",
    "add_task",
    "add_dep",
    "topological_order",
    "dispatch",
    "bind_producers_to_type3_consumers",
    "declare_envelope",
}

META_COLS = {
    "chomsky_type",
    "llm_model",
    "context_window_tokens",
    "context_policy",
    "long_term_memory",
    "ltm_growth_bound",
    "slurm_partition",
    "slurm_resources",
    "gpu_device",
}

PEDREGOSA_TOKENS = {
    "build_numeric_pipeline",
    "build_lowcard_pipeline",
    "build_highcard_pipeline",
    "assemble_column_transformer",
    "replace_sentinels_with_nan",
    "choose_cv_scheme",
    "instantiate_groupkfold",
    "emit_fold_indices",
    "provide_groups",
    "subdivide_train_by_well",
    "subdivide_train_by_depth_bin",
    "nested_groupkfold_emit_fold_indices",
    "register_schema",
    "load_sample_submission",
    "infer_id_column",
    "infer_target_columns",
}

KE_TOKENS = {
    "set_objective_regression",
    "set_metric_rmse",
    "log_best_iteration",
    "train_with_seed_42",
    "train_with_seed_69",
    "train_with_seed_2024",
    "average_seed_predictions",
    "collect_oof_predictions",
    "compute_rmse_per_fold",
    "compute_mean_oof_rmse",
    "report_std_across_folds",
}

TRAIN_PREDICT_MAP: dict[str, str] = {
    "register_schema": "infer_columns (+ SchemaSentinel.register_schema in agents.py)",
    "load_sample_submission": "infer_columns",
    "infer_id_column": "infer_columns",
    "infer_target_columns": "infer_columns",
    "detect_multi_target": "infer_columns (single-target check in main)",
    "check_dataframe": "SchemaSentinel.check_dataframe (agents.py)",
    "recommend_log1p": "recommend_log1p (import pipeline.target_diagnostician)",
    "replace_sentinels_with_nan": "replace_sentinels_with_nan (import pipeline.preprocessor)",
    "build_numeric_pipeline": "categorize_columns + build_feature_matrix",
    "build_lowcard_pipeline": "categorize_columns + build_feature_matrix",
    "build_highcard_pipeline": "categorize_columns + build_feature_matrix",
    "assemble_column_transformer": "build_feature_matrix",
    "scan_for_well_columns": "well_group_detector.recommend_group_key",
    "count_unique_groups": "well_group_detector.count_unique_groups",
    "recommend_group_key": "well_group_detector.recommend_group_key",
    "provide_groups": "well_group_detector.provide_groups",
    "choose_cv_scheme": "choose_cv_scheme via _effective_cv",
    "instantiate_groupkfold": "_effective_cv",
    "emit_fold_indices": "emit_fold_indices via cross_val_and_predict",
    "set_objective_regression": "make_estimator (LGBMRegressor.objective)",
    "set_metric_rmse": "make_estimator + rmse",
    "log_best_iteration": "cross_val_and_predict (lgb.early_stopping)",
    "train_with_seed_42": "make_estimator.random_state=42; cross_val_and_predict",
    "train_with_seed_69": "— (multi-seed; trace only; train_predict uses seed 42)",
    "train_with_seed_2024": "— (multi-seed; trace only)",
    "average_seed_predictions": "— (multi-seed; trace only)",
    "collect_oof_predictions": "cross_val_and_predict (oof_fit)",
    "compute_rmse_per_fold": "cross_val_and_predict + rmse",
    "compute_mean_oof_rmse": "cross_val_and_predict",
    "report_std_across_folds": "cross_val_and_predict (fold_rmses std)",
    "inverse_log1p": "cross_val_and_predict + main (np.expm1 on test_pred)",
    "load_fold_models": "cross_val_and_predict (per-fold est)",
    "predict_per_fold": "cross_val_and_predict",
    "average_test_predictions": "main (test_mat.mean(axis=1))",
    "align_to_sample_submission_columns": "main (out_df column filter)",
    "set_id_column": "main (DataFrame id_col)",
    "set_prediction_columns": "main (DataFrame target col)",
    "assert_no_nans": "SubmissionEnvelopeValidator._no_nans (agents.py)",
    "assert_columns_match_sample": "SubmissionEnvelopeValidator._columns_match",
    "assert_row_count_matches_test": "SubmissionEnvelopeValidator._row_count_matches",
    "align_train_target_to_schema": "align_train_target_to_schema",
    "load_experiment_descriptor": "— (ExperimentDesignArchitect; not train_predict.py)",
    "cite_base_paper_ablations": "— (ExperimentDesignArchitect)",
    "write_mle_plan_json": "— (ExperimentDesignArchitect)",
    "define_statistical_framework": "— (ExperimentDesignArchitect)",
    "design_ablation_factorial_grid": "— (ExperimentDesignArchitect)",
    "configure_variant_ablation_flags": "— (ExperimentDesignArchitect)",
    "record_ablation_plan": "— (ExperimentDesignArchitect / ADRRecorder)",
    "pin_seed": "SeedControlOfficer.pin_seed (agents.py; train_tcn.py)",
    "design_factorial_and_episodic_training": "ExperimentDesignArchitect.design_factorial_and_episodic_training",
    "record_initial_adr": "ADRRecorder.record_initial_adr",
    "add_task": "DependencyGraphOrchestrator.add_node",
    "add_dep": "DependencyGraphOrchestrator.add_node",
    "topological_order": "DependencyGraphOrchestrator",
    "dispatch": "DependencyGraphOrchestrator",
    "bind_producers_to_type3_consumers": "Type3ConsumerGate (trace_executor)",
}

DUAL_PAPER_TOKENS = {
    "recommend_log1p",
    "load_experiment_descriptor",
    "cite_base_paper_ablations",
    "design_ablation_factorial_grid",
}


def _phase(lane: str, token: str) -> str:
    if token in GOVERNANCE_TOKENS and token != "declare_envelope":
        return "02_statistical_framework"
    return LANE_TO_PHASE.get(lane, "06_submission")


def _paper(lane: str, token: str) -> str:
    if token.startswith("type3_consumer"):
        return "agent-tracing (Type-3 audit)"
    if token == "declare_envelope":
        return "agent-tracing (resource envelope)"
    if token in DUAL_PAPER_TOKENS:
        return "ke2017_lightgbm; pedregosa2011_sklearn"
    if token in PEDREGOSA_TOKENS or lane in ("preprocessor", "cv_orchestrator"):
        if token.startswith("cd ") or "sbatch" in token:
            return "— (infrastructure)"
        return "pedregosa2011_sklearn"
    if token in KE_TOKENS or token.startswith("train_with_seed"):
        return "ke2017_lightgbm"
    if lane in ("model_trainer", "model_ensembler") and token not in GOVERNANCE_TOKENS:
        if "sbatch" in token or token.startswith("cd ") or "training_review" in token:
            return "— (infrastructure / TCN Slurm)"
        if token in ("load_episode_checkpoints", "select_best_episode_by_oof_rmse"):
            return "— (episodic TCN; not Ke/Pedregosa)"
        return "ke2017_lightgbm"
    if lane == "oof_evaluator":
        return "ke2017_lightgbm"
    if lane in (
        "experiment-design-architect",
        "architecture-decision-recorder",
        "dependency-graph-orchestrator",
        "seed-control-officer",
    ):
        return "agent-tracing (experiment design)"
    if token.startswith("cd ") or token.startswith("kaggle") or "sbatch" in token:
        return "— (infrastructure)"
    if lane == "data_downloader":
        return "— (competition data IO)"
    if lane in ("submission_formatter", "submission_validator", "kaggle_submitter"):
        return "— (submission envelope)"
    if lane in ("eda_profiler", "error_analyzer", "feature_engineer"):
        return "— (competition shared / EDA)"
    return "—"


def _train_predict(lane: str, token: str) -> str:
    if token.startswith("type3_consumer"):
        return "Type3ConsumerGate (agents.py) / trace_executor.execute_step"
    if token == "declare_envelope":
        return "—"
    if token in TRAIN_PREDICT_MAP:
        return TRAIN_PREDICT_MAP[token]
    if token.startswith("train_with_seed"):
        return "— (multi-seed extension; baseline train_predict.py uses random_state=42)"
    if token.startswith("cd ") or "sbatch" in token or token.startswith("kaggle"):
        return "— (shell; not in train_predict.py)"
    if lane == "feature_engineer":
        return "— (rolling/lag tokens not in baseline train_predict.py)"
    if lane == "eda_profiler":
        return "— (EDA only)"
    if lane == "target_diagnostician":
        return TRAIN_PREDICT_MAP.get(token, "— (diagnostics only)")
    if lane == "predictor" and token == "generate_sample_submission_from_checkpoint":
        return "— (checkpoint path; train_predict.py writes submission in main)"
    if lane == "model_trainer" and "train_tcn" in token:
        return "train_tcn.py (TCN; not train_predict.py)"
    if lane == "error_analyzer":
        return "— (analysis / review scripts)"
    return "—"


def build_index(trace_csv: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with trace_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        lanes = [c for c in (reader.fieldnames or []) if c not in META_COLS]
        for row_num, row in enumerate(reader, start=2):
            for lane in lanes:
                token = (row.get(lane) or "").strip()
                if not token:
                    continue
                rows.append(
                    {
                        "trace_row": str(row_num),
                        "agent": lane,
                        "token": token,
                        "phase": _phase(lane, token),
                        "paper": _paper(lane, token),
                        "train_predict_py": _train_predict(lane, token),
                    }
                )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Write trace_row_index.csv for a Rogii variant")
    ap.add_argument("--variant", default="baseline_column_transformer")
    ap.add_argument(
        "--trace-csv",
        type=Path,
        default=None,
        help="Override path to trace_language.csv",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV (default: beside trace_language.csv)",
    )
    args = ap.parse_args()

    variant_dir = TRACES / args.variant
    trace_csv = args.trace_csv or (variant_dir / "trace_language.csv")
    out = args.out or (variant_dir / "trace_row_index.csv")

    if not trace_csv.is_file():
        raise SystemExit(f"trace CSV not found: {trace_csv}")

    rows = build_index(trace_csv)
    fieldnames = ["trace_row", "agent", "token", "phase", "paper", "train_predict_py"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
