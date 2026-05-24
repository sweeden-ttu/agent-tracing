# Variants reference

All six preprocessing ablations share the same six-phase skeleton and `_shared/phase_runner_core.py`. Differences are encoded in `VariantHooks` and the linked base papers.

## Comparison table

| Variant | Worktree | Slurm tag | Hook flags | Extra features (typical) | Base paper(s) |
|---------|----------|-----------|------------|--------------------------|---------------|
| `baseline_column_transformer` | `agent-tracing-trace-baseline` | `trace_baseline` | defaults | none | Ke 2017 LightGBM, Pedregosa 2011 sklearn |
| `typewell_gr_alignment` | `agent-tracing-trace-typewell` | `trace_typewell` | `typewell_align=True`, PCHIP | `gr_typewell_diff`, `estimated_tvt`, `dtw_path_cost`, … | Sakoe & Chiba 1978 DTW |
| `ps_point_leakage_aware` | `agent-tracing-trace-ps` | `trace_ps` | `eval_mask=post_ps_only` | none (mask only) | Kaufman et al. 2012 leakage |
| `robust_scale_log1p` | `agent-tracing-trace-robust` | `trace_robust` | `force_log1p`, `numeric_scaler=robust` | none (transform only) | Hampel 1986 / Pedregosa RobustScaler |
| `parallel_multiwell_loader` | `agent-tracing-trace-parallel` | `trace_parallel` | `parallel_workers=8` | geology surface cols if present | Rocklin 2015 Dask |
| `formation_plane_spatial` | `agent-tracing-trace-formation` | `trace_formation` | `formation_knn=True`, k=5 | `md_delta`, `formation_knn_propagated`, … | Cover & Hart 1967 k-NN |

## Per-variant detail

### baseline_column_transformer

- **Branch:** `trace/baseline-column-transformer`
- **Approach:** Standard tabular pipeline — median imputation on numerics, LightGBM regressor.
- **Merge order:** First among six variants (see `MERGE_PATH.md` in unified repo).
- **Key files:** `experiment_descriptor.json`, `ablation_plan.json`, full phase artifacts in trace-baseline worktree.

### typewell_gr_alignment

- **Module:** `rogii/pipeline/typewell_alignment.py`
- **Algorithm:** Band-constrained beam search aligns horizontal GR to typewell GR/TVT curve; optional PCHIP interpolation on typewell.
- **Phase 01 metadata:** `typewell_align: on`, interpolator name in `variant_scaffold.json`.
- **Typewell CSV:** Discovered via `find_typewell_path(data_dir, train_df)`.

### ps_point_leakage_aware

- **Module:** `rogii/pipeline/leakage_masks.py`
- **Behavior:** Detects first NaN in `TVT_input` per well (perforation start). Phase 04 CV uses `val_row_mask=post_ps_mask(train_df)` so fold RMSE matches competition scoring horizon.
- **Note:** Lower CV RMSE vs baseline is expected when masking pre-PS rows.

### robust_scale_log1p

- **Module:** `rogii/pipeline/robust_preprocess.py`
- **Behavior:** `VariantHooks.build_numeric_transformer()` returns RobustScaler pipeline; target always log1p-transformed; inverse at predict via `expm1`.
- **feature_config.json:** `"numeric_scaler": "robust"`.

### parallel_multiwell_loader

- **Module:** `rogii/pipeline/parallel_loader.py`
- **Behavior:** Phase 01 may parallel-load `*__horizontal.csv` via `ProcessPoolExecutor`; attaches geology surface features when files exist.
- **Scaffold:** `variant_scaffold.json` records `parallel_loader` metadata (workers, elapsed, backend).

### formation_plane_spatial

- **Module:** `rogii/pipeline/formation_spatial.py`
- **Behavior:** Drilling geometry deltas (`md_delta`, `tvd_delta`, …), formation thickness sums, k-NN propagation of `formation_code` in MD/TVD space.
- **Test set:** Formation thickness columns may be absent on test CSV; module zero-fills test thickness before k-NN.

## Variant directory contents

Each `traces/preprocessing/{variant}/` includes:

| File / dir | Purpose |
|------------|---------|
| `trace_language.csv` | Full agent trace specification |
| `trace_row_index.csv` | Row index with phase/paper tags |
| `experiment_descriptor.json` | Papers, claims, trace theory link |
| `ablation_plan.json` | Factorial ablation grid |
| `environment.yml` | Per-variant conda spec (name = slug) |
| `artifacts/01..06/` | Phase outputs + `PHASE_CONTRACT.json` |
| `notebooks/` | `phase_runner.py`, phase notebooks |
| `run_pipeline.sh` | Login-node PaperBench dry-run gate |

## Registering a new variant

1. Add slug to `variant_hooks.py` `_REGISTRY`
2. Implement pipeline module under `rogii/pipeline/` if needed
3. Scaffold: `python examples/rogii/scripts/scaffold_trace_variant.py --variant SLUG --sync-worktrees`
4. Add entry to `frontier.yaml` `rogii_pipeline.variants`
5. Re-run `generate_rogii_pipelines.py --all`
