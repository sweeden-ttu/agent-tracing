# parallel_multiwell_loader

**Branch:** `trace/parallel-multiwell-loader`  
**Approach:** Parallel IO + geology surfaces  
**Base paper:** Rocklin 2015 Dask

Scaffolded trace bundle. Run phases in order via `notebooks/phase_runner.py`.

| Phase | Artifact dir | Contract |
|-------|--------------|----------|
| 01 | `artifacts/01_data_analysis/` | `PHASE_CONTRACT.json` |
| 02 | `artifacts/02_statistical_framework/` | `PHASE_CONTRACT.json` |
| 03 | `artifacts/03_feature_engineering/` | `PHASE_CONTRACT.json` |
| 04 | `artifacts/04_model_training/` | `PHASE_CONTRACT.json` |
| 05 | `artifacts/05_evaluation/` | `PHASE_CONTRACT.json` |
| 06 | `artifacts/06_submission/` | `PHASE_CONTRACT.json` |

Regenerate trace index: ``python examples/rogii/scripts/write_trace_row_index.py --variant parallel_multiwell_loader``

See [`../../README.md`](../../README.md) and [`../README.md`](../README.md).
