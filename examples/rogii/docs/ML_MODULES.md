# ML modules (`/lustre/work/sweeden/rogii/pipeline/`)

Python package imported by `_shared/variant_hooks.py` and phase runner. Path injected at runtime via `sys.path`.

## Variant-specific modules

### `typewell_alignment.py`

GR / typewell alignment via band-constrained beam search (DTW-like).

| Function | Description |
|----------|-------------|
| `beam_search_path(gr_h, tw_tvt, tw_gr, start_tvt, ...)` | Returns path TVT, path GR, mean cost |
| `add_typewell_alignment_features(df, typewell_df, ...)` | Adds diff, z-score, residual, `estimated_tvt` columns |
| `find_typewell_path(data_dir, train_df)` | Locates typewell CSV in data directory |

**Extra columns:** `gr_typewell_diff`, `gr_typewell_absdiff`, `gr_typewell_zscore`, `typewell_gr_at_path`, `estimated_tvt`, `typewell_gr_at_tvt`, `gr_tvt_residual`, `dtw_path_cost`

### `leakage_masks.py`

Perforation-start detection and post-PS evaluation masks (Kaufman et al. 2012).

| Function | Description |
|----------|-------------|
| `detect_ps_per_well(df)` | Map well_id → first NaN index in `TVT_input` |
| `post_ps_mask(df)` | Boolean mask for competition-scored rows |

### `robust_preprocess.py`

Target and metadata helpers for robust scaling variant.

| Function | Description |
|----------|-------------|
| `apply_log1p_target(y)` | log1p on non-negative targets |
| `inverse_log1p(y_fit)` | expm1 with clipping |
| `robust_transform_metadata(...)` | JSON-serializable transform config |

### `parallel_loader.py`

Parallel CSV IO and geology surface attachment (Rocklin / Dask pattern).

| Function | Description |
|----------|-------------|
| `parallel_read_multiwell_csvs(data_dir, pattern, n_workers)` | ProcessPoolExecutor multi-file load |
| `attach_geology_surface_features(df, data_dir)` | Merge surface geology columns when available |

### `formation_spatial.py`

Drilling geometry and formation k-NN propagation (Cover & Hart 1967).

| Function | Description |
|----------|-------------|
| `compute_drilling_geometry_features(df)` | `md_delta`, `md_pct_rank`, `{tvd,z,inc,azi}_delta` |
| `encode_formation_codes(df)` | Dominant formation code from thickness columns |
| `fit_formation_plane_knn(train, test, k=5)` | k-NN label propagation in MD/TVD space |
| `add_formation_spatial_features(train, test, k=5)` | Full augmentation entry point |

**Formation columns:** `ANCC`, `ASTNU`, `ASTNL`, `EGFDU`, `EGFDL`, `BUDA`

## Shared / supporting modules

| Module | Role |
|--------|------|
| `competition_data.py` | Rogii CSV loading, schema helpers |
| `preprocessor.py` | Column typing, feature column selection |
| `well_group_detector.py` | Infer well groups for CV |
| `target_diagnostician.py` | Target stats, sentinel detection |
| `cv_orchestrator.py` | Fold orchestration utilities |
| `train_predict` (parent) | `cross_val_and_predict`, LightGBM wiring — not under `pipeline/` but primary training entry |
| `physics_features.py` | Optional physics-derived well features |
| `ensemble_blend.py` | Multi-model blend helpers |
| `temporal_cnn.py` | TCN path (episodic Slurm trace, separate from six phase runner) |
| `agents.py` | Agent-facing pipeline utilities |
| `trace_executor.py` | Trace CSV execution helpers |
| `nb_support.py` | Notebook support utilities |

## Tests

Unit tests in `examples/rogii/tests/test_variant_hooks.py` cover:

- `beam_search_path` finiteness
- Typewell feature augmentation
- PS mask and per-well detection
- Formation spatial (with and without test formation columns)
- Hook registry flags per variant slug

Run:

```bash
python -m pytest examples/rogii/tests/test_variant_hooks.py -q
```
