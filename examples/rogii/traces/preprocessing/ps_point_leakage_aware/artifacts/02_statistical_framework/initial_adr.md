# Architecture Decision Records

## ADR-01: Initial pipeline ADR

- **Options considered:** proceed, defer
- **Chosen:** proceed
- **Rationale:** ps_point_leakage_aware phase 02 bootstrap (leakage-aware eval; post-PS RMSE mask (Kaufman et al.)); cv=kfold; target_log1p=none; high_missing=GR,TVT_input
- **Consequences:** Revise after first CV
