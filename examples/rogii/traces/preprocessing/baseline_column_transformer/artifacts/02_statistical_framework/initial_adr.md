# Architecture Decision Records

## ADR-01: Initial pipeline ADR

- **Options considered:** proceed, defer
- **Chosen:** proceed
- **Rationale:** baseline_column_transformer phase 02 bootstrap (baseline ColumnTransformer + LightGBM; Pedregosa/Ke path); cv=kfold; target_log1p=none; high_missing=GR,TVT_input
- **Consequences:** Revise after first CV
