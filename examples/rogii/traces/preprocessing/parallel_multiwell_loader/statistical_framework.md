# Statistical framework: parallel_multiwell_loader

**Approach:** Parallel IO + geology surface columns

- **Hypothesis:** preprocessing variant improves OOF RMSE vs baseline.
- **CV:** GroupKFold by well; nested subdivisions by well and depth bin.
- **Metric:** competition RMSE; SMRE = mean ± std across folds/episodes.
- **Type-3 bounds:** every producer lane bounded by schema-sentinel or submission_validator.
