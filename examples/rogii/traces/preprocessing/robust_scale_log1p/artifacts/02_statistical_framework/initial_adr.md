# Architecture Decision Records

## ADR-01: Initial pipeline ADR

- **Options considered:** proceed, defer
- **Chosen:** proceed
- **Rationale:** robust_scale_log1p phase 02 bootstrap (RobustScaler numeric block + log1p target (Hampel et al.)); cv=kfold; target_log1p=none; high_missing=GR,TVT_input
- **Consequences:** Revise after first CV
