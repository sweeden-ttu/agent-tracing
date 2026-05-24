# Variant ↔ research paper alignment

Critical review of each trace branch against its `experiment_descriptor.json` base paper and what the **implemented** pipelines actually exercise (LightGBM phase 04 + episodic TCN as of 2026-05-24).

| Variant | Base paper | Paper claim (abstraction) | Phase 04 (LightGBM) | Episodic TCN | Alignment |
|---------|------------|---------------------------|---------------------|--------------|-----------|
| **baseline** | Ke et al. 2017 LightGBM; Pedregosa 2011 sklearn | Histogram GBDT + heterogeneous column preprocessing | ColumnTransformer median + LGBM, `full_well` | 6 base log cols only | **Strong** for tabular baseline |
| **typewell** | Sakoe & Chiba 1978 DTW | Depth-indexed sequence alignment / warping | +8 GR/typewell features (`gr_typewell_*`, `dtw_path_cost`) | Variant hooks in `train_tcn.py` | **Good** (DTW proxy via beam search, not full Sakoe band) |
| **ps** | Kaufman et al. 2012 leakage | Evaluation mask must match deployment (post-PS) | `eval_mask=post_ps_only`, OOF ~0.053 | `post_ps_only` in `train_tcn.py` benchmark | **Strong** |
| **robust** | Hampel 1986 robust stats | Robust scale + skewed target handling | `RobustScaler` + log1p target in transform | log1p + robust via hooks in TCN | **Good** |
| **parallel** | Rocklin 2015 Dask | Parallel IO + optional surface features | +13 IO/formation cols (re-run phases 03–06) | Variant hooks in TCN | **Good** after `parallel_loader` fix |
| **formation** | Cover & Hart 1967 k-NN | Spatial neighbor propagation of formation labels | +geometry + `formation_*` cols | Variant hooks in TCN | **Good** |

## Per-variant detail

### baseline_column_transformer

- **Papers:** Ke et al. (LightGBM), Pedregosa et al. (ColumnTransformer).
- **Implemented:** Median imputation, numeric block, 5-fold depth/well CV, RMSE on `full_well`.
- **Gap:** None for stated baseline scope.

### typewell_gr_alignment

- **Paper:** Sakoe & Chiba — DTW / warping for aligning GR to typewell curves.
- **Implemented:** `add_typewell_alignment_features` with PCHIP interpolator; 14 feature columns in phase 04.
- **Gap:** No true DTW band search (documented as proxy features); TCN does not consume alignment columns. Ablation grid (`linear` vs `pchip`) not swept automatically.

### ps_point_leakage_aware

- **Paper:** Kaufman et al. — leakage-aware evaluation.
- **Implemented:** `post_ps_only` mask for OOF/CV metrics; PS detection per well in phase 01 metadata.
- **Gap:** TCN still reports full-well-scale RMSE (~11k on raw TVT). Fair comparison requires applying `post_ps_mask` to TCN OOF (now supported in variant-aware `train_tcn.py`).

### robust_scale_log1p

- **Paper:** Hampel et al. — robust M-estimators; sklearn RobustScaler cited.
- **Implemented:** `force_log1p=True`, `numeric_scaler=robust` in phase hooks.
- **Gap:** OOF RMSE 0.645 vs baseline 0.613 on `full_well` — robust path does not beat baseline yet. TCN must use log1p target to align (variant-aware training).

### parallel_multiwell_loader

- **Paper:** Rocklin — parallel task graphs for blocked IO.
- **Implemented:** Loader metadata in phase 01; `parallel_read_multiwell_csvs` exists in tests.
- **Gap:** **Phase 04 does not add surface/parallel-derived columns** — metrics match baseline exactly. Paper alignment requires wiring `attach_geology_surface_features` into phase 04 feature_config.

### formation_plane_spatial

- **Paper:** Cover & Hart k-NN; Shepard 1968 supporting (interpolation).
- **Implemented:** `add_formation_spatial_features` with k=5; thickness sum, KNN propagated column on **train**; test-safe column filter (`te_form_cols`).
- **Gap:** Formation one-hot columns absent on test — handled. TCN still ignores formation features.

## Trace theory (all variants)

Agent-tracing Chomsky paper is aligned for **governance** (Type-0/3 envelopes, `trace_language.csv`, Slurm rows). That is independent of geoscience paper fidelity.

## Recommended paper-faithful fixes (priority)

1. Wire `variant_hooks.augment_train_test` into `train_tcn.py` (done in this change set).
2. Wire parallel variant surfaces into `phase_runner_core` feature list for phase 04.
3. Run ablation sweeps listed in each `ablation_plan.json` (not just single default level).
4. Report TCN metrics on same `eval_mask` as LightGBM for ps and primary `rmse_post_ps` everywhere.
