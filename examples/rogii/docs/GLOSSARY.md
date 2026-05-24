# Glossary

Alphabetical reference for Rogii trace pipelines, wellbore ML, and agent-tracing terminology.

---

### Aho–Corasick / Type-3 consumer

Multi-pattern string matcher compiled from unit-test keywords. In agent-tracing theory, the **Data-Driven consumer** has a **Type-3** (regular) trace language: membership in the verified trace is decidable in linear time. Concrete consumers include `schema-sentinel` and `submission_validator`.

### AGENT_TRACING_ROOT

Environment variable pointing at the git worktree root that owns the variant’s `examples/rogii/traces/preprocessing/{variant}/` directory. Set by generated submit wrappers so Slurm jobs run against the correct checkout.

### Artifact / phase manifest

Each pipeline phase writes `artifacts/{phase}/phase_manifest.json` listing output paths and timestamps. Downstream phases and `verify_phase_handoff.py` use manifests for handoff validation.

### Baseline variant

`baseline_column_transformer`: ColumnTransformer numeric imputation + LightGBM regression. Reference for ablation comparisons (Ke et al. 2017, Pedregosa et al. 2011).

### Beam search path (typewell)

Band-constrained dynamic-programming alignment of horizontal **GR** against a **typewell** log. Implemented in `pipeline/typewell_alignment.py`; produces `estimated_tvt`, `gr_typewell_diff`, `dtw_path_cost`, etc.

### Chomsky hierarchy (Type-0 … Type-3)

Classification of formal languages by grammar power. **Type-0** producers (LLM agents) are recursively enumerable; **Type-3** consumers (keyword DFAs) are regular and efficiently verifiable. See trace-theory paper in PaperBench `data/papers/agent-tracing/`.

### ColumnTransformer

scikit-learn construct applying different transforms per column block (numeric impute/scale, categorical encode). Default preprocessor for baseline and shared phase 04 training.

### CV / GroupKFold

Cross-validation with folds grouped by **well_id** so the same borehole never appears in both train and validation within a fold.

### DTW (Dynamic Time Warping)

Classic sequence alignment (Sakoe & Chiba 1978). The typewell variant uses a beam-search approximation rather than full DTW for speed on long logs.

### Experiment descriptor

`experiment_descriptor.json` per variant: base papers, claims, trace tokens, ablation factors, link to `paper_file` PDF.

### Formation columns

Lithology thickness indicators in Rogii train data: `ANCC`, `ASTNU`, `ASTNL`, `EGFDU`, `EGFDL`, `BUDA`. Used by `formation_plane_spatial` for thickness sums and k-NN propagation.

### frontier.yaml

Architecture spec at `/lustre/work/sweeden/frontier-evals/frontier.yaml`. Section `rogii_pipeline` maps variants → worktrees, Slurm tags, and phases.

### GR (Gamma Ray)

Well-log measurement used for typewell alignment and as a numeric feature.

### Handoff / preboot

Before a Slurm phase runs, `verify_phase_handoff.py --preboot` checks prior phase manifests and required files exist.

### Hook (`VariantHooks`)

Dataclass in `_shared/variant_hooks.py` encoding per-variant behavior: typewell alignment, PS mask, robust scaler, parallel loader metadata, formation k-NN.

### LightGBM

Gradient boosting library (Ke et al. 2017). Default regressor in phase 04 with objective `regression` and metric RMSE.

### log1p transform

Target transform `log(1 + y)` used by `robust_scale_log1p`; inverted with `expm1` at predict time.

### MD / TVD / TVT

**MD** — measured depth along borehole. **TVD** — true vertical depth. **TVT** — true vertical thickness (competition target). **TVT_input** — input column; NaN marks perforation start (**PS**).

### OOF (out-of-fold)

Predictions on validation rows during cross-validation, stored as `oof_predictions.npy` in phase 04.

### PaperBench

Benchmark in `frontier-evals/project/paperbench`: agent rollout, reproduction, grading. Rogii variants use split `trace_variants` and `TracePipelineSolver`.

### Perforation start (PS)

Point in a well where `TVT_input` becomes NaN. Competition RMSE is scored on **post-PS** rows only. The PS variant applies `post_ps_mask` during CV.

### Phase (01–06)

Fixed pipeline stages: data analysis → statistical framework → feature engineering → model training → evaluation → submission.

### Post-PS mask

Boolean array from `pipeline/leakage_masks.py`: `True` for rows at or after perforation start per well.

### RobustScaler

scikit-learn scaler using median and IQR; resistant to outliers (Hampel-style robust statistics; Pedregosa et al. substitute in open PDFs).

### ROGII_ROOT

Path to live Kaggle codebase (`/lustre/work/sweeden/rogii`): `data/`, `train_predict.py`, `pipeline/`.

### RMSE

Root mean squared error — primary competition metric on post-PS **TVT**.

### Slurm job tag

Short name prefix for chained jobs: `trace_baseline`, `trace_typewell`, `trace_ps`, `trace_robust`, `trace_parallel`, `trace_formation`.

### SMRE

Statistical metric reporting convention in trace plans: mean RMSE ± std across folds/episodes.

### Swim lane

Row group in `trace_language.csv` assigned to one sub-agent (e.g. `eda_profiler`, `model_trainer`).

### Trace language / trace_language.csv

CSV specification of agent actions, resource envelopes, and Chomsky types. Each variant has its own file under `traces/preprocessing/{variant}/`.

### Typewell

Reference well log (separate CSV) with GR vs TVT used to align horizontal well features via DTW-like path search.

### Variant slug

Directory name and `VARIANT` env value, e.g. `typewell_gr_alignment`.

### Worktree

Separate git checkout under `/lustre/work/sweeden/agent-tracing-trace-*`, one primary variant per dedicated worktree (baseline hosts all six trace folders).
