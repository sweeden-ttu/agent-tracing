# Current Status and Next Steps — Agent Tracing / Rogii Trace Experiments

**Repository:** https://github.com/sweeden-ttu/agent-tracing  
**GitHub Project:** [trace_language_experiments (#13)](https://github.com/users/sweeden-ttu/projects/13)  
**Last updated:** May 24, 2026 (evening)  
**Active branch:** `trace/base` — synced with `origin/trace/base` @ [`310f4ee`](https://github.com/sweeden-ttu/agent-tracing/commit/310f4ee)  
**Umbrella PR:** [#16](https://github.com/sweeden-ttu/agent-tracing/pull/16) · variant PRs [#17–#22](https://github.com/sweeden-ttu/agent-tracing/pulls)

---

## Executive summary

All six Rogii trace variants are **95% scaffolded** and **committed on `trace/base`**. PaperBench descriptors, ablation manifests, Slurm consumer-review gates, per-pipeline conda envs, and **six open-access base-paper PDFs** are in the repo. The remaining gap is **full GPU Slurm pipeline execution** (`slurm_full_pipeline=not_started` on every variant).

| Area | Status |
|------|--------|
| Six variant trace bundles on GitHub | ✅ Done — [`examples/rogii/`](examples/rogii/) on `trace/base` |
| Experiment descriptors + dual base papers (baseline) | ✅ Done |
| Subdivision manifests | ✅ Done |
| Ablation run manifests (`rogii/ablation_runs/`) | ✅ Initialized (rogii repo, local) |
| Base scientific papers (PDFs + links) | ✅ Done — [`BASE_PAPERS.md`](examples/rogii/BASE_PAPERS.md) (6 PDFs + 1 DOI-only) |
| Slurm Ollama consumer review rule + script | ✅ Done |
| Per-pipeline conda `environment.yml` (×6) | ✅ Done |
| HPCC Slurm scripts (module load + conda + Ollama) | ✅ All 5 scripts consumer PASS |
| Cursor agent rules (Slurm pipeline + consumer review) | ✅ Done — [`.cursor/rules/`](.cursor/rules/) |
| Rogii artifacts pushed to remote | ✅ Done on `trace/base` (commits through `310f4ee`) |
| Baseline merge to `main` | ⚠️ PR #17 open; local FF merge in `agent-tracing-main` not pushed |
| Matador Slurm jobs submitted | ⚠️ 2 pending (`24317863` enrich, `24317864` vague_spec) — awaiting resources |
| Full ablation / training pipeline per variant | ❌ Not started |
| Conda envs created on compute nodes | ❌ Not verified on Matador |

---

## Recent commits (`trace/base`)

| Commit | Summary |
|--------|---------|
| [`310f4ee`](https://github.com/sweeden-ttu/agent-tracing/commit/310f4ee) | Open-access base paper PDFs under `examples/rogii/papers/` |
| [`0762c0b`](https://github.com/sweeden-ttu/agent-tracing/commit/0762c0b) | `BASE_PAPERS.md`, `papers/manifest.json` |
| [`8802fa9`](https://github.com/sweeden-ttu/agent-tracing/commit/8802fa9) | Rogii trace bundles, Slurm rules, conda envs, llm_review |
| [`085c8a2`](https://github.com/sweeden-ttu/agent-tracing/commit/085c8a2) | Prior status doc refresh |

---

## Agent accomplishments (May 23–24, 2026)

### PaperBench / experiment design (`frontier-evals`)

- **`paperbench/trace_pipeline/experiment_descriptor.py`** — variant base papers; baseline has co-equal `base_papers[]` (Ke 2017 LightGBM + Pedregosa 2011 ColumnTransformer); branch + `github_pr: "17"` metadata.
- **`paperbench/trace_pipeline/subdivision.py`** — train-data fold subdivision; manifests per variant.
- **`write_experiment_descriptors.py`**, **`write_subdivision_manifests.py`** — batch writers.
- **Unit tests:** `test_experiment_descriptor.py`, `test_subdivision.py` (passing locally).

### Agent-tracing repo (`examples/rogii/`)

- **Six variant directories** under `traces/preprocessing/{variant}/` with enriched `trace_language.csv` (29 cols), `experiment_descriptor.json`, `paper_refs.md`, `ablation_plan.json`, `subdivision_manifest.json`, `mle_plan.json`.
- **`ablation_tracking_status.csv`** — all six variants at **95% / partial** (`slurm_full_pipeline=not_started`).
- **`MERGE_PATH.md`** — merge order baseline → formation; PR mapping #17–#22.
- **`BASE_PAPERS.md`** + **`papers/`** — Ke, Pedregosa, Sakoe–Chiba, Kaufman, Rocklin, Cover–Hart PDFs; Hampel 1986 DOI link only.
- **`docs/llm_review/`** — sectioned critical reviews of trace-theory paper (`llm.txt`).
- **Per-pipeline `environment.yml`** (conda-forge; env name = variant slug).

### Rogii HPCC (`/lustre/work/sweeden/rogii/`)

- **`hpcc/review_slurm_before_submit.sh`** — Type-3 consumer: log triage, `module load gcc/cuda/python`, per-variant conda, Ollama localhost, interactive preflight markers.
- **`hpcc/load_matador_modules.sh`**, **`hpcc/_variant_conda_env.sh`**, **`hpcc/_matador_ollama_env.sh`** — shared Matador setup.
- **Slurm scripts (all consumer PASS):** `run_ablation_variant.slurm`, `train_tcn.slurm`, `train_tcn_episodic.slurm`, `vague_spec_batch_matador.slurm`, `enrich_readme_matador.slurm`.
- **`scripts/run_ablation_suite.py`**, **`scripts/paper_implementation_reviewer.py`** — ablation init + paper compliance audit.
- **Ablation manifests** under `ablation_runs/{variant}/` (12/8/8/8/12/12 runs per variant).

### Cursor agent rules

- **`.cursor/rules/slurm-ollama-consumer-review.mdc`** — mandatory pre-`sbatch` review (TTU Ollama guide, interactive preflight, log triage).
- **`.cursor/rules/slurm-pipeline-execution.mdc`** — one active job per variant; cross-links consumer review.

### Git / worktrees

| Path | Branch | Notes |
|------|--------|-------|
| `agent-tracing` | `trace/base` | Clean; synced with origin |
| `agent-tracing-main` | `main` | Local FF merge of baseline (not pushed) |
| `agent-tracing-trace-{baseline,…}` | per variant | Six worktrees for PR #17–#22 |

---

## Six-variant tracking matrix

| Variant | Issue | PR | Branch | Overall | Blocker |
|---------|-------|-----|--------|---------|---------|
| baseline_column_transformer | [#10](https://github.com/sweeden-ttu/agent-tracing/issues/10) | [#17](https://github.com/sweeden-ttu/agent-tracing/pull/17) | trace/baseline-column-transformer | 95% | `slurm_full_pipeline` |
| typewell_gr_alignment | [#11](https://github.com/sweeden-ttu/agent-tracing/issues/11) | [#18](https://github.com/sweeden-ttu/agent-tracing/pull/18) | trace/typewell-gr-alignment | 95% | `slurm_full_pipeline` |
| ps_point_leakage_aware | [#12](https://github.com/sweeden-ttu/agent-tracing/issues/12) | [#19](https://github.com/sweeden-ttu/agent-tracing/pull/19) | trace/ps-point-leakage-aware | 95% | `slurm_full_pipeline` |
| robust_scale_log1p | [#13](https://github.com/sweeden-ttu/agent-tracing/issues/13) | [#20](https://github.com/sweeden-ttu/agent-tracing/pull/20) | trace/robust-scale-log1p | 95% | `slurm_full_pipeline` |
| parallel_multiwell_loader | [#14](https://github.com/sweeden-ttu/agent-tracing/issues/14) | [#21](https://github.com/sweeden-ttu/agent-tracing/pull/21) | trace/parallel-multiwell-loader | 95% | `slurm_full_pipeline` |
| formation_plane_spatial | [#15](https://github.com/sweeden-ttu/agent-tracing/issues/15) | [#22](https://github.com/sweeden-ttu/agent-tracing/pull/22) | trace/formation-plane-spatial | 95% | `slurm_full_pipeline` |

Detail: [`examples/rogii/ablation_tracking_status.csv`](examples/rogii/ablation_tracking_status.csv)

---

## GitHub project board (#13) — May 24 snapshot

| Status | Item |
|--------|------|
| **Done** | [#4](https://github.com/sweeden-ttu/agent-tracing/issues/4) Resource envelope columns |
| **Done** | [#5](https://github.com/sweeden-ttu/agent-tracing/issues/5) Commit Rogii trace artifacts → `trace/base` pushed |
| **In Progress** | [#6](https://github.com/sweeden-ttu/agent-tracing/issues/6) typewell_aligner / ps_detector swim lanes |
| **In Progress** | [#8](https://github.com/sweeden-ttu/agent-tracing/issues/8) Link traces to automata paper sections |
| **In Progress** | [#9](https://github.com/sweeden-ttu/agent-tracing/issues/9) Episodic training + Kaggle publish |
| **In Progress** | [#10–#15](https://github.com/sweeden-ttu/agent-tracing/issues/10) Full MLE pipeline (×6) @ 95% |
| **Todo** | [#7](https://github.com/sweeden-ttu/agent-tracing/issues/7) CI rubric validation |

Project readme: [base papers + status links](https://github.com/users/sweeden-ttu/projects/13)

---

## Matador queue (last checked May 24)

| Job ID | Name | State | Script |
|--------|------|-------|--------|
| 24317863 | rogii_enr | PD (Resources) | `hpcc/enrich_readme_matador.slurm` |
| 24317864 | rogii_vag | PD (Resources) | `hpcc/vague_spec_batch_matador.slurm` |

No variant ablation jobs (`run_ablation_variant.slurm`) submitted yet.

---

## Next steps (priority order)

### 1. Review and merge PRs

- Review umbrella [#16](https://github.com/sweeden-ttu/agent-tracing/pull/16) and baseline [#17](https://github.com/sweeden-ttu/agent-tracing/pull/17) first.
- Follow merge order in [`examples/rogii/MERGE_PATH.md`](examples/rogii/MERGE_PATH.md) (#17 → #18 → … → #22).

### 2. Interactive preflight + variant ablation Slurm (one job per variant)

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

After each successful run, set `slurm_full_pipeline=done` in [`ablation_tracking_status.csv`](examples/rogii/ablation_tracking_status.csv).

### 3. Create per-pipeline conda envs on Matador (first interactive session)

```bash
for v in baseline_column_transformer typewell_gr_alignment ps_point_leakage_aware \
         robust_scale_log1p parallel_multiwell_loader formation_plane_spatial; do
  mamba env create -f /lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/$v/environment.yml -y
done
```

### 4. Remaining engineering

- Triage `logs/rogii_vague_spec.e24259983` before next vague_spec retry.
- Add `CONSUMER_REVIEW: YYYY-MM-DD` headers to Slurm scripts after interactive preflight.
- Automate trace CSV rubric validation in CI ([#7](https://github.com/sweeden-ttu/agent-tracing/issues/7)).
- Push `frontier-evals` descriptor/subdivision changes to its remote.
- Close variant issues #10–#15 when `slurm_full_pipeline` completes and SMRE/checkpoints land.

---

## Key references

| Resource | Link |
|----------|------|
| Base papers catalog | [`examples/rogii/BASE_PAPERS.md`](examples/rogii/BASE_PAPERS.md) |
| Rogii experiment README | [`examples/rogii/README.md`](examples/rogii/README.md) |
| TTU Ollama on Matador | https://www.depts.ttu.edu/hpcc/userguides/application_guides/ollama.php |
| Umbrella PR | https://github.com/sweeden-ttu/agent-tracing/pull/16 |
| GitHub project #13 | https://github.com/users/sweeden-ttu/projects/13 |
