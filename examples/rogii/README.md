# Rogii trace language experiments

Six preprocessing/modeling approaches for [rogii-wellbore-geology-prediction](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction), each driven by a `trace_language.csv` swim-lane pipeline.

| Variant | Branch | Paper sections |
|---------|--------|----------------|
| `baseline_column_transformer` | `trace/baseline-column-transformer` | sec/2 schemata, sec/4 eval |
| `typewell_gr_alignment` | `trace/typewell-gr-alignment` | sec/3 Type-2 stack, sec/7 R&D |
| `ps_point_leakage_aware` | `trace/ps-point-leakage-aware` | sec/4 audit, sec/5 limitations |
| `robust_scale_log1p` | `trace/robust-scale-log1p` | sec/3 Type-1 linear transcript |
| `parallel_multiwell_loader` | `trace/parallel-multiwell-loader` | sec/7 Bayesian loop |
| `formation_plane_spatial` | `trace/formation-plane-spatial` | sec/3 Type-0 envelope |

Validation (from frontier-evals):

```bash
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
uv run python -m paperbench.trace_pipeline.orchestrator --variant baseline_column_transformer --dry-run
```

Miniforge env: `mamba activate kc-rogii-wellbore-geology-prediction` (see `/lustre/work/sweeden/rogii/environment.yml`).
