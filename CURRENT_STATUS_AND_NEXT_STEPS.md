# Current Status and Next Steps — Agent Tracing / Rogii Trace Experiments

**Repository:** https://github.com/sweeden-ttu/agent-tracing  
**GitHub Project:** [trace_language_experiments (#13)](https://github.com/users/sweeden-ttu/projects/13)  
**Last updated:** May 24, 2026  
**Active branch:** `trace/base` (six variant branches + PRs #16–#22)

---

## Executive summary

The Rogii trace-language experiment program is **~95% scaffolded** across all six preprocessing variants. PaperBench orchestration, experiment descriptors, ablation manifests, Slurm consumer-review gates, and per-pipeline conda environments are in place. **Full GPU Slurm pipeline runs** (`slurm_full_pipeline`) remain the primary blocker to 100% completion.

| Area | Status |
|------|--------|
| Six variant trace bundles | ✅ Done (local on `trace/base`) |
| Experiment descriptors + dual base papers (baseline) | ✅ Done |
| Subdivision manifests | ✅ Done |
| Ablation run manifests (`rogii/ablation_runs/`) | ✅ Initialized |
| Slurm Ollama consumer review rule + script | ✅ Done |
| Per-pipeline conda `environment.yml` (×6) | ✅ Done |
| Base scientific papers (PDFs + links) | ✅ Done — [`BASE_PAPERS.md`](examples/rogii/BASE_PAPERS.md) |
| HPCC Slurm scripts (module load + conda + Ollama) | ✅ Updated; consumer PASS |
| Baseline merge to `main` | ⚠️ Local FF merge; not pushed |
| Full Slurm ablation / training runs | ❌ Not started |
| Rogii artifacts committed to remote | ⚠️ Partial |

---

## Agent accomplishments (May 23–24, 2026)

### PaperBench / experiment design (`frontier-evals`)

- **`paperbench/trace_pipeline/experiment_descriptor.py`** — variant base papers; baseline has co-equal `base_papers[]` (Ke 2017 LightGBM + Pedregosa 2011 ColumnTransformer); branch + `github_pr: "17"` metadata.
- **`paperbench/trace_pipeline/subdivision.py`** — train-data fold subdivision; manifests per variant.
- **`write_experiment_descriptors.py`**, **`write_subdivision_manifests.py`** — batch writers.
- **Unit tests:** `test_experiment_descriptor.py`, `test_subdivision.py` (passing).

### Agent-tracing repo (`examples/rogii/`)

- **Six variant directories** under `traces/preprocessing/{variant}/` with enriched `trace_language.csv` (29 cols), `experiment_descriptor.json`, `paper_refs.md`, `ablation_plan.json`, `subdivision_manifest.json`, `mle_plan.json`.
- **`ablation_tracking_status.csv`** — all six variants at **95% / partial** (`slurm_full_pipeline=not_started`).
- **`MERGE_PATH.md`** — merge order baseline → formation; PR mapping #17–#22.
- **`docs/llm_review/`** — sectioned critical reviews of trace-theory paper (`llm.txt`).
- **Per-pipeline `environment.yml`** (conda-forge; env name = variant slug) for all six pipelines.

### Rogii HPCC (`/lustre/work/sweeden/rogii/`)

- **`hpcc/review_slurm_before_submit.sh`** — Type-3 consumer: log triage, `module load gcc/cuda/python`, per-variant conda, Ollama localhost, interactive preflight markers.
- **`hpcc/load_matador_modules.sh`**, **`hpcc/_variant_conda_env.sh`**, **`hpcc/_matador_ollama_env.sh`** — shared Matador setup.
- **Slurm scripts updated:** `run_ablation_variant.slurm`, `train_tcn.slurm`, `train_tcn_episodic.slurm`, `vague_spec_batch_matador.slurm`, `enrich_readme_matador.slurm` — all pass consumer review.
- **`scripts/run_ablation_suite.py`**, **`scripts/paper_implementation_reviewer.py`** — ablation init + paper compliance audit.
- **Ablation manifests** under `ablation_runs/{variant}/` (12/8/8/8/12/12 runs per variant).

### Cursor agent rules

- **`.cursor/rules/slurm-ollama-consumer-review.mdc`** — mandatory pre-`sbatch` review (TTU Ollama guide, interactive preflight, log triage).
- **`.cursor/rules/slurm-pipeline-execution.mdc`** — one active job per variant; cross-links consumer review.

### Git / worktrees

| Path | Branch | Notes |
|------|--------|-------|
| `agent-tracing` | `trace/base` | Primary; many unstaged Rogii enrichments |
| `agent-tracing-main` | `main` | Local FF merge of baseline branch |
| `agent-tracing-trace-{baseline,…}` | per variant | Six worktrees for isolated PR work |

---

## Six-variant tracking matrix

| Variant | Issue | PR | Branch | Overall | Blocker |
|---------|-------|-----|--------|---------|---------|
| baseline_column_transformer | #10 | #17 | trace/baseline-column-transformer | 95% | `slurm_full_pipeline` |
| typewell_gr_alignment | #11 | #18 | trace/typewell-gr-alignment | 95% | `slurm_full_pipeline` |
| ps_point_leakage_aware | #12 | #19 | trace/ps-point-leakage-aware | 95% | `slurm_full_pipeline` |
| robust_scale_log1p | #13 | #20 | trace/robust-scale-log1p | 95% | `slurm_full_pipeline` |
| parallel_multiwell_loader | #14 | #21 | trace/parallel-multiwell-loader | 95% | `slurm_full_pipeline` |
| formation_plane_spatial | #15 | #22 | trace/formation-plane-spatial | 95% | `slurm_full_pipeline` |

Detail: [`examples/rogii/ablation_tracking_status.csv`](examples/rogii/ablation_tracking_status.csv)

---

## Next steps (priority order)

### 1. Commit and push Rogii trace artifacts

```bash
cd /lustre/work/sweeden/agent-tracing
git checkout trace/base
git add examples/rogii/ .cursor/rules/ docs/llm_review/ CURRENT_STATUS_AND_NEXT_STEPS.md
git commit -m "Rogii trace bundles, Slurm consumer rules, per-pipeline conda envs, status update"
git push origin trace/base
```

Merge baseline PR #17 into `main` after review; follow [`examples/rogii/MERGE_PATH.md`](examples/rogii/MERGE_PATH.md).

### 2. Interactive preflight + Slurm ablation (one job per variant)

```bash
cd /lustre/work/sweeden/rogii
alias interactive='/etc/slurm/scripts/interactive'
# Match #SBATCH resources; run setup through LONG_RUNNING_START, then kill.

for v in baseline_column_transformer typewell_gr_alignment ps_point_leakage_aware \
         robust_scale_log1p parallel_multiwell_loader formation_plane_spatial; do
  bash hpcc/review_slurm_before_submit.sh hpcc/run_ablation_variant.slurm "$v" && \
  VARIANT="$v" sbatch hpcc/run_ablation_variant.slurm
done
```

Training jobs require `VARIANT`:

```bash
VARIANT=baseline_column_transformer sbatch hpcc/train_tcn_episodic.slurm
```

### 3. Create per-pipeline conda envs on Matador (first interactive session)

```bash
for v in baseline_column_transformer typewell_gr_alignment ps_point_leakage_aware \
         robust_scale_log1p parallel_multiwell_loader formation_plane_spatial; do
  mamba env create -f /lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/$v/environment.yml -y
done
```

### 4. Close GitHub project items as work completes

| Issue | Title | Suggested status |
|-------|-------|------------------|
| #4 | Resource envelope columns | **Done** |
| #5 | Commit Rogii trace artifacts | **In Progress** |
| #6 | typewell_aligner / ps_detector swim lanes | **In Progress** |
| #8 | Link traces to automata paper sections | **In Progress** |
| #9 | Episodic training + Kaggle publish | **In Progress** |
| #10–#15 | Full MLE pipeline (×6) | **In Progress** (95%) |
| #7 | CI rubric validation | **Todo** |

### 5. Remaining engineering

- Triage `logs/rogii_vague_spec.e24259983` before next vague_spec batch.
- Add `CONSUMER_REVIEW: YYYY-MM-DD` headers to Slurm scripts after interactive preflight.
- Wire `slurm_full_pipeline=done` in tracking CSV after successful variant runs.
- Automate trace CSV rubric validation in CI (issue #7).
- Push `frontier-evals` descriptor/subdivision changes to its remote.

---

## References

- TTU Ollama on Matador: https://www.depts.ttu.edu/hpcc/userguides/application_guides/ollama.php
- Umbrella tracking issue: https://github.com/sweeden-ttu/agent-tracing/issues/16
- Parent PR (six variants): https://github.com/sweeden-ttu/agent-tracing/pull/16
