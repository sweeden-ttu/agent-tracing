# Preprocessing trace variants

Six ablation branches under `examples/rogii/traces/preprocessing/`. **Baseline merges first** — others extend the shared CV → train → submit tail.

**Documentation:** [`../../docs/README.md`](../../docs/README.md) · [`../../docs/GLOSSARY.md`](../../docs/GLOSSARY.md) · [`../../docs/VARIANTS.md`](../../docs/VARIANTS.md)

| Variant | Branch | Status in this worktree |
|---------|--------|-------------------------|
| `baseline_column_transformer` | `trace/baseline-column-transformer` | Phases 01–02 committed; 03–06 scaffolded |
| `typewell_gr_alignment` | `trace/typewell-gr-alignment` | Scaffolded (specs from canonical repo) |
| `ps_point_leakage_aware` | `trace/ps-point-leakage-aware` | Scaffolded |
| `robust_scale_log1p` | `trace/robust-scale-log1p` | Scaffolded |
| `parallel_multiwell_loader` | `trace/parallel-multiwell-loader` | Scaffolded |
| `formation_plane_spatial` | `trace/formation-plane-spatial` | Scaffolded |

## Run baseline phases

```bash
cd examples/rogii/traces/preprocessing/baseline_column_transformer/notebooks
python -c "from phase_runner import run_03_feature_engineering; run_03_feature_engineering()"
```

Each phase writes `artifacts/<phase>/phase_manifest.json` when complete. Pending phases have `PHASE_CONTRACT.json` describing required outputs.

## Tracking

[`../../ablation_tracking_status.csv`](../../ablation_tracking_status.csv) — refresh per variant with `experiment_design_architect.py --sync-tracking` from the rogii repo.
