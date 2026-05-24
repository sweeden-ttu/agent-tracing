# Rogii trace bundles

Execution traces and phase artifacts for the [Rogii Wellbore Geology Prediction](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction) ablation matrix.

## Layout

```text
examples/rogii/traces/
├── README.md                 ← this file
└── preprocessing/
    ├── README.md             ← six-variant index
    ├── baseline_column_transformer/   ← merge order #1 (phase_runner + artifacts)
    ├── typewell_gr_alignment/
    ├── ps_point_leakage_aware/
    ├── robust_scale_log1p/
    ├── parallel_multiwell_loader/
    └── formation_plane_spatial/
```

Each variant directory contains:

| Path | Purpose |
|------|---------|
| `trace_language.csv` | 29-column agent swim-lane specification |
| `trace_row_index.csv` | Row → phase → paper → `train_predict.py` index |
| `experiment_descriptor.json` | Base paper + trace join |
| `notebooks/phase_runner.py` | Six-phase artifact pipeline |
| `artifacts/<phase>/` | Phase outputs + `PHASE_CONTRACT.json` |
| `artifacts/pipeline_state.json` | Last completed phase tracker |

## Scaffold

Create or refresh variant folders:

```bash
python examples/rogii/scripts/scaffold_trace_variant.py --all-pending
python examples/rogii/scripts/scaffold_trace_variant.py --variant baseline_column_transformer --phases-only
```

Canonical trace CSVs live in `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/` until each branch merges to `main` (see [`../MERGE_PATH.md`](../MERGE_PATH.md)).

## Phase order

1. `01_data_analysis` — schema, EDA, well groups, target diagnosis  
2. `02_statistical_framework` — experiment design, ablation grid, ADR  
3. `03_feature_engineering` — ColumnTransformer config, CV folds  
4. `04_model_training` — LightGBM cross-val (Slurm for full scale)  
5. `05_evaluation` — OOF metrics and residuals  
6. `06_submission` — `submission.csv` + envelope validation  
