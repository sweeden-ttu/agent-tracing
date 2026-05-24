# Rogii trace pipeline documentation

Documentation for the six preprocessing-variant ML pipelines on the [Rogii Wellbore Geology Prediction](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction) Kaggle task, wired to agent-tracing trace languages and PaperBench (frontier-evals).

## Table of contents

| Document | Description |
|----------|-------------|
| [GLOSSARY.md](GLOSSARY.md) | Definitions of domain, trace-language, and ML terms |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Repositories, worktrees, and data flow |
| [VARIANTS.md](VARIANTS.md) | All six variants: papers, hooks, branches, worktrees |
| [PIPELINE_PHASES.md](PIPELINE_PHASES.md) | Phases 01–06, artifacts, handoff contracts |
| [ML_MODULES.md](ML_MODULES.md) | `/lustre/work/sweeden/rogii/pipeline/` module reference |
| [SHARED_CODE.md](SHARED_CODE.md) | `_shared/` phase runner, variant hooks, notebooks |
| [SCRIPTS.md](SCRIPTS.md) | Login-node and generator scripts |
| [SLURM_AND_WORKTREES.md](SLURM_AND_WORKTREES.md) | HPCC execution, job naming, submit wrappers |
| [PAPERBENCH.md](PAPERBENCH.md) | frontier-evals / PaperBench integration |
| [ARTIFACTS.md](ARTIFACTS.md) | JSON/CSV outputs per phase |
| [PAPERS.md](PAPERS.md) | Base-paper PDF library and downloads |
| [KAGGLE_NOTEBOOK.md](KAGGLE_NOTEBOOK.md) | Unified Kaggle kernel, synthetic RMSE smoke, push/run |
| [PAPER_ALIGNMENT.md](PAPER_ALIGNMENT.md) | Variant ↔ base-paper implementation alignment |

## Quick start

```bash
# Validate traces (login node)
python examples/rogii/scripts/run_paperbench_rogii_gate.py

# Generate Slurm submit wrappers from frontier.yaml
bash /lustre/work/sweeden/frontier-evals/scripts/generate_rogii_worktree_pipelines.sh

# Submit one variant (Slurm only — one active job per variant)
bash examples/rogii/generated/submit_baseline.sh

# Submit all six (skips variants with active jobs)
bash examples/rogii/generated/submit_all_variants.sh --submit
```

## Repository map

| Path | Role |
|------|------|
| `examples/rogii/traces/preprocessing/` | Six variant trace bundles + `_shared/` |
| `examples/rogii/hpcc/` | Slurm phase scripts (`run_trace_phase.slurm`, submit chain) |
| `examples/rogii/scripts/` | Paper download, scaffolding, PaperBench gate |
| `examples/rogii/papers/` | Variant and layer PDF library |
| `examples/rogii/generated/` | Auto-generated submit wrappers (`frontier.yaml`) |
| `examples/rogii/tests/` | Variant hook unit tests |
| `/lustre/work/sweeden/rogii/` | Live Kaggle repo: data, `train_predict.py`, `pipeline/` |
| `/lustre/work/sweeden/frontier-evals/` | PaperBench, Chomsky validator, orchestrator |

## Six variants at a glance

| Slug | Branch | Worktree | Base idea |
|------|--------|----------|-----------|
| `baseline_column_transformer` | `trace/baseline-column-transformer` | `agent-tracing-trace-baseline` | ColumnTransformer + LightGBM |
| `typewell_gr_alignment` | `trace/typewell-gr-alignment` | `agent-tracing-trace-typewell` | DTW / typewell GR alignment |
| `ps_point_leakage_aware` | `trace/ps-point-leakage-aware` | `agent-tracing-trace-ps` | Post-PS CV mask |
| `robust_scale_log1p` | `trace/robust-scale-log1p` | `agent-tracing-trace-robust` | RobustScaler + log1p |
| `parallel_multiwell_loader` | `trace/parallel-multiwell-loader` | `agent-tracing-trace-parallel` | Parallel multi-CSV IO |
| `formation_plane_spatial` | `trace/formation-plane-spatial` | `agent-tracing-trace-formation` | Formation k-NN spatial features |

Canonical unified traces: `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/`.

## Related docs outside this folder

- [`../papers/README.md`](../papers/README.md) — PDF download status
- [`../BASE_PAPERS.md`](../BASE_PAPERS.md) — full paper catalog
- [`../traces/preprocessing/README.md`](../traces/preprocessing/README.md) — variant folder overview
- [`/lustre/work/sweeden/frontier-evals/frontier.yaml`](../../../frontier-evals/frontier.yaml) — `rogii_pipeline` worktree config
