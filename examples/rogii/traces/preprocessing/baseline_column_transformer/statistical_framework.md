# Statistical framework: baseline_column_transformer

**Approach:** ColumnTransformer + LightGBM baseline

**Base papers:** Ke et al. (2017) LightGBM; Pedregosa et al. (2011) scikit-learn ColumnTransformer

- **Hypothesis:** heterogeneous column preprocessing (ColumnTransformer) plus histogram GBDT (LightGBM) improves OOF RMSE vs shared baseline.
- **CV:** GroupKFold by well; nested subdivisions by well and depth bin.
- **Metric:** competition RMSE; SMRE = mean ± std across folds/episodes.
- **Type-3 bounds:** every producer lane bounded by schema-sentinel or submission_validator.
