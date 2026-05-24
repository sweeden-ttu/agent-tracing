# Rogii trace merge path

Variants merge into `main` in dependency order. **Baseline is first** — it establishes the shared pipeline tail (CV → train → submit) that other branches extend.

| Order | Branch | Variant | Base paper | PR |
|-------|--------|---------|------------|-----|
| 1 | `trace/baseline-column-transformer` | `baseline_column_transformer` | Ke et al. 2017 LightGBM + Pedregosa et al. 2011 scikit-learn ColumnTransformer | #17 |
| 2 | `trace/typewell-gr-alignment` | `typewell_gr_alignment` | Sakoe & Chiba 1978 DTW | #18 |
| 3 | `trace/ps-point-leakage-aware` | `ps_point_leakage_aware` | Kaufman et al. 2012 leakage | #19 |
| 4 | `trace/robust-scale-log1p` | `robust_scale_log1p` | Hampel et al. 1986 robust stats | #20 |
| 5 | `trace/parallel-multiwell-loader` | `parallel_multiwell_loader` | Rocklin 2015 Dask | #21 |
| 6 | `trace/formation-plane-spatial` | `formation_plane_spatial` | Cover & Hart 1967 k-NN | #22 |

## Merge baseline into main

```bash
cd /lustre/work/sweeden/agent-tracing
git checkout main
git merge trace/baseline-column-transformer -m "Merge trace/baseline-column-transformer (Ke 2017 LightGBM + Pedregosa 2011 ColumnTransformer) into main"
git push origin main
```

After merge, `main` contains:

- `examples/rogii/traces/preprocessing/baseline_column_transformer/` — trace + `experiment_descriptor.json` + ablation plan
- Shared `examples/rogii/README.md` and ablation tracking matrix

## Ablation execution (all six)

```bash
cd /lustre/work/sweeden/rogii
python scripts/run_ablation_suite.py --all-variants --init
# Slurm (one job per variant):
for v in baseline_column_transformer typewell_gr_alignment ps_point_leakage_aware \
         robust_scale_log1p parallel_multiwell_loader formation_plane_spatial; do
  VARIANT=$v sbatch hpcc/run_ablation_variant.slurm
done
```

Ablation manifests: `rogii/ablation_runs/{variant}/manifest.json`
