# Pipeline phases (01–06)

Shared phase order defined in `_shared/phase_runner_core.py` (`PHASE_ORDER`). Each phase writes `phase_manifest.json` and declared outputs under `artifacts/{phase}/`.

## Phase chain

```
01_data_analysis
    ↓
02_statistical_framework
    ↓
03_feature_engineering
    ↓
04_model_training
    ↓
05_evaluation
    ↓
06_submission
```

## Phase 01 — data analysis

**Runner:** `run_01_data_analysis()`

| Output | Description |
|--------|-------------|
| `schema.json` | Column dtypes, row counts |
| `data_paths.json` | Train/test CSV paths |
| `well_groups.json` | Well IDs for GroupKFold |
| `target_diagnosis.json` | Target distribution, sentinel values |
| `eda_summary.json` | Basic EDA stats |
| `variant_scaffold.json` | Variant-specific phase-01 metadata from hooks |

**Variant hooks:** `phase01_extra()` — PS map, typewell flag, parallel loader stats, robust scaler tag.

**Parallel variant:** May call `parallel_read_multiwell_csvs()` in phase 01 when loading multiple horizontal CSVs.

## Phase 02 — statistical framework

**Runner:** `run_02_statistical_framework()`

| Output | Description |
|--------|-------------|
| `statistical_framework.json` | Hypothesis, CV plan, metric |
| `ablation_grid.json` | Factorial cells |
| `training_plan.json` | Model family, seeds, row limits |
| `paper_citations.json` | Base paper IDs from descriptor |
| `initial_adr.md` | Architecture decision record |
| `*_snapshot.json` | Copies of mle_plan, ablation_plan, experiment_descriptor |

Uses `HOOKS.phase02_rationale` for variant-specific statistical narrative.

## Phase 03 — feature engineering

**Runner:** `run_03_feature_engineering()`

| Output | Description |
|--------|-------------|
| `feature_config.json` | Feature columns, scaler, `variant_extra_cols` |
| `cv_config.json` | n_splits, grouping column |
| `fold_indices.json` | Per-fold train/val indices |
| `subdivision_by_well.json` | Optional well subdivisions |
| `subdivision_by_depth.json` | Optional depth bins |

**Variant hooks:** `augment_train_test()` — typewell, formation, parallel surface features.

## Phase 04 — model training

**Runner:** `run_04_model_training()`

| Output | Description |
|--------|-------------|
| `transform.json` | Serialized preprocessor metadata |
| `training_metrics.json` | `cv_rmse`, fold scores |
| `oof_predictions.npy` | Out-of-fold train predictions |
| `test_preds_per_fold.npy` | Test predictions per fold |

**Training:** LightGBM via `rogii/train_predict.py` → `cross_val_and_predict()`.

**PS variant:** Passes `val_row_mask=HOOKS.eval_mask_indices(train_df)` to restrict CV to post-PS rows.

**Slurm:** Longest phase — default 4h walltime, 100G RAM (`submit_trace_pipeline.sh`).

## Phase 05 — evaluation

**Runner:** `run_05_evaluation()`

| Output | Description |
|--------|-------------|
| `metrics.json` | OOF RMSE, fold breakdown |
| `residuals.csv` | Per-row residuals |
| `residuals_by_depth.json` | Binned residual stats |

## Phase 06 — submission

**Runner:** `run_06_submission()`

| Output | Description |
|--------|-------------|
| `submission.csv` | Kaggle-format `id,tvt` |
| `validation_report.json` | Schema checks, row count |

Aligns ensemble of fold test predictions to `sample_submission.csv` column order.

## Handoff validation

```bash
python examples/rogii/hpcc/verify_phase_handoff.py \
  --variant baseline_column_transformer \
  --agent-tracing-root /lustre/work/sweeden/agent-tracing-trace-baseline \
  --review-chain
```

Slurm jobs call `--preboot` for the target phase before execution.

## Resume from mid-phase

If phases 01–N completed, submit with:

```bash
VARIANT=typewell_gr_alignment START_PHASE=03_feature_engineering \
  bash examples/rogii/hpcc/submit_trace_pipeline.sh
```

See `.cursor/rules/trace-language-mid-resume-slurm-gate.mdc` for sacct and artifact gates.
