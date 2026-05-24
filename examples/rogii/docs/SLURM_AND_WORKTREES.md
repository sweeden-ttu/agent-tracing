# Slurm and worktrees

## Rules (summary)

- ML training and full pipeline execution run on **matador** via **sbatch**, not on login nodes.
- **One active job chain per variant** — max six concurrent variant roots across the project.
- Job names: `trace_{variant}_p{01..06}` (e.g. `trace_typewell_p04`).

## Submit wrappers

Generated under `examples/rogii/generated/` from `frontier.yaml`:

```bash
# Single variant (uses dedicated worktree AGENT_TRACING_ROOT)
bash examples/rogii/generated/submit_typewell.sh

# All variants — dry-run first
bash examples/rogii/generated/submit_all_variants.sh

# All variants — real submit (skips if squeue shows active job for tag)
bash examples/rogii/generated/submit_all_variants.sh --submit
```

Each wrapper exports:

```bash
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-typewell"
export ROGII_ROOT="/lustre/work/sweeden/rogii"
export VARIANT="typewell_gr_alignment"
```

## Manual submit

```bash
cd examples/rogii/traces/preprocessing/baseline_column_transformer
VARIANT=baseline_column_transformer \
AGENT_TRACING_ROOT=/lustre/work/sweeden/agent-tracing-trace-baseline \
  ../../hpcc/submit_trace_pipeline.sh

# Resume from phase 03
START_PHASE=03_feature_engineering VARIANT=formation_plane_spatial \
  bash examples/rogii/generated/submit_formation.sh
```

## Resource envelopes (default)

| Phase | Walltime | Memory |
|-------|----------|--------|
| 01, 02, 05 | 1:00:00 | 32G |
| 03 | 2:00:00 | 64G |
| 04 | 4:00:00 | 100G |
| 06 | 0:30:00 | 16G |

All use `-p matador --gpus-per-node=1`, 8 CPUs.

## Conda environment

Pre-built on login node (never created on compute nodes):

```bash
bash examples/rogii/hpcc/ensure_trace_slurm_env.sh
# → /lustre/work/sweeden/sweeden/envs/rogii-trace-slurm
```

## Monitoring

```bash
squeue -u $USER | grep trace_
sacct -j JOBID --format=JobID,JobName,State,ExitCode,Elapsed -P
tail -f traces/preprocessing/baseline_column_transformer/logs/trace_baseline_p04.oJOBID
```

## Worktree hpcc symlink

Dedicated worktrees symlink shared Slurm scripts:

```
agent-tracing-trace-typewell/examples/rogii/hpcc
  → agent-tracing-trace-baseline/examples/rogii/hpcc
```

Submit wrappers override `AGENT_TRACING_ROOT` so paths resolve to the correct variant checkout.

## frontier.yaml registry

`/lustre/work/sweeden/frontier-evals/frontier.yaml` section `rogii_pipeline` lists all variants, worktrees, branches, and Slurm tags. Regenerate wrappers after edits:

```bash
bash /lustre/work/sweeden/frontier-evals/scripts/generate_rogii_worktree_pipelines.sh
```

Output manifest: `frontier-evals/project/paperbench/data/rogii/pipeline_manifest.json`.
