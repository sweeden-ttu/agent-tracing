# Statistical framework: baseline_column_transformer

**Approach:** ColumnTransformer + LightGBM baseline

- **Hypothesis:** preprocessing variant improves OOF RMSE vs baseline.
- **CV:** GroupKFold by well; nested subdivisions by well and depth bin.
- **Metric:** competition RMSE; SMRE = mean ± std across folds/episodes.
- **Type-3 bounds:** every producer lane bounded by schema-sentinel or submission_validator.
