# Rogii trace experiments — base scientific papers

One **primary base paper** per preprocessing variant (plus a co-primary preprocessing paper for baseline). PDFs are stored under [`papers/`](papers/) when an open-access copy is available; otherwise use the canonical publisher / DOI link.

| # | Variant | Paper | Authors | Year | PDF in repo | Canonical link |
|---|---------|-------|---------|------|-------------|----------------|
| 1 | `baseline_column_transformer` | LightGBM: A Highly Efficient Gradient Boosting Decision Tree | Ke et al. | 2017 | [ke2017_lightgbm.pdf](papers/baseline_column_transformer/ke2017_lightgbm.pdf) | https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree |
| 1b | `baseline_column_transformer` | Scikit-learn: Machine Learning in Python (ColumnTransformer) | Pedregosa et al. | 2011 | [pedregosa2011_sklearn.pdf](papers/baseline_column_transformer/pedregosa2011_sklearn.pdf) | https://jmlr.org/papers/v12/pedregosa11a.html |
| 2 | `typewell_gr_alignment` | Dynamic Programming Algorithm Optimization for Spoken Word Recognition (DTW) | Sakoe & Chiba | 1978 | [sakoe1978_dtw.pdf](papers/typewell_gr_alignment/sakoe1978_dtw.pdf) | https://doi.org/10.1109/TASSP.1978.1163055 |
| 3 | `ps_point_leakage_aware` | Leakage in Data Mining: Formulation, Detection, and Avoidance | Kaufman et al. | 2012 | [kaufman2012_leakage.pdf](papers/ps_point_leakage_aware/kaufman2012_leakage.pdf) | https://doi.org/10.1145/2382575.2382577 |
| 4 | `robust_scale_log1p` | Robust Statistics: The Approach Based on Influence Functions | Hampel et al. | 1986 | [pedregosa2011_sklearn_robust_substitute.pdf](papers/robust_scale_log1p/pedregosa2011_sklearn_robust_substitute.pdf) (open substitute) | https://doi.org/10.1002/9781118186435 |
| 5 | `parallel_multiwell_loader` | Dask: Parallel Computation with Blocked algorithms and Task Scheduling | Rocklin | 2015 | [rocklin2015_dask.pdf](papers/parallel_multiwell_loader/rocklin2015_dask.pdf) | https://doi.org/10.25080/Majora-7b98e3ed-013 |
| 6 | `formation_plane_spatial` | Nearest Neighbor Pattern Classification | Cover & Hart | 1967 | [cover1967_knn.pdf](papers/formation_plane_spatial/cover1967_knn.pdf) | https://doi.org/10.1109/TIT.1967.1053964 |
| 6b | `formation_plane_spatial` | A Two-dimensional Interpolation Function for Irregularly-spaced Data | Shepard | 1968 | [shepard1968_interpolation.pdf](papers/formation_plane_spatial/shepard1968_interpolation.pdf) | https://doi.org/10.1145/321267.321298 |

## Trace-theory paper (all variants)

| Paper | Role | Location |
|-------|------|----------|
| *Agentic Programming as Formal Automata* (agent-tracing) | Trace language audit + agent implementation | [`data/papers/agent-tracing`](../../data/papers/agent-tracing) (PaperBench bundle) |

## Per-variant human summaries

- [`traces/preprocessing/baseline_column_transformer/paper_refs.md`](traces/preprocessing/baseline_column_transformer/paper_refs.md)
- [`traces/preprocessing/typewell_gr_alignment/paper_refs.md`](traces/preprocessing/typewell_gr_alignment/paper_refs.md)
- [`traces/preprocessing/ps_point_leakage_aware/paper_refs.md`](traces/preprocessing/ps_point_leakage_aware/paper_refs.md)
- [`traces/preprocessing/robust_scale_log1p/paper_refs.md`](traces/preprocessing/robust_scale_log1p/paper_refs.md)
- [`traces/preprocessing/parallel_multiwell_loader/paper_refs.md`](traces/preprocessing/parallel_multiwell_loader/paper_refs.md)
- [`traces/preprocessing/formation_plane_spatial/paper_refs.md`](traces/preprocessing/formation_plane_spatial/paper_refs.md)

Machine-readable index: [`papers/manifest.json`](papers/manifest.json)
