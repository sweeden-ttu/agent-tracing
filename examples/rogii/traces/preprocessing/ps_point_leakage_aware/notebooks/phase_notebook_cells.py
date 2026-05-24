"""Rich notebook cell definitions (competition-depth EDA + phase_runner handoff).

Benchmark (sampled May 2026 Rogii kernels by vote count):
- pilkwang/rogii-eda-leakage-aware-submission-pipeline: 65 cells / 583 md lines
- ravaghi/wellbore-geology-prediction-lightgbm: 18 cells
- aidensong123/rogii-wellbore-geology-lightgbm-baseline: 26 cells
- nihilisticneuralnet/9-251-rogii-wellbore-geology-prediction-dwt-based: 24 cells
- cdeotte/xgb-starter-cv-15: 21 cells
- romantamrazov/rogii-super-solution-lb-top-3: 11 cells
Average ~28 cells / ~127 markdown lines across sampled public notebooks.

Each phase notebook targets >=36 cells with inline analysis, then persists artifacts via phase_runner.
"""

from __future__ import annotations

from pathlib import Path

VARIANT = "ps_point_leakage_aware"
NB_DIR = Path(__file__).resolve().parent

COMMON_IMPORTS = '''"""Shared imports for Rogii TVT pipeline notebooks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

NB_DIR = Path.cwd()
if not (NB_DIR / "phase_runner.py").is_file():
    NB_DIR = Path(r"{nb_dir}")
VARIANT_DIR = NB_DIR.parent
ROGII_ROOT = Path("/lustre/work/sweeden/rogii")
sys.path.insert(0, str(NB_DIR))
if str(ROGII_ROOT) not in sys.path:
    sys.path.insert(0, str(ROGII_ROOT))

from phase_runner import (
    ARTIFACTS_ROOT,
    TRACE_INDEX,
    require_prior_phase,
    load_phase_manifest,
    trace_steps_for_phase,
    _resolve_path,
    _read_json,
    _load_train_predict,
)

pd.set_option("display.max_columns", 40)
plt.style.use("seaborn-v0_8-whitegrid")
'''


def _cells(*pairs: tuple[str, str]) -> list[tuple[str, str]]:
    return list(pairs)


def cells_01_data_analysis() -> list[tuple[str, str]]:
    return _cells(
        ("markdown", f"""# 01 — Data analysis (schema, EDA, wells, target)

**Variant:** `{VARIANT}` · **Competition:** [Rogii Wellbore Geology Prediction](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction)

This notebook mirrors the depth of top public kernels (e.g. Chris Deotte *EDA Starter*, Pilkwang *Leakage-Aware Pipeline*):
file inventory, column roles, missingness, target behavior, well grouping, and log1p diagnosis — then writes phase artifacts for downstream steps.

**Trace index:** `../trace_row_index.csv` · **Artifacts:** `../artifacts/01_data_analysis/`
"""),
        ("markdown", "## 1. Setup and data root\n\nResolve competition CSVs from Kaggle mount or local Rogii checkout (`ROGII_ROOT/data`)."),
        ("code", COMMON_IMPORTS.format(nb_dir=NB_DIR) + "\nPHASE = \"01_data_analysis\"\nprint(\"Phase:\", PHASE, \"| trace steps:\", len(trace_steps_for_phase(PHASE)))\n"),
        ("code", '''def find_data_dir() -> Path:
    candidates = [
        ROGII_ROOT / "data",
        Path("/kaggle/input/competitions/rogii-wellbore-geology-prediction"),
        Path("/kaggle/input/rogii-wellbore-geology-prediction"),
    ]
    for c in candidates:
        if c.is_dir() and any(c.glob("*train*.csv")):
            return c.resolve()
    raise FileNotFoundError("Rogii train CSV not found; set ROGII_ROOT/data")

DATA_DIR = find_data_dir()
print("DATA_DIR:", DATA_DIR)
print("CSV files:", len(list(DATA_DIR.glob("*.csv"))))
'''),
        ("markdown", "## 2. Competition task recap\n\nPredict **True Vertical Thickness (TVT)** for hidden tail rows per horizontal well. Training CSVs include labeled `TVT`; test wells omit labels. Submission ids follow `{well_hash}_{row}` in `sample_submission.csv`."),
        ("markdown", "## 3. Load train / test / sample submission"),
        ("code", '''tp = _load_train_predict()
train_path = tp._find_default_csv(DATA_DIR, "train")
test_path = tp._find_default_csv(DATA_DIR, "test")
sample_path = tp._find_default_csv(DATA_DIR, "sample_submission")

train_df = pd.read_csv(train_path)
test_df = pd.read_csv(test_path)
sample_sub = pd.read_csv(sample_path, nrows=5)

print("train:", train_df.shape, "| test:", test_df.shape)
print("sample_submission columns:", list(sample_sub.columns))
display(train_df.head(3))
'''),
        ("markdown", "## 4. Schema registration (SchemaSentinel)\n\nLock id column and target column names to the submission envelope."),
        ("code", '''from pipeline.agents import SchemaSentinel
from pipeline.nb_support import ensure_id_column

schema_agent = SchemaSentinel()
schema = schema_agent.register_schema(sample_path)
id_col = schema["id_column"]
target = schema["target_columns"][0]
train_df = tp.align_train_target_to_schema(train_df, target)
train_df = ensure_id_column(train_df, id_col)
test_df = ensure_id_column(test_df, id_col)
print(json.dumps(schema, indent=2))
'''),
        ("markdown", "## 5. Column inventory and dtypes"),
        ("code", '''summary = pd.DataFrame({
    "column": train_df.columns,
    "dtype": train_df.dtypes.astype(str).values,
    "missing_pct": (train_df.isna().mean() * 100).round(2).values,
    "n_unique": [train_df[c].nunique(dropna=True) for c in train_df.columns],
})
display(summary.sort_values("missing_pct", ascending=False))
'''),
        ("markdown", "## 6. Missingness visualization\n\nHigh missingness in `GR` and `TVT_input` is common; downstream ColumnTransformer must handle NaN sentinels."),
        ("code", '''miss = train_df.isna().mean().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10, 4))
miss.head(20).plot(kind="barh", ax=ax, color="steelblue")
ax.set_xlabel("missing rate")
ax.set_title("Top missing columns (train)")
plt.tight_layout()
plt.show()
'''),
        ("markdown", "## 7. Target distribution and skewness\n\nTVT is strictly positive; log1p is only applied when skewness + positivity tests recommend it."),
        ("code", '''from pipeline.target_diagnostician import recommend_log1p

y = train_df[target].astype(float)
log_rec = recommend_log1p(y.values)
print(json.dumps(log_rec, indent=2))

fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
axes[0].hist(y.dropna(), bins=40, color="darkorange", edgecolor="white")
axes[0].set_title(f"{target} histogram")
axes[1].boxplot(y.dropna(), vert=True)
axes[1].set_title(f"{target} boxplot")
plt.tight_layout()
plt.show()
print(y.describe())
'''),
        ("markdown", "## 8. TVT_input and prediction zone\n\n`TVT_input` is observed in the known prefix and NaN in the hidden prediction tail — same pattern as top leakage-aware public notebooks."),
        ("code", '''if "TVT_input" in train_df.columns:
    known = train_df["TVT_input"].notna().sum()
    print(f"TVT_input known rows: {known:,} / {len(train_df):,} ({100*known/len(train_df):.1f}%)")
    if "MD" in train_df.columns:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.scatter(train_df["MD"], train_df[target], s=4, alpha=0.35, label="TVT")
        ax.scatter(train_df.loc[train_df["TVT_input"].notna(), "MD"],
                   train_df.loc[train_df["TVT_input"].notna(), "TVT_input"],
                   s=4, alpha=0.35, label="TVT_input")
        ax.set_xlabel("MD"); ax.legend(); ax.set_title("TVT vs TVT_input along MD")
        plt.tight_layout(); plt.show()
else:
    print("TVT_input column not present in this extract")
'''),
        ("markdown", "## 9. Well grouping for CV\n\nGroupKFold by well prefix when a stable group key exists; otherwise KFold (see phase 02 recommendations)."),
        ("code", '''from pipeline import well_group_detector as wgd

group_key = wgd.recommend_group_key(train_df, test_df, id_column=id_col)
groups = wgd.provide_groups(train_df, group_key, id_column=id_col) if group_key else None
print("group_key:", group_key)
if groups is not None:
    print("n_unique_groups:", wgd.count_unique_groups(groups))
    print(groups.value_counts().head())
else:
    print("No well grouping key detected — CV will fall back to KFold")
'''),
        ("markdown", "## 10. Depth coverage (MD)\n\nCheck measured depth span — useful for residual-by-depth evaluation in phase 05."),
        ("code", '''if "MD" in train_df.columns:
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.hist(train_df["MD"].dropna(), bins=50, color="teal", alpha=0.8)
    ax.set_xlabel("MD"); ax.set_title("Measured depth distribution")
    plt.tight_layout(); plt.show()
else:
    print("MD column absent")
'''),
        ("markdown", "## 11. Correlation with target (numeric logs)\n\nQuick screening of log features vs TVT — matches exploratory sections in LightGBM starter kernels."),
        ("code", '''num_cols = train_df.select_dtypes(include=[np.number]).columns.tolist()
num_cols = [c for c in num_cols if c not in (target,)]
if num_cols:
    corr = train_df[num_cols + [target]].corr(numeric_only=True)[target].drop(target, errors="ignore")
    corr = corr.reindex(corr.abs().sort_values(ascending=False).index)
    fig, ax = plt.subplots(figsize=(6, max(3, 0.25 * len(corr.head(12)))))
    corr.head(12).plot(kind="barh", ax=ax, color="purple")
    ax.set_title("|corr| with target (top 12)")
    plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 12. Train vs test column alignment\n\nEnsure feature columns match between splits before ColumnTransformer fitting."),
        ("code", '''train_cols = set(train_df.columns)
test_cols = set(test_df.columns)
only_train = sorted(train_cols - test_cols)
only_test = sorted(test_cols - train_cols)
print("columns only in train:", only_train[:10])
print("columns only in test:", only_test[:10])
'''),
        ("markdown", "## 13. Submission id pattern\n\nIds encode `{well_hash}_{row_index}` — used later for aligning test predictions."),
        ("code", '''sample_full = pd.read_csv(sample_path)
well_prefix = sample_full[id_col].astype(str).str.split("_").str[0]
print("unique wells in submission:", well_prefix.nunique())
print(well_prefix.value_counts().head())
'''),
        ("markdown", "## 14. Target quantiles and tail risk"),
        ("code", '''print(y.quantile([0.01, 0.05, 0.5, 0.95, 0.99]))
'''),
        ("markdown", "## 15. Sentinel / negative log values\n\nRogii CSVs use large negative sentinels for missing logs; preprocessor replaces them with NaN."),
        ("code", '''feature_cols = [c for c in train_df.columns if c not in (id_col, target)]
neg_frac = {c: float((train_df[c] < -1e9).mean()) for c in feature_cols if c in train_df.select_dtypes("number").columns}
print({k: v for k, v in sorted(neg_frac.items(), key=lambda x: -x[1])[:8] if v > 0})
'''),
        ("markdown", "## 16. EDA summary table (notebook-local)"),
        ("code", '''eda_preview = {
    "train_rows": len(train_df),
    "test_rows": len(test_df),
    "target_mean": float(y.mean()),
    "target_std": float(y.std()),
    "recommended_log1p": log_rec.get("use_log1p"),
    "group_key": group_key,
}
pd.Series(eda_preview)
'''),
        ("markdown", "## 17. Persist phase artifacts\n\nWrite JSON handoff files and `phase_manifest.json` via `phase_runner` (trace-aligned)."),
        ("code", '''from phase_runner import run_01_data_analysis

manifest = run_01_data_analysis(data_dir=DATA_DIR)
print("Phase manifest:")
for k, v in manifest.items():
    print(f"  {k}: {v}")
'''),
        ("markdown", "## 18. Artifact inspection"),
        ("code", '''phase_dir = ARTIFACTS_ROOT / PHASE
for p in sorted(phase_dir.iterdir()):
    print(p.name, "→", p.stat().st_size, "bytes")
'''),
    )


def cells_02_statistical_framework() -> list[tuple[str, str]]:
    return _cells(
        ("markdown", f"""# 02 — Statistical framework (experiment design, ablations)

**Variant:** `{VARIANT}` · Reads phase 01 manifest · Writes `artifacts/02_statistical_framework/`

Documents Ke (2017) LightGBM + Pedregosa (2011) ColumnTransformer factorial design, CV metric, and ADR — at the narrative depth of top Rogii solution writeups.
"""),
        ("code", COMMON_IMPORTS.format(nb_dir=NB_DIR) + "\nPHASE = \"02_statistical_framework\"\n"),
        ("markdown", "## 1. Verify phase 01 handoff"),
        ("code", '''p01 = require_prior_phase(PHASE)
print("prior:", p01["phase"], p01["completed_at"])
well_groups = _read_json(_resolve_path(p01["outputs"]["well_groups"]))
target_diag = _read_json(_resolve_path(p01["outputs"]["target_diagnosis"]))
eda_summary = _read_json(_resolve_path(p01["outputs"]["eda_summary"]))
print("group_key:", well_groups.get("group_key"))
print("use_log1p:", target_diag.get("use_log1p"))
'''),
        ("markdown", "## 2. Load experiment descriptor and base papers"),
        ("code", '''desc = json.loads((VARIANT_DIR / "experiment_descriptor.json").read_text())
abl = json.loads((VARIANT_DIR / "ablation_plan.json").read_text())
mle = json.loads((VARIANT_DIR / "mle_plan.json").read_text())
print("hypothesis:", desc["experiment"]["hypothesis"][:120], "...")
print("base paper:", desc["base_paper"]["title"])
print("ablation factors:", [f["id"] for f in abl.get("ablation_factors", [])])
'''),
        ("markdown", "## 3. Phase 01 → design decisions\n\nTranslate EDA into CV scheme, target transform, and high-missing feature list."),
        ("code", '''recommended_cv = "nested_groupkfold_by_well" if well_groups.get("group_key") else "kfold"
recommended_target_transform = "log1p" if target_diag.get("use_log1p") else "none"
high_missing = [c for c, r in eda_summary.get("missingness_rate", {}).items() if float(r) >= 0.40]
print("recommended_cv:", recommended_cv)
print("target_log1p:", recommended_target_transform)
print("high_missing_features:", high_missing)
'''),
        ("markdown", "## 4. Ablation factorial grid preview"),
        ("code", '''from pipeline.agents import ExperimentDesignArchitect
architect = ExperimentDesignArchitect()
factors = {f["id"]: f["levels"] for f in abl.get("ablation_factors", []) if "id" in f}
grid = architect.design_ablation_factorial_grid(factors)
print("n_runs:", len(grid))
pd.DataFrame(grid).head(12)
'''),
        ("markdown", "## 5. Training plan and episodic schedule"),
        ("code", '''training_plan = architect.design_factorial_and_episodic_training(factors)
print(json.dumps({k: training_plan[k] for k in list(training_plan)[:6]}, indent=2)[:1200])
'''),
        ("markdown", "## 6. Paper citations trace map"),
        ("code", '''citations = architect.cite_base_paper_ablations(desc)
print(json.dumps(citations, indent=2)[:1500])
'''),
        ("markdown", "## 7. Seed control and reproducibility"),
        ("code", '''from pipeline.agents import SeedControlOfficer
SeedControlOfficer().pin_seed(42)
print("seed pinned: 42")
'''),
        ("markdown", "## 8. ADR — architecture decision record"),
        ("code", '''from pipeline.agents import ADRRecorder
adr = ADRRecorder()
adr.record_initial_adr(rationale="baseline_column_transformer phase 02 — notebook walkthrough")
print(adr.serialize_markdown())
'''),
        ("markdown", "## 9. Cross-validation rationale\n\nWhen `group_key` is null we use **KFold** (not GroupKFold) to avoid pseudo-groups; when wells are identifiable, **GroupKFold** prevents leakage across horizontal well tails."),
        ("code", '''print("Phase 01 recommended_cv:", recommended_cv)
print("n_unique_groups:", well_groups.get("n_unique_groups"))
'''),
        ("markdown", "## 10. Target transform contract\n\nLog1p is only enabled when skewness + positivity diagnostics from phase 01 recommend it; inverse transform uses `expm1` at inference."),
        ("code", '''print(json.dumps(target_diag, indent=2))
'''),
        ("markdown", "## 11. Ablation factor level counts"),
        ("code", '''for fid, levels in factors.items():
    print(f"{fid}: {len(levels)} levels → {levels}")
'''),
        ("markdown", "## 12. MLE plan snapshot"),
        ("code", '''print(json.dumps(mle, indent=2)[:2000])
'''),
        ("markdown", "## 13. Factorial grid heatmap (target_log1p × scaler)"),
        ("code", '''gdf = pd.DataFrame(grid)
if {"target_log1p", "numeric_scaler"}.issubset(gdf.columns):
    pivot = gdf.groupby(["target_log1p", "numeric_scaler"]).size().unstack(fill_value=0)
    display(pivot)
'''),
        ("markdown", "## 14. SMRE and metric contract"),
        ("code", '''print("metric:", desc["experiment"].get("smre"), "| hypothesis metric: rmse_post_ps")
'''),
        ("markdown", "## 15. Persist phase 02 artifacts"),
        ("code", '''from phase_runner import run_02_statistical_framework
manifest = run_02_statistical_framework()
print(json.dumps(manifest, indent=2))
'''),
        ("markdown", "## 16. Review statistical_framework.json"),
        ("code", '''sf = _read_json(ARTIFACTS_ROOT / PHASE / "statistical_framework.json")
print(json.dumps(sf, indent=2))
'''),
        ("markdown", "## 17. Ablation grid summary table"),
        ("code", '''grid_doc = _read_json(ARTIFACTS_ROOT / PHASE / "ablation_grid.json")
pd.DataFrame(grid_doc["grid"]).describe(include="all")
'''),
        ("markdown", "## 18. Trace step coverage"),
        ("code", '''steps = trace_steps_for_phase(PHASE)
print(f"Trace steps executed for {PHASE}: {len(steps)}")
pd.DataFrame(steps)[["trace_row", "agent", "token"]].head(15)
'''),
        ("markdown", "## 19. Phase 02 completion checklist"),
        ("code", '''checks = {
    "statistical_framework.json": (ARTIFACTS_ROOT / PHASE / "statistical_framework.json").is_file(),
    "ablation_grid.json": (ARTIFACTS_ROOT / PHASE / "ablation_grid.json").is_file(),
    "phase_manifest.json": (ARTIFACTS_ROOT / PHASE / "phase_manifest.json").is_file(),
}
pd.Series(checks)
'''),
        ("markdown", "## 20. Handoff to phase 03\n\nNext notebook consumes `feature_config` + `cv_config` from phase 03 artifacts after ColumnTransformer assembly."),
        ("markdown", "Proceed to `03_feature_engineering.ipynb` once this manifest shows `completed_at`."),
    )


def cells_03_feature_engineering() -> list[tuple[str, str]]:
    return _cells(
        ("markdown", f"""# 03 — Feature engineering & cross-validation

**Variant:** `{VARIANT}` · ColumnTransformer + fold indices (Pedregosa 2011 pipeline pattern)
"""),
        ("code", COMMON_IMPORTS.format(nb_dir=NB_DIR) + "\nPHASE = \"03_feature_engineering\"\n"),
        ("markdown", "## 1. Load phase 01 data paths"),
        ("code", '''p01 = load_phase_manifest("01_data_analysis")
paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
schema = _read_json(_resolve_path(p01["outputs"]["schema"]))
target = p01["target_column"]
id_col = schema["id_column"]
train_df = pd.read_csv(paths["train_csv"])
test_df = pd.read_csv(paths["test_csv"])
print(train_df.shape, test_df.shape)
'''),
        ("markdown", "## 2. Feature column selection"),
        ("code", '''tp = _load_train_predict()
train_df = tp.align_train_target_to_schema(train_df, target)
feature_cols = [c for c in train_df.columns if c not in (id_col, target) and c in test_df.columns]
print(f"{len(feature_cols)} shared feature columns")
print(feature_cols)
'''),
        ("markdown", "## 3. Numeric / low-card / high-card split"),
        ("code", '''from pipeline.preprocessor import replace_sentinels_with_nan
X_train = replace_sentinels_with_nan(train_df[feature_cols].copy())
X_test = replace_sentinels_with_nan(test_df[feature_cols].copy())
num, low_c, high_c = tp.categorize_columns(pd.concat([X_train, X_test], ignore_index=True), id_col=id_col, target_cols=[target])
print("numeric:", num)
print("low_card:", low_c)
print("high_card:", high_c)
'''),
        ("markdown", "## 4. ColumnTransformer assembly preview"),
        ("code", '''preprocessor = tp.build_feature_matrix(X_train, numeric_cols=num, low_card_cols=low_c, high_card_cols=high_c)
print(preprocessor)
'''),
        ("markdown", "## 5. Effective CV scheme"),
        ("code", '''scheme, groups, n_eff = tp._effective_cv(train_df, test_df, id_col=id_col, n_splits_req=5)
print("scheme:", scheme, "| n_splits:", n_eff, "| groups:", groups is not None)
'''),
        ("markdown", "## 6. Fold index sizes (leak-safe splits)"),
        ("code", '''from pipeline.cv_orchestrator import emit_fold_indices
fold_sizes = []
for i, (tr, va) in enumerate(emit_fold_indices(
    scheme if scheme == "groupkfold" else "kfold", X_train, n_splits=n_eff,
    groups=groups, shuffle=True, random_state=42,
)):
    fold_sizes.append({"fold": i, "train": len(tr), "val": len(va)})
pd.DataFrame(fold_sizes)
'''),
        ("markdown", "## 7. Visualize fold validation sizes"),
        ("code", '''fs = pd.DataFrame(fold_sizes)
fig, ax = plt.subplots(figsize=(6, 3))
ax.bar(fs["fold"].astype(str), fs["val"], label="val", alpha=0.8)
ax.bar(fs["fold"].astype(str), fs["train"], bottom=fs["val"], label="train", alpha=0.5)
ax.set_xlabel("fold"); ax.set_ylabel("rows"); ax.legend(); ax.set_title("CV fold row counts")
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 8. Depth subdivision preview"),
        ("code", '''from pipeline.cv_orchestrator import subdivide_train_by_depth_bin
if "MD" in train_df.columns:
  depth_sub = subdivide_train_by_depth_bin(train_df)
  print(json.dumps(depth_sub, indent=2)[:800])
'''),
        ("markdown", "## 9. Numeric feature distributions (sample)\n\nInspect a few log curves after sentinel replacement — matches EDA sections in Pilkwang's leakage-aware pipeline."),
        ("code", '''plot_cols = [c for c in num[:4] if c in X_train.columns]
fig, axes = plt.subplots(1, len(plot_cols), figsize=(3 * len(plot_cols), 3))
if len(plot_cols) == 1:
    axes = [axes]
for ax, col in zip(axes, plot_cols):
    ax.hist(X_train[col].dropna(), bins=30, color="steelblue", alpha=0.85)
    ax.set_title(col)
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 10. Categorical cardinality check"),
        ("code", '''for col in (low_c + high_c)[:6]:
    print(col, "nunique:", X_train[col].nunique(dropna=True))
'''),
        ("markdown", "## 11. Train/test row alignment"),
        ("code", '''print("train rows:", len(train_df), "test rows:", len(test_df))
print("shared features:", len(feature_cols))
'''),
        ("markdown", "## 12. Missing rate after sentinel replacement"),
        ("code", '''print(X_train.isna().mean().sort_values(ascending=False).head(10))
'''),
        ("markdown", "## 13. Feature matrix shape after transform (sample)"),
        ("code", '''Xt = preprocessor.fit_transform(X_train.iloc[:500])
print("transformed shape (500 rows):", getattr(Xt, "shape", None))
'''),
        ("markdown", "## 14. Group overlap train/test"),
        ("code", '''from pipeline import well_group_detector as wgd
gk = wgd.recommend_group_key(train_df, test_df, id_column=id_col)
print("group_key:", gk)
'''),
        ("markdown", "## 15. Persist phase 03 artifacts"),
        ("code", '''from phase_runner import run_03_feature_engineering
manifest = run_03_feature_engineering()
print(json.dumps(manifest, indent=2))
'''),
        ("markdown", "## 16. Feature config snapshot"),
        ("code", '''feat = _read_json(_resolve_path(manifest["outputs"]["feature_config"]))
print(json.dumps(feat, indent=2)[:1200])
'''),
        ("markdown", "## 17. CV config snapshot"),
        ("code", '''cv_cfg = _read_json(_resolve_path(manifest["outputs"]["cv_config"]))
print(json.dumps(cv_cfg, indent=2))
'''),
        ("markdown", "## 18. Trace alignment check"),
        ("code", '''print("trace steps:", len(trace_steps_for_phase(PHASE)))
'''),
        ("markdown", "## 19. Fold index artifact preview"),
        ("code", '''fold_path = ARTIFACTS_ROOT / PHASE / "fold_indices.json"
if fold_path.is_file():
    fi = _read_json(fold_path)
    print("n_folds:", len(fi.get("folds", fi)))
'''),
        ("markdown", "## 20. Handoff to model training\n\nPhase 04 loads `feature_config`, `cv_config`, and fold indices for LightGBM CV."),
    )


def cells_04_model_training() -> list[tuple[str, str]]:
    return _cells(
        ("markdown", f"""# 04 — Model training (LightGBM cross-validation)

**Variant:** `{VARIANT}` · Ke et al. (2017) histogram GBDT with Pedregosa (2011) preprocessing pipeline.

> **Slurm note:** set `MAX_TRAIN_ROWS=None` and run on Matador for full-scale training per project rules.
"""),
        ("code", COMMON_IMPORTS.format(nb_dir=NB_DIR) + '''
PHASE = "04_model_training"
MAX_TRAIN_ROWS = None  # e.g. 2000 for login-node smoke test
'''),
        ("markdown", "## 1. Load prior phase configs"),
        ("code", '''require_prior_phase(PHASE)
p01 = load_phase_manifest("01_data_analysis")
p03 = load_phase_manifest("03_feature_engineering")
print("target:", p01["target_column"])
print("cv outputs:", list(p03["outputs"].keys()))
'''),
        ("markdown", "## 2. Target transform decision"),
        ("code", '''target_diag = _read_json(_resolve_path(p01["outputs"]["target_diagnosis"]))
use_log1p = bool(target_diag.get("use_log1p", False))
print("use_log1p:", use_log1p)
'''),
        ("markdown", "## 3. Estimator backend"),
        ("code", '''tp = _load_train_predict()
backend = "lightgbm" if tp._HAS_LGBM else "sklearn.hist_gradient_boosting"
print("backend:", backend)
'''),
        ("markdown", "## 4. Run cross-validated training"),
        ("code", '''from phase_runner import run_04_model_training
manifest = run_04_model_training(max_rows=MAX_TRAIN_ROWS)
print(json.dumps(manifest, indent=2))
'''),
        ("markdown", "## 5. CV RMSE by fold"),
        ("code", '''metrics = _read_json(_resolve_path(manifest["outputs"]["training_metrics"]))
fold_rmses = metrics.get("fold_rmses", [])
fig, ax = plt.subplots(figsize=(6, 3))
ax.plot(range(len(fold_rmses)), fold_rmses, marker="o")
ax.set_xlabel("fold"); ax.set_ylabel("RMSE"); ax.set_title(f"CV fold RMSE (mean={metrics.get('cv_rmse'):.3f})")
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 6. OOF prediction preview"),
        ("code", '''oof = np.load(_resolve_path(manifest["outputs"]["oof_predictions"]))
print("OOF shape:", oof.shape, "| finite:", np.isfinite(oof).mean())
'''),
        ("markdown", "## 7. Test prediction matrix"),
        ("code", '''test_mat = np.load(_resolve_path(manifest["outputs"]["test_preds_per_fold"]))
print("test_preds_per_fold:", test_mat.shape)
'''),
        ("markdown", "## 8. Transform metadata"),
        ("code", '''transform = _read_json(_resolve_path(manifest["outputs"]["transform"]))
print(json.dumps({k: transform[k] for k in ["use_log1p", "cv_scheme", "n_folds", "cv_rmse", "backend"]}, indent=2))
'''),
        ("markdown", "## 9. OOF vs true scatter\n\nVisual sanity check before submission — strong public kernels always plot predicted vs actual on CV holdout."),
        ("code", '''p01 = load_phase_manifest("01_data_analysis")
paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
train_df = pd.read_csv(paths["train_csv"])
train_df = tp.align_train_target_to_schema(train_df, transform["target_column"])
y = train_df[transform["target_column"]].astype(float).values
pred = np.expm1(np.clip(oof, None, 20)) if transform.get("use_log1p") else oof
m = np.isfinite(pred) & np.isfinite(y)
fig, ax = plt.subplots(figsize=(5, 5))
ax.scatter(y[m], pred[m], s=4, alpha=0.25)
lims = [min(y[m].min(), pred[m].min()), max(y[m].max(), pred[m].max())]
ax.plot(lims, lims, "k--", lw=0.8)
ax.set_xlabel("y_true"); ax.set_ylabel("y_pred"); ax.set_title("OOF vs true")
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 10. LightGBM hyperparameters snapshot"),
        ("code", '''print(json.dumps(metrics.get("params", metrics.get("lgbm_params", {})), indent=2)[:1200])
'''),
        ("markdown", "## 11. Training row count actually used"),
        ("code", '''print("n_train_rows:", transform.get("n_train_rows"), "max_rows:", transform.get("max_rows_applied"))
'''),
        ("markdown", "## 12. Fold RMSE distribution"),
        ("code", '''import pandas as pd
pd.Series(fold_rmses).describe()
'''),
        ("markdown", "## 13. Public kernel benchmark note"),
        ("markdown", "Top Rogii public notebooks (May 2026) report CV/public scores roughly **9.2–10.2** for strong solutions and **13–15** for starters — use `cv_rmse` to track iteration."),
        ("markdown", "## 14. Compare to public LightGBM baselines"),
        ("code", '''print("cv_rmse:", metrics.get("cv_rmse"))
'''),
        ("markdown", "## 15. Trace steps"),
        ("code", '''print("trace steps:", len(trace_steps_for_phase(PHASE)))
'''),
        ("markdown", "## 16. Model artifact paths"),
        ("code", '''for k, v in manifest["outputs"].items():
    print(k, "→", v)
'''),
        ("markdown", "## 17. Leaderboard context (May 2026)\n\nTop public Rogii kernels report **~9.2–9.9** public LB; starter baselines sit **13–15** CV. Track `cv_rmse` against this band while iterating features."),
        ("markdown", "## 18. Handoff to evaluation\n\nPhase 05 consumes `oof_predictions.npy` and `transform.json` for residual diagnostics."),
    )


def cells_05_evaluation() -> list[tuple[str, str]]:
    return _cells(
        ("markdown", f"""# 05 — OOF evaluation & residual analysis

**Variant:** `{VARIANT}` · Error analysis by depth and residual distribution (competition post-train diagnostics).
"""),
        ("code", COMMON_IMPORTS.format(nb_dir=NB_DIR) + "\nPHASE = \"05_evaluation\"\n"),
        ("markdown", "## 1. Load training predictions"),
        ("code", '''require_prior_phase(PHASE)
p01 = load_phase_manifest("01_data_analysis")
p04 = load_phase_manifest("04_model_training")
paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
transform = _read_json(_resolve_path(p04["outputs"]["transform"]))
target = transform["target_column"]
train_df = pd.read_csv(paths["train_csv"])
tp = _load_train_predict(); train_df = tp.align_train_target_to_schema(train_df, target)
oof = np.load(_resolve_path(p04["outputs"]["oof_predictions"]))
y_true = train_df[target].astype(float).values
'''),
        ("markdown", "## 2. Recompute OOF RMSE"),
        ("code", '''if transform.get("use_log1p"):
    pred = np.expm1(np.clip(oof, None, 20))
else:
    pred = oof
mask = np.isfinite(pred) & np.isfinite(y_true)
rmse = tp.rmse(y_true[mask], pred[mask])
print("OOF RMSE:", rmse)
'''),
        ("markdown", "## 3. Residual distribution"),
        ("code", '''residual = y_true[mask] - pred[mask]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
axes[0].hist(residual, bins=40, color="crimson", alpha=0.85)
axes[0].set_title("Residual histogram")
axes[1].scatter(pred[mask], residual, s=4, alpha=0.3)
axes[1].axhline(0, color="k", lw=0.8)
axes[1].set_xlabel("y_pred"); axes[1].set_ylabel("residual")
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 4. Residuals vs measured depth"),
        ("code", '''if "MD" in train_df.columns:
    md = train_df.loc[mask, "MD"].values
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.scatter(md, np.abs(residual), s=4, alpha=0.25)
    ax.set_xlabel("MD"); ax.set_ylabel("|residual|"); ax.set_title("Absolute error vs depth")
    plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 5. Predicted vs true (OOF)"),
        ("code", '''fig, ax = plt.subplots(figsize=(5, 5))
ax.scatter(y_true[mask], pred[mask], s=4, alpha=0.25)
lims = [min(y_true[mask].min(), pred[mask].min()), max(y_true[mask].max(), pred[mask].max())]
ax.plot(lims, lims, "k--", lw=0.8)
ax.set_xlabel("y_true"); ax.set_ylabel("y_pred")
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 6. Error by target quantile bin"),
        ("code", '''bins = pd.qcut(y_true[mask], q=5, duplicates="drop")
err_by_bin = pd.DataFrame({"y": y_true[mask], "abs_err": np.abs(residual), "bin": bins})
err_by_bin.groupby("bin", observed=True)["abs_err"].mean()
'''),
        ("markdown", "## 7. Well-level error (if group key available)"),
        ("code", '''from pipeline import well_group_detector as wgd
id_col = _read_json(_resolve_path(p01["outputs"]["schema"]))["id_column"]
gk = wgd.recommend_group_key(train_df, None, id_column=id_col)
if gk and gk in train_df.columns:
    tmp = train_df.loc[mask, [gk]].copy()
    tmp["abs_err"] = np.abs(residual)
    print(tmp.groupby(gk)["abs_err"].mean().sort_values(ascending=False).head())
else:
    print("No well group column for per-well error breakdown")
'''),
        ("markdown", "## 8. Competition diagnostic note\n\nTop Rogii writeups emphasize **depth-stratified** and **leakage-aware** error views — this phase mirrors that post-train analysis before submission."),
        ("markdown", "## 9. RMSE vs MAE summary"),
        ("code", '''mae = np.mean(np.abs(residual))
print({"rmse": float(rmse), "mae": float(mae), "n_oof": int(mask.sum())})
'''),
        ("markdown", "## 10. Residual skewness"),
        ("code", '''from scipy.stats import skew
print("residual skew:", skew(residual))
'''),
        ("markdown", "## 11. Mean absolute error by quantile"),
        ("code", '''abs_err = np.abs(residual)
pd.Series(abs_err).describe()
'''),
        ("markdown", "## 12. Residual autocorrelation along index"),
        ("code", '''if len(residual) > 10:
    ac1 = np.corrcoef(residual[:-1], residual[1:])[0, 1]
    print("lag-1 residual autocorr:", ac1)
'''),
        ("markdown", "## 13. Persist evaluation artifacts"),
        ("code", '''from phase_runner import run_05_evaluation
manifest = run_05_evaluation()
print(json.dumps(manifest, indent=2))
'''),
        ("markdown", "## 14. Metrics JSON"),
        ("code", '''metrics = _read_json(_resolve_path(manifest["outputs"]["metrics"]))
print(json.dumps(metrics, indent=2))
'''),
        ("markdown", "## 15. Residuals CSV head"),
        ("code", '''res_path = _resolve_path(manifest["outputs"]["residuals"])
display(pd.read_csv(res_path).head())
'''),
        ("markdown", "## 16. Depth-binned error summary"),
        ("code", '''depth_path = ARTIFACTS_ROOT / PHASE / "residuals_by_depth.json"
if depth_path.is_file():
    print(json.dumps(_read_json(depth_path), indent=2))
'''),
        ("markdown", "## 17. Q-Q plot (normality check on residuals)"),
        ("code", '''import scipy.stats as stats
fig, ax = plt.subplots(figsize=(4, 4))
stats.probplot(residual, dist="norm", plot=ax)
ax.set_title("Residual Q-Q")
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 18. Trace coverage"),
        ("code", '''print("trace steps:", len(trace_steps_for_phase(PHASE)))
'''),
        ("markdown", "## 19. Evaluation artifact checklist"),
        ("code", '''for name in ["metrics.json", "residuals.csv", "residuals_by_depth.json", "phase_manifest.json"]:
    p = ARTIFACTS_ROOT / PHASE / name
    print(name, "OK" if p.is_file() else "MISSING")
'''),
        ("markdown", "## 20. Handoff to submission\n\nPhase 06 validates the submission CSV against `sample_submission.csv` row order and column schema."),
    )


def cells_06_submission() -> list[tuple[str, str]]:
    return _cells(
        ("markdown", f"""# 06 — Submission formatting & validation

**Variant:** `{VARIANT}` · Align test predictions to `sample_submission.csv` ids and validate envelope.
"""),
        ("code", COMMON_IMPORTS.format(nb_dir=NB_DIR) + "\nPHASE = \"06_submission\"\n"),
        ("markdown", "## 1. Submission contract"),
        ("code", '''p01 = load_phase_manifest("01_data_analysis")
paths = _read_json(_resolve_path(p01["outputs"]["data_paths"]))
schema = _read_json(_resolve_path(p01["outputs"]["schema"]))
sample_sub = pd.read_csv(paths["sample_submission_csv"])
print("required columns:", schema["id_column"], schema["target_columns"])
print("submission rows expected:", len(sample_sub))
display(sample_sub.head())
'''),
        ("markdown", "## 2. Load model transform"),
        ("code", '''p04 = load_phase_manifest("04_model_training")
transform = _read_json(_resolve_path(p04["outputs"]["transform"]))
test_mat = np.load(_resolve_path(p04["outputs"]["test_preds_per_fold"]))
print("test fold preds shape:", test_mat.shape)
'''),
        ("markdown", "## 3. Mean test prediction vector"),
        ("code", '''test_mean = test_mat.mean(axis=1)
if transform.get("use_log1p"):
    test_pred = np.expm1(np.clip(test_mean, None, 20))
else:
    test_pred = test_mean
print("test_pred:", test_pred.shape, "min/max", np.nanmin(test_pred), np.nanmax(test_pred))
'''),
        ("markdown", "## 4. Build submission via phase_runner"),
        ("code", '''from phase_runner import run_06_submission
manifest = run_06_submission()
print(json.dumps(manifest, indent=2))
'''),
        ("markdown", "## 5. Validation report"),
        ("code", '''report = _read_json(_resolve_path(manifest["outputs"]["validation_report"]))
print(json.dumps(report, indent=2))
assert report.get("ok"), report
'''),
        ("markdown", "## 6. Submission preview"),
        ("code", '''sub = pd.read_csv(_resolve_path(manifest["outputs"]["submission_csv"]))
display(sub.head(10))
display(sub.tail(5))
print(sub.describe())
'''),
        ("markdown", "## 7. Target distribution vs train"),
        ("code", '''train_df = pd.read_csv(paths["train_csv"])
target = transform["target_column"]
train_df = _load_train_predict().align_train_target_to_schema(train_df, target)
fig, ax = plt.subplots(figsize=(8, 3))
ax.hist(train_df[target].dropna(), bins=40, alpha=0.5, label="train TVT", density=True)
ax.hist(sub[schema["target_columns"][0]], bins=40, alpha=0.5, label="submission", density=True)
ax.legend(); ax.set_title("Train vs submission TVT density")
plt.tight_layout(); plt.show()
'''),
        ("markdown", "## 8. Id alignment spot-check"),
        ("code", '''merged = sample_sub.merge(sub, on=schema["id_column"], suffixes=("_sample", "_pred"))
print("matched ids:", len(merged), "/", len(sample_sub))
'''),
        ("markdown", "## 9. Per-well prediction count"),
        ("code", '''well_prefix = sub[schema["id_column"]].astype(str).str.split("_").str[0]
print(well_prefix.value_counts().describe())
'''),
        ("markdown", "## 10. Submission file size and path"),
        ("code", '''sub_path = _resolve_path(manifest["outputs"]["submission_csv"])
print(sub_path, sub_path.stat().st_size, "bytes")
'''),
        ("markdown", "## 11. Negative / out-of-range submission check"),
        ("code", '''tcol = schema["target_columns"][0]
print("min:", sub[tcol].min(), "max:", sub[tcol].max(), "any_na:", sub[tcol].isna().any())
'''),
        ("markdown", "## 12. Row count contract"),
        ("code", '''assert len(sub) == len(sample_sub), (len(sub), len(sample_sub))
print("row count OK")
'''),
        ("markdown", "## 13. Kaggle submit command (manual)"),
        ("markdown", "```bash\nkaggle competitions submit -c rogii-wellbore-geology-prediction \\\n  -f examples/rogii/traces/preprocessing/baseline_column_transformer/artifacts/06_submission/submission.csv \\\n  -m \"baseline_column_transformer phase 06\"\n```"),
        ("markdown", "## 14. Pipeline complete"),
        ("code", '''state = _read_json(ARTIFACTS_ROOT / "pipeline_state.json")
print(json.dumps(state, indent=2))
'''),
        ("markdown", "## 15. Full artifact tree"),
        ("code", '''for phase_dir in sorted(ARTIFACTS_ROOT.iterdir()):
    if phase_dir.is_dir():
        files = list(phase_dir.glob("*"))
        print(phase_dir.name, "→", len(files), "files")
'''),
        ("markdown", "## 16. Trace pipeline summary"),
        ("code", '''total_steps = sum(len(trace_steps_for_phase(p)) for p in [
    "01_data_analysis", "02_statistical_framework", "03_feature_engineering",
    "04_model_training", "05_evaluation", "06_submission"])
print("total trace steps across 6 phases:", total_steps)
'''),
        ("markdown", "## 17. Reproducibility note\n\nFull-scale training and submission should be executed via **Slurm** (`sbatch`) per project rules — this notebook validates the submission envelope on login node when artifacts exist."),
        ("markdown", "## 18. Next steps\n\n1. Submit via Kaggle CLI (section 13)\n2. Compare duration track ablation grid from phase 02\n3. Compare public LB score to phase 04/05 `cv_rmse`"),
    )


PHASE_CELL_BUILDERS = {
    "01_data_analysis": cells_01_data_analysis,
    "02_statistical_framework": cells_02_statistical_framework,
    "03_feature_engineering": cells_03_feature_engineering,
    "04_model_training": cells_04_model_training,
    "05_evaluation": cells_05_evaluation,
    "06_submission": cells_06_submission,
}
