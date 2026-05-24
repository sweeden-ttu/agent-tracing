# Phase notebooks

Six notebooks implement the baseline TVT pipeline with **artifact handoffs** under `../artifacts/`.

| Notebook | Reads | Writes |
|----------|-------|--------|
| `01_data_analysis.ipynb` | Rogii `data/` CSVs | `artifacts/01_data_analysis/` |
| `02_statistical_framework.ipynb` | phase 01 manifest | `artifacts/02_statistical_framework/` |
| `03_feature_engineering.ipynb` | phase 01 | `artifacts/03_feature_engineering/` |
| `04_model_training.ipynb` | phases 01 + 03 | `artifacts/04_model_training/` |
| `05_evaluation.ipynb` | phases 01 + 04 | `artifacts/05_evaluation/` |
| `06_submission.ipynb` | phases 01 + 04 | `artifacts/06_submission/submission.csv` |

## Run order

Execute notebooks **in order** (or call `phase_runner.py` from the shell):

```bash
cd notebooks
python -c "from phase_runner import run_01_data_analysis; run_01_data_analysis()"
python -c "from phase_runner import run_02_statistical_framework; run_02_statistical_framework()"
# … through run_06_submission
```

Or run all phases:

```bash
python -c "
from phase_runner import *
run_01_data_analysis()
run_02_statistical_framework()
run_03_feature_engineering()
run_04_model_training()  # set max_rows= for login-node smoke tests
run_05_evaluation()
run_06_submission()
"
```

## Core module

- **`phase_runner.py`** — implements trace-indexed steps per phase; skips Type-3 bounds and `sbatch` cells.
- **`write_phase_notebooks.py`** — regenerates the six `.ipynb` files.

Trace row reference: [`../trace_row_index.csv`](../trace_row_index.csv).

## Slurm note

Phase 04 runs LightGBM cross-validation on the login node by default. For full-scale training, use `hpcc/train_tcn.slurm` or call `run_04_model_training(max_rows=None)` on Matador after syncing artifacts.

**Before `sbatch` (episodic or long GPU jobs):** run interactive preflight per [`../SLURM_INTERACTIVE_PREFLIGHT.md`](../SLURM_INTERACTIVE_PREFLIGHT.md):

```bash
cd /lustre/work/sweeden/rogii
bash hpcc/interactive_preflight_from_slurm.sh hpcc/train_tcn_episodic.slurm
# then --run when ready; stop at LONG_RUNNING_START
```
