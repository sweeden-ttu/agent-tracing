# Architecture

## System overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  frontier-evals (PaperBench + Chomsky)                                  │
│  frontier.yaml → generate_rogii_pipelines.py → pipeline_manifest.json   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ validate-traces, orchestrator --dry-run
┌───────────────────────────────▼─────────────────────────────────────────┐
│  agent-tracing* worktrees (6 variants + unified agent-tracing)          │
│  trace_language.csv  →  phase_runner  →  artifacts/01..06               │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ Slurm run_trace_phase.slurm
┌───────────────────────────────▼─────────────────────────────────────────┐
│  /lustre/work/sweeden/rogii (Kaggle repo)                               │
│  data/  train_predict.py  pipeline/{typewell,leakage,...}               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Layer responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Trace spec** | `traces/preprocessing/{variant}/trace_language.csv` | Agent swim lanes, Slurm envelopes, Type-3 bounds |
| **Shared runner** | `traces/preprocessing/_shared/` | Phase logic, variant hooks dispatch |
| **ML implementation** | `/lustre/work/sweeden/rogii/pipeline/` | Variant-specific feature engineering |
| **Training** | `/lustre/work/sweeden/rogii/train_predict.py` | LightGBM CV, predict, optional `val_row_mask` |
| **Slurm** | `examples/rogii/hpcc/` | Matador GPU jobs, conda env, handoff preboot |
| **Verification** | `frontier-evals/.../implement_agent_tracing` | Chomsky Type-0 CSV validation |

## Worktree layout

Dedicated worktrees (from `frontier.yaml#rogii_pipeline`):

```
/lustre/work/sweeden/
├── agent-tracing-trace-baseline/     # baseline + all six variant folders
├── agent-tracing-trace-typewell/     # typewell_gr_alignment only
├── agent-tracing-trace-ps/         # ps_point_leakage_aware
├── agent-tracing-trace-robust/     # robust_scale_log1p
├── agent-tracing-trace-parallel/   # parallel_multiwell_loader
├── agent-tracing-trace-formation/  # formation_plane_spatial
└── agent-tracing/                  # unified canonical traces (all variants)
```

Each worktree symlinks `examples/rogii/hpcc/` to trace-baseline and syncs `_shared/` from baseline.

## Execution paths

**Login node (allowed):**

- Chomsky `--validate-traces`
- Orchestrator `--dry-run`
- Unit tests (`examples/rogii/tests/`)
- Pipeline generation from `frontier.yaml`

**Slurm / matador (required for training):**

- `submit_trace_pipeline.sh` chains phases 01–06
- One active job chain per variant (six max across project)
- Conda env: `/lustre/work/sweeden/sweeden/envs/rogii-trace-slurm`

## Data flow (phase 03 → 06)

1. Load train/test CSVs from `ROGII_ROOT/data/`
2. `VariantHooks.augment_train_test()` adds variant columns
3. Build ColumnTransformer + LightGBM pipeline
4. GroupKFold CV; PS variant passes `val_row_mask` into `cross_val_and_predict`
5. Write metrics, OOF, test fold preds
6. Align predictions to `sample_submission.csv` schema in phase 06
