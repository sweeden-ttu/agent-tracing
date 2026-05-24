# Statistical framework: ps_point_leakage_aware

**Approach:** PS-point detection + post-PS RMSE mask

- **Hypothesis:** preprocessing variant improves OOF RMSE vs baseline.
- **CV:** GroupKFold by well; nested subdivisions by well and depth bin.
- **Metric:** competition RMSE; SMRE = mean ± std across folds/episodes.
- **Type-3 bounds:** every producer lane bounded by schema-sentinel or submission_validator.
