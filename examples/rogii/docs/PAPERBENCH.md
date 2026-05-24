# PaperBench integration

Rogii trace variants integrate with [PaperBench](https://github.com/openai/frontier-evals) under `/lustre/work/sweeden/frontier-evals/project/paperbench`.

## Key components

| Component | Path |
|-----------|------|
| Orchestrator | `paperbench.trace_pipeline.orchestrator` |
| Chomsky validator | `paperbench.scripts.implement_agent_tracing --validate-traces` |
| Paper registry | `paperbench/trace_pipeline/paper_registry.py` |
| Frontier config | `paperbench/trace_pipeline/frontier_config.py` |
| Trace solver | `paperbench/solvers/trace_pipeline/solver.py` (`TracePipelineSolver`) |
| Agent-tracing paper | `data/papers/agent-tracing/` |

## frontier.yaml wiring

```yaml
integration:
  datasets:
    rogii_traces: .../agent-tracing-trace-baseline/examples/rogii/traces/preprocessing
    rogii_papers: .../agent-tracing-trace-baseline/examples/rogii/papers

rogii_pipeline:
  variants: [... six slugs with worktree + slurm_job_tag ...]
```

## Login-node gate

```bash
python examples/rogii/scripts/run_paperbench_rogii_gate.py --write-descriptors --sync-papers
```

Steps:

1. Optional: sync PDFs → `data/rogii/papers/`
2. Write `experiment_descriptor.json` for all variants
3. Pytest chomsky + trace_pipeline units
4. `--validate-traces` (Type-0 envelope check)
5. Orchestrator `--dry-run` for each variant

## Orchestrator CLI

```bash
cd /lustre/work/sweeden/frontier-evals/project/paperbench
ROGII_ROOT=/lustre/work/sweeden/agent-tracing-trace-baseline \
  uv run python -m paperbench.trace_pipeline.orchestrator \
  --variant typewell_gr_alignment --dry-run
```

`--execute` runs real training (Slurm-only per project rules).

## CI script

```bash
bash /lustre/work/sweeden/frontier-evals/scripts/ci_validate_trace_pipeline.sh
```

## Paper split

PaperBench eval config supports `paper_split=trace_variants` for the six Rogii preprocessing pipelines.

## SWE-Lancer

Not used for Rogii — SWE-Lancer covers Expensify freelance SWE tasks. Wellbore ML reproduction lives entirely in PaperBench + agent-tracing traces.

## Bundled data

After sync:

- `data/rogii/papers/` — symlinked PDFs
- `data/rogii/traces/preprocessing/` — trace copies (when mirrored)
- `data/rogii/pipeline_manifest.json` — generated pipeline registry
