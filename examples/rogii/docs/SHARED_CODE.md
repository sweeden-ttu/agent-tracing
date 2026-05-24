# Shared code (`traces/preprocessing/_shared/`)

Code shared across all six variant worktrees. Synced to dedicated worktrees by `scaffold_trace_variant.py --sync-worktrees`.

## Files

| File | Purpose |
|------|---------|
| `variant_hooks.py` | `VariantHooks` dataclass + `_REGISTRY` + `load_hooks()` |
| `phase_runner_core.py` | `run_01` … `run_06`, `run_phase()`, manifest I/O |
| `__init__.py` | Package marker (if present) |

## `VariantHooks` API

```python
@dataclass
class VariantHooks:
    slug: str
    approach: str
    phase02_rationale: str
    force_log1p: bool | None = None
    numeric_scaler: str = "median"          # median | robust
    eval_mask: str = "full_well"            # full_well | post_ps_only
    typewell_align: bool = False
    typewell_interpolator: Literal["linear", "pchip"] = "linear"
    parallel_workers: int = 4
    formation_knn: bool = False
    formation_knn_k: int = 5

    def phase01_extra(train_df, target) -> dict
    def resolve_log1p(log_rec) -> bool
    def augment_train_test(train, test, data_dir) -> (tr, te, extra_cols)
    def eval_mask_indices(train_df) -> ndarray | None
    def build_numeric_transformer() -> sklearn Pipeline
```

## Phase runner globals

Each variant’s thin `notebooks/phase_runner.py` calls:

```python
from phase_runner_core import init_runner, run_phase, run_01_data_analysis, ...
init_runner(VARIANT_DIR, load_hooks("typewell_gr_alignment"))
```

`init_runner` binds `VARIANT_DIR`, `HOOKS`, `ARTIFACTS_ROOT`, `TRACE_INDEX`.

## Per-variant notebooks

Each variant directory contains:

```
notebooks/
├── phase_runner.py          # init_runner + re-exports
├── phase_notebook_cells.py  # Jupyter cell sources per phase
└── write_phase_notebooks.py # Regenerate .ipynb files
```

Regenerate all notebooks:

```bash
python traces/preprocessing/baseline_column_transformer/notebooks/write_phase_notebooks.py --all-variants
```

## Trace index

`scripts/write_trace_row_index.py` builds `trace_row_index.csv` from `trace_language.csv` with phase, paper, and train/predict tags.

```bash
python examples/rogii/scripts/write_trace_row_index.py --variant baseline_column_transformer
```
