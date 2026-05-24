# Unified Kaggle notebook

Single kernel that runs the Rogii pipeline end-to-end:

1. **Tabular baseline** — `load_competition_frames` + GroupKFold by `well_id` (LightGBM or sklearn HGBR)
2. **RMSE gate (12 ft)** — if mean OOF `cv_rmse` ≥ 12, trigger episodic TCN training
3. **Episodic TCN** — per-fold episodes, checkpoints under `checkpoints/`, `episode_manifest.json` + `ensemble_manifest.json`
4. **Ensemble blend** — inverse-RMSE weights for tabular vs episodic; optional tabular refine pass
5. **Kaggle submit** — `kaggle competitions submit` when CLI/credentials are available

## Location

| Path | Role |
|------|------|
| [`../kaggle/rogii-unified-baseline/`](../kaggle/rogii-unified-baseline/) | Kernel folder (`kernel-metadata.json`, notebook, bundled `pipeline/`) |
| [`../kaggle/rogii-unified-baseline/run_kaggle_pipeline.py`](../kaggle/rogii-unified-baseline/run_kaggle_pipeline.py) | Gate (12 ft), episodic, blend, auto-submit |
| [`../kaggle/rogii-unified-baseline/run_baseline.py`](../kaggle/rogii-unified-baseline/run_baseline.py) | Tabular baseline only |
| [`../kaggle/rogii-unified-baseline/run_episodic_kaggle.py`](../kaggle/rogii-unified-baseline/run_episodic_kaggle.py) | Episodic TCN + checkpoints |
| [`../kaggle/rogii-unified-baseline/embed_notebook.py`](../kaggle/rogii-unified-baseline/embed_notebook.py) | Regenerate self-contained notebook |
| [`../kaggle/rogii-unified-baseline/sync_bundle.sh`](../kaggle/rogii-unified-baseline/sync_bundle.sh) | Copy `pipeline/` + `train_predict.py` from `/lustre/work/sweeden/rogii` |

## Synthetic competition data

Offline smoke tests use the flat layout under `/lustre/work/sweeden/rogii/data` (see [`/lustre/work/sweeden/rogii/data/NOTE.md`](../../../../rogii/data/NOTE.md)):

```bash
python /lustre/work/sweeden/rogii/scripts/generate_synthetic_competition_data.py \
  --data-dir /lustre/work/sweeden/rogii/data
```

Ground-truth labels for the blind prediction tail are in `data/submission_samples/submission.csv` (train `TVT` at submission row indices). The runner reports:

- **`cv_rmse`** — mean OOF RMSE across CV folds (original target scale)
- **`holdout_rmse_synthetic`** — RMSE of aligned `submission.csv` vs the oracle (only when the oracle file exists)

## Local run (login node — no full training pipeline)

```bash
cd examples/rogii/kaggle/rogii-unified-baseline
bash sync_bundle.sh
python run_baseline.py --data-dir /lustre/work/sweeden/rogii/data --work-dir /tmp/rogii_kaggle_out
cat /tmp/rogii_kaggle_out/metrics.json
```

## Push and run on Kaggle

1. Accept competition rules on Kaggle.
2. Regenerate notebook and sync bundle:

   ```bash
   bash examples/rogii/kaggle/rogii-unified-baseline/sync_bundle.sh
   python examples/rogii/kaggle/rogii-unified-baseline/embed_notebook.py
   ```

3. Push and execute (GPU + internet enabled for episodic TCN and `kaggle submit`):

   ```bash
   cd examples/rogii/kaggle/rogii-unified-baseline
   kaggle kernels push -p .
   kaggle kernels status scottweeden/rogii-trace-baseline-smoke
   kaggle kernels output scottweeden/rogii-trace-baseline-smoke -p /tmp/rogii_kernel_out
   ```

4. Inspect `pipeline_metrics.json`, `checkpoints/episode_manifest.json`, and `submission.csv` in kernel output.

## Relation to trace variants

This kernel is the **shared baseline** aligned with `baseline_column_transformer` phase 04 (LightGBM + median imputation). Variant-specific hooks (typewell, PS mask, robust scale, etc.) remain in the six trace worktrees and Slurm phase jobs — see [VARIANTS.md](VARIANTS.md) and [PAPER_ALIGNMENT.md](PAPER_ALIGNMENT.md).
