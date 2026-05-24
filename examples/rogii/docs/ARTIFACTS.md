# Artifacts reference

All paths relative to `traces/preprocessing/{variant}/`.

## Global state

| File | Description |
|------|-------------|
| `artifacts/pipeline_state.json` | Last completed phase, timestamps |
| `artifacts/{phase}/PHASE_CONTRACT.json` | Expected outputs before phase runs (scaffold) |
| `artifacts/{phase}/phase_manifest.json` | Actual outputs after phase completes |

## Phase manifests

Each `phase_manifest.json` contains:

```json
{
  "phase": "04_model_training",
  "variant": "typewell_gr_alignment",
  "completed_at": "2026-05-24T...",
  "outputs": {
    "training_metrics": "artifacts/04_model_training/training_metrics.json",
    ...
  }
}
```

## Key JSON schemas

### feature_config.json (phase 03)

```json
{
  "variant": "...",
  "feature_cols": ["MD", "X", "Y", "Z", "GR", "TVT_input", "..."],
  "numeric_cols": [...],
  "variant_extra_cols": ["gr_typewell_diff", "..."],
  "numeric_scaler": "median|robust",
  "n_train_rows": 5278,
  "n_test_rows": 5278
}
```

### training_metrics.json (phase 04)

```json
{
  "cv_rmse": 0.671,
  "fold_rmse": [...],
  "n_splits": 5
}
```

### metrics.json (phase 05)

OOF RMSE, residual summaries, optional post-PS breakdown.

### validation_report.json (phase 06)

Submission schema validation, row counts, id alignment checks.

## Logs

Slurm stdout/stderr under `{variant}/logs/`:

```
trace_baseline_p04.o24318001
trace_baseline_p04.e24318001
```

## Ablation runs (rogii repo)

Separate from phase artifacts — episodic / TCN path:

```
/lustre/work/sweeden/rogii/ablation_runs/{variant}/
├── manifest.json
├── run_{run_id}.json
└── ...
```

## Tracking CSV

`examples/rogii/ablation_tracking_status.csv` — cross-variant RMSE and scaffold status (refresh via rogii `experiment_design_architect.py --sync-tracking`).
