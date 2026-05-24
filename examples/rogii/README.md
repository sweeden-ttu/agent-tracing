# Rogii trace language experiments

Six preprocessing/modeling approaches for [rogii-wellbore-geology-prediction](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction). Each variant is defined by a **two-layer descriptor**:

1. **Scientific base paper** — primary citation for the ablation / experiment design (`experiment_descriptor.json` → `base_paper`; human summary in `paper_refs.md`).
2. **Agent implementation** — swim-lane execution trace (`trace_language.csv`) audited against the trace-theory paper (PaperBench bundle `agent-tracing`).

| Variant | Branch | Base paper (method) | Trace theory sections |
|---------|--------|---------------------|------------------------|
| `baseline_column_transformer` | `trace/baseline-column-transformer` | Ke et al. 2017 LightGBM + Pedregosa et al. 2011 ColumnTransformer | sec/2 schemata, sec/4 eval |
| `typewell_gr_alignment` | `trace/typewell-gr-alignment` | Sakoe & Chiba 1978 DTW alignment | sec/3 Type-2, sec/7 R&D |
| `ps_point_leakage_aware` | `trace/ps-point-leakage-aware` | Kaufman et al. 2012 leakage | sec/4 audit, sec/5 limits |
| `robust_scale_log1p` | `trace/robust-scale-log1p` | Hampel et al. 1986 robust stats | sec/3 Type-1 transcript |
| `parallel_multiwell_loader` | `trace/parallel-multiwell-loader` | Rocklin 2015 Dask parallel IO | sec/7 Bayesian loop |
| `formation_plane_spatial` | `trace/formation-plane-spatial` | Cover & Hart 1967 k-NN spatial | sec/3 Type-0 envelope |

**Base papers (PDFs + links):** [`BASE_PAPERS.md`](BASE_PAPERS.md) — six variant primaries (+ Pedregosa co-primary for baseline); open-access PDFs in [`papers/`](papers/).

**Full documentation:** [`docs/README.md`](docs/README.md) — table of contents, [glossary](docs/GLOSSARY.md), architecture, variants, phases, ML modules, Slurm, PaperBench.

Per-variant artifacts under `traces/preprocessing/{variant}/`:

| File | Role |
|------|------|
| `experiment_descriptor.json` | Machine-readable join: base paper + ablation + `trace_language.csv` path |
| `paper_refs.md` | Human-readable citations and claim→ablation mapping |
| `trace_language.csv` | Agent swim-lane implementation (29-column schema) |
| `ablation_plan.json` | Factorial grid derived from base-paper claims |
| `subdivision_manifest.json` | Train-data fold indices (`paperbench.trace_pipeline.subdivision`) |

**Ablation tracking:** [`ablation_tracking_status.csv`](ablation_tracking_status.csv) — refresh with `python scripts/experiment_design_architect.py --variant <slug> --sync-tracking` from rogii.

Write / refresh experiment descriptors:

```bash
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.scripts.write_experiment_descriptors --all-variants
```

Validation (from frontier-evals):

```bash
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.scripts.enrich_resource_envelopes examples/rogii/traces/preprocessing/<variant>/trace_language.csv
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
uv run python -m paperbench.trace_pipeline.orchestrator --variant baseline_column_transformer --dry-run
cd /lustre/work/sweeden/rogii && python scripts/evaluate_computing_resources.py --trace traces/preprocessing/<variant>/trace_language.csv -q
```

Each trace CSV uses a **29-column header**: 20 swim lanes plus nine resource-envelope columns (`chomsky_type`, `llm_model`, `context_window_tokens`, `context_policy`, `long_term_memory`, `ltm_growth_bound`, `slurm_partition`, `slurm_resources`, `gpu_device`). Rows 2–21 declare per-agent envelopes; the pre-submit review block includes Chomsky computing-resources evaluation tokens.

Miniforge env: `mamba activate kc-rogii-wellbore-geology-prediction` (see `/lustre/work/sweeden/rogii/environment.yml`).
