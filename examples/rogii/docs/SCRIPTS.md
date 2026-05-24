# Scripts reference

## `examples/rogii/scripts/`

| Script | Purpose |
|--------|---------|
| `scaffold_trace_variant.py` | Create phase dirs, contracts, notebooks; `--sync-worktrees` |
| `download_variant_papers.py` | Fetch variant base PDFs; `--verify-only` |
| `download_layer_papers.py` | Fetch leaderboard ensemble layer PDFs |
| `write_trace_row_index.py` | Generate `trace_row_index.csv` from trace CSV |
| `run_paperbench_rogii_gate.py` | PaperBench pytest + validate + orchestrator dry-run |

### scaffold_trace_variant.py

```bash
python examples/rogii/scripts/scaffold_trace_variant.py --all-variants --sync-worktrees
python examples/rogii/scripts/scaffold_trace_variant.py --variant formation_plane_spatial --phases-only
```

Worktree mapping (internal `WORKTREE_BY_VARIANT`):

| Variant | Worktree repo folder |
|---------|---------------------|
| baseline | `agent-tracing-trace-baseline` |
| typewell | `agent-tracing-trace-typewell` |
| ps | `agent-tracing-trace-ps` |
| robust | `agent-tracing-trace-robust` |
| parallel | `agent-tracing-trace-parallel` |
| formation | `agent-tracing-trace-formation` |

### run_paperbench_rogii_gate.py

```bash
python examples/rogii/scripts/run_paperbench_rogii_gate.py
python examples/rogii/scripts/run_paperbench_rogii_gate.py --write-descriptors --sync-papers --generate-pipelines
python examples/rogii/scripts/run_paperbench_rogii_gate.py --no-dry-run-all --execute-orchestrator typewell_gr_alignment
```

Flags: `--validate-traces` / `--no-validate-traces`, `--dry-run-all` / `--no-dry-run-all`, `--skip-pytest`, `--generate-pipelines`.

## `examples/rogii/hpcc/`

| File | Purpose |
|------|---------|
| `submit_trace_pipeline.sh` | Chain sbatch phases 01–06 with dependencies |
| `run_trace_phase.slurm` | Single-phase Slurm job template |
| `run_trace_phase.py` | CLI entry: `--variant`, `--phase`, `--agent-tracing-root` |
| `verify_phase_handoff.py` | `--preboot`, `--review-chain` |
| `_trace_phase_common.sh` | Module load, conda, preboot (sourced by .slurm) |
| `_trace_phase_env.sh` | `trace_phase_activate_env()` |
| `ensure_trace_slurm_env.sh` | Create `rogii-trace-slurm` conda env on login node |

## `examples/rogii/generated/` (auto-generated)

Produced by `paperbench.scripts.generate_rogii_pipelines`:

| File | Purpose |
|------|---------|
| `submit_baseline.sh` … `submit_formation.sh` | Per-variant submit with correct `AGENT_TRACING_ROOT` |
| `submit_all_variants.sh` | Loop all variants; `--submit` for real sbatch |

## frontier-evals scripts

| Path | Purpose |
|------|---------|
| `scripts/generate_rogii_worktree_pipelines.sh` | Wrapper: `uv run generate_rogii_pipelines --all` |
| `scripts/ci_validate_trace_pipeline.sh` | Pytest + validate + 6 dry-runs |
| `paperbench/scripts/generate_rogii_pipelines.py` | Read `frontier.yaml`, symlink hpcc, write manifest |
| `paperbench/scripts/sync_rogii_papers.py` | Symlink PDFs into PaperBench `data/rogii/papers` |
| `paperbench/scripts/write_experiment_descriptors.py` | Write `experiment_descriptor.json` + mirrors |
| `paperbench/scripts/implement_agent_tracing.py` | `--validate-traces` Chomsky gate |

## Tests

```bash
python -m pytest examples/rogii/tests/test_variant_hooks.py -q
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run pytest tests/unit/trace_pipeline/test_frontier_config.py tests/unit/trace_pipeline/test_paper_registry.py -q
```
