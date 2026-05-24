#!/usr/bin/env python3
"""Scaffold trace variant folders under examples/rogii/traces/preprocessing/.

Creates phase artifact directories, phase contracts, notebooks helpers, and
(optionally) copies trace specs from the canonical agent-tracing checkout.

Usage::

    python examples/rogii/scripts/scaffold_trace_variant.py --all-pending
    python examples/rogii/scripts/scaffold_trace_variant.py --variant typewell_gr_alignment
    python examples/rogii/scripts/scaffold_trace_variant.py --variant baseline_column_transformer --phases-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACES_ROOT = REPO_ROOT / "traces" / "preprocessing"
CANONICAL_ROOT = Path("/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing")

PHASE_ORDER = [
    "01_data_analysis",
    "02_statistical_framework",
    "03_feature_engineering",
    "04_model_training",
    "05_evaluation",
    "06_submission",
]

PHASE_CONTRACTS: dict[str, dict] = {
    "01_data_analysis": {
        "prior_phase": None,
        "outputs": {
            "schema": "artifacts/01_data_analysis/schema.json",
            "data_paths": "artifacts/01_data_analysis/data_paths.json",
            "well_groups": "artifacts/01_data_analysis/well_groups.json",
            "target_diagnosis": "artifacts/01_data_analysis/target_diagnosis.json",
            "eda_summary": "artifacts/01_data_analysis/eda_summary.json",
            "variant_scaffold": "artifacts/01_data_analysis/variant_scaffold.json",
        },
    },
    "02_statistical_framework": {
        "prior_phase": "01_data_analysis",
        "outputs": {
            "statistical_framework": "artifacts/02_statistical_framework/statistical_framework.json",
            "ablation_grid": "artifacts/02_statistical_framework/ablation_grid.json",
            "training_plan": "artifacts/02_statistical_framework/training_plan.json",
            "paper_citations": "artifacts/02_statistical_framework/paper_citations.json",
            "initial_adr": "artifacts/02_statistical_framework/initial_adr.md",
        },
    },
    "03_feature_engineering": {
        "prior_phase": "02_statistical_framework",
        "outputs": {
            "feature_config": "artifacts/03_feature_engineering/feature_config.json",
            "cv_config": "artifacts/03_feature_engineering/cv_config.json",
            "fold_indices": "artifacts/03_feature_engineering/fold_indices.json",
        },
        "optional_outputs": {
            "subdivision_by_well": "artifacts/03_feature_engineering/subdivision_by_well.json",
            "subdivision_by_depth": "artifacts/03_feature_engineering/subdivision_by_depth.json",
        },
    },
    "04_model_training": {
        "prior_phase": "03_feature_engineering",
        "outputs": {
            "transform": "artifacts/04_model_training/transform.json",
            "test_preds_per_fold": "artifacts/04_model_training/test_preds_per_fold.npy",
            "oof_predictions": "artifacts/04_model_training/oof_predictions.npy",
            "training_metrics": "artifacts/04_model_training/training_metrics.json",
        },
    },
    "05_evaluation": {
        "prior_phase": "04_model_training",
        "outputs": {
            "metrics": "artifacts/05_evaluation/metrics.json",
            "residuals": "artifacts/05_evaluation/residuals.csv",
        },
        "optional_outputs": {
            "residuals_by_depth": "artifacts/05_evaluation/residuals_by_depth.json",
        },
    },
    "06_submission": {
        "prior_phase": "05_evaluation",
        "outputs": {
            "submission_csv": "artifacts/06_submission/submission.csv",
            "validation_report": "artifacts/06_submission/validation_report.json",
        },
    },
}

SPEC_FILES = (
    "trace_language.csv",
    "experiment_descriptor.json",
    "ablation_plan.json",
    "mle_plan.json",
    "subdivision_manifest.json",
    "paper_refs.md",
    "statistical_framework.md",
    "environment.yml",
    "run_pipeline.sh",
)

NOTEBOOKS = tuple(f"{p}.ipynb" for p in PHASE_ORDER)

WORKTREE_ROOT = Path("/lustre/work/sweeden")
WORKTREE_BY_VARIANT: dict[str, str] = {
    "baseline_column_transformer": "agent-tracing-trace-baseline",
    "typewell_gr_alignment": "agent-tracing-trace-typewell",
    "ps_point_leakage_aware": "agent-tracing-trace-ps",
    "robust_scale_log1p": "agent-tracing-trace-robust",
    "parallel_multiwell_loader": "agent-tracing-trace-parallel",
    "formation_plane_spatial": "agent-tracing-trace-formation",
}

VARIANT_META: dict[str, dict[str, str]] = {
    "baseline_column_transformer": {
        "branch": "trace/baseline-column-transformer",
        "approach": "ColumnTransformer + LightGBM baseline",
        "base_paper": "Ke et al. 2017 LightGBM + Pedregosa et al. 2011 ColumnTransformer",
    },
    "typewell_gr_alignment": {
        "branch": "trace/typewell-gr-alignment",
        "approach": "GR/typewell alignment features",
        "base_paper": "Sakoe & Chiba 1978 DTW",
    },
    "ps_point_leakage_aware": {
        "branch": "trace/ps-point-leakage-aware",
        "approach": "PS-point detection + post-PS RMSE mask",
        "base_paper": "Kaufman et al. 2012 leakage",
    },
    "robust_scale_log1p": {
        "branch": "trace/robust-scale-log1p",
        "approach": "RobustScaler + log1p target",
        "base_paper": "Hampel et al. 1986 robust stats",
    },
    "parallel_multiwell_loader": {
        "branch": "trace/parallel-multiwell-loader",
        "approach": "Parallel IO + geology surfaces",
        "base_paper": "Rocklin 2015 Dask",
    },
    "formation_plane_spatial": {
        "branch": "trace/formation-plane-spatial",
        "approach": "Drilling geometry + formation KNN",
        "base_paper": "Cover & Hart 1967 k-NN",
    },
}


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _write_phase_contract(variant_dir: Path, phase: str) -> None:
    contract = {
        "variant": variant_dir.name,
        "phase": phase,
        "status": "pending",
        **PHASE_CONTRACTS[phase],
    }
    _write_json(variant_dir / "artifacts" / phase / "PHASE_CONTRACT.json", contract)


def _write_variant_readme(variant_dir: Path, variant: str) -> None:
    meta = VARIANT_META[variant]
    readme = variant_dir / "README.md"
    if readme.is_file():
        return
    readme.write_text(
        f"""# {variant}

**Branch:** `{meta["branch"]}`  
**Approach:** {meta["approach"]}  
**Base paper:** {meta["base_paper"]}

Scaffolded trace bundle. Run phases in order via `notebooks/phase_runner.py`.

| Phase | Artifact dir | Contract |
|-------|--------------|----------|
| 01 | `artifacts/01_data_analysis/` | `PHASE_CONTRACT.json` |
| 02 | `artifacts/02_statistical_framework/` | `PHASE_CONTRACT.json` |
| 03 | `artifacts/03_feature_engineering/` | `PHASE_CONTRACT.json` |
| 04 | `artifacts/04_model_training/` | `PHASE_CONTRACT.json` |
| 05 | `artifacts/05_evaluation/` | `PHASE_CONTRACT.json` |
| 06 | `artifacts/06_submission/` | `PHASE_CONTRACT.json` |

Regenerate trace index: ``python examples/rogii/scripts/write_trace_row_index.py --variant {variant}``

See [`../../README.md`](../../README.md) and [`../README.md`](../README.md).
""",
        encoding="utf-8",
    )


def _copy_specs(variant_dir: Path, variant: str) -> list[str]:
    copied: list[str] = []
    src_root = CANONICAL_ROOT / variant
    if not src_root.is_dir():
        return copied
    for name in SPEC_FILES:
        src = src_root / name
        dst = variant_dir / name
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)
            copied.append(name)
    nb_src = src_root / "notebooks"
    nb_dst = variant_dir / "notebooks"
    nb_dst.mkdir(parents=True, exist_ok=True)
    for name in NOTEBOOKS:
        src = nb_src / name
        dst = nb_dst / name
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)
            copied.append(f"notebooks/{name}")
    return copied


def _write_phase_runner(variant_dir: Path) -> None:
    """Install thin wrapper that delegates to ``_shared/phase_runner_core``."""
    template_path = TRACES_ROOT / "_shared" / "phase_runner_entry.py.txt"
    dst = variant_dir / "notebooks" / "phase_runner.py"
    variant_dir.joinpath("notebooks").mkdir(parents=True, exist_ok=True)
    text = template_path.read_text(encoding="utf-8").replace("{variant}", variant_dir.name)
    if not dst.is_file() or dst.read_text(encoding="utf-8") != text:
        dst.write_text(text, encoding="utf-8")


def _write_phase_notebook_cells(variant_dir: Path, variant: str, baseline_dir: Path) -> None:
    """Copy baseline cell definitions and set VARIANT slug."""
    src = baseline_dir / "notebooks" / "phase_notebook_cells.py"
    dst = variant_dir / "notebooks" / "phase_notebook_cells.py"
    if not src.is_file():
        return
    variant_dir.joinpath("notebooks").mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    text = text.replace('VARIANT = "baseline_column_transformer"', f'VARIANT = "{variant}"')
    meta = VARIANT_META.get(variant, {})
    if meta and "approach" in meta:
        text = text.replace(
            "ColumnTransformer + LightGBM baseline",
            meta["approach"],
            1,
        )
    if not dst.is_file() or dst.read_text(encoding="utf-8") != text:
        dst.write_text(text, encoding="utf-8")


def _write_write_phase_notebooks(variant_dir: Path, variant: str) -> None:
    baseline = TRACES_ROOT / "baseline_column_transformer" / "notebooks" / "write_phase_notebooks.py"
    dst = variant_dir / "notebooks" / "write_phase_notebooks.py"
    if dst.is_file():
        return
    if baseline.is_file():
        text = baseline.read_text(encoding="utf-8").replace(
            'VARIANT = "baseline_column_transformer"', f'VARIANT = "{variant}"'
        )
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(
        f'VARIANT = "{variant}"  # regenerate via baseline write_phase_notebooks.py\n',
        encoding="utf-8",
    )


def _write_notebooks_readme(variant_dir: Path) -> None:
    dst = variant_dir / "notebooks" / "README.md"
    if dst.is_file():
        return
    baseline = TRACES_ROOT / "baseline_column_transformer" / "notebooks" / "README.md"
    if baseline.is_file():
        shutil.copy2(baseline, dst)


def _write_pipeline_state(variant_dir: Path) -> None:
    path = variant_dir / "artifacts" / "pipeline_state.json"
    if path.is_file():
        return
    _write_json(
        path,
        {
            "last_completed_phase": None,
            "updated_at": None,
            "phases": {p: False for p in PHASE_ORDER},
        },
    )


def scaffold_variant(
    variant: str,
    *,
    phases_only: bool = False,
    baseline_dir: Path | None = None,
) -> list[str]:
    actions: list[str] = []
    variant_dir = TRACES_ROOT / variant
    variant_dir.mkdir(parents=True, exist_ok=True)
    baseline_dir = baseline_dir or TRACES_ROOT / "baseline_column_transformer"

    for phase in PHASE_ORDER:
        phase_dir = variant_dir / "artifacts" / phase
        phase_dir.mkdir(parents=True, exist_ok=True)
        contract_path = phase_dir / "PHASE_CONTRACT.json"
        if not contract_path.is_file():
            _write_phase_contract(variant_dir, phase)
            actions.append(f"wrote {contract_path.relative_to(REPO_ROOT)}")

    if phases_only:
        return actions

    copied = _copy_specs(variant_dir, variant)
    actions.extend(f"copied {c}" for c in copied)

    _write_phase_runner(variant_dir)
    actions.append(f"phase_runner.py (shared core) -> {variant}/notebooks/")

    _write_phase_notebook_cells(variant_dir, variant, baseline_dir)
    if (variant_dir / "notebooks" / "phase_notebook_cells.py").is_file():
        actions.append(f"phase_notebook_cells.py -> {variant}/notebooks/")

    _write_write_phase_notebooks(variant_dir, variant)
    _write_notebooks_readme(variant_dir)
    _write_variant_readme(variant_dir, variant)
    _write_pipeline_state(variant_dir)

    trace_csv = variant_dir / "trace_language.csv"
    index_csv = variant_dir / "trace_row_index.csv"
    if trace_csv.is_file() and not index_csv.is_file():
        script = REPO_ROOT / "scripts" / "write_trace_row_index.py"
        if script.is_file():
            subprocess.run(
                [sys.executable, str(script), "--variant", variant],
                check=False,
                cwd=str(REPO_ROOT.parent.parent),
            )
            if index_csv.is_file():
                actions.append(f"generated {index_csv.relative_to(REPO_ROOT)}")

    slurm_doc = variant_dir / "SLURM_INTERACTIVE_PREFLIGHT.md"
    baseline_slurm = baseline_dir / "SLURM_INTERACTIVE_PREFLIGHT.md"
    if baseline_slurm.is_file() and not slurm_doc.is_file():
        shutil.copy2(baseline_slurm, slurm_doc)
        actions.append(f"copied SLURM_INTERACTIVE_PREFLIGHT.md")

    return actions


def sync_dedicated_worktree(variant: str) -> list[str]:
    """Copy variant scaffolding into its dedicated git worktree checkout."""
    actions: list[str] = []
    repo_name = WORKTREE_BY_VARIANT.get(variant)
    if not repo_name or repo_name == "agent-tracing-trace-baseline":
        return actions
    wt_pre = WORKTREE_ROOT / repo_name / "examples" / "rogii" / "traces" / "preprocessing"
    src = TRACES_ROOT / variant
    dst = wt_pre / variant
    shared_src = TRACES_ROOT / "_shared"
    shared_dst = wt_pre / "_shared"
    if not src.is_dir():
        return actions
    wt_pre.mkdir(parents=True, exist_ok=True)
    if shared_src.is_dir():
        if shared_dst.is_dir():
            shutil.rmtree(shared_dst)
        shutil.copytree(shared_src, shared_dst, ignore=shutil.ignore_patterns("__pycache__"))
        actions.append(f"synced _shared/ -> {repo_name}")
    if dst.is_dir() and dst.resolve() != src.resolve():
        shutil.rmtree(dst)
    if not dst.exists():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "logs", "*.o*", "*.e*"))
        actions.append(f"synced worktree {repo_name} <- {variant}")
    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold Rogii trace variant directories.")
    parser.add_argument("--variant", action="append", help="Variant slug (repeatable).")
    parser.add_argument(
        "--all-pending",
        action="store_true",
        help="Scaffold all variants except baseline_column_transformer.",
    )
    parser.add_argument(
        "--phases-only",
        action="store_true",
        help="Only write artifact phase dirs + PHASE_CONTRACT.json.",
    )
    parser.add_argument(
        "--all-variants",
        action="store_true",
        help="Scaffold all six trace variants (including baseline).",
    )
    parser.add_argument(
        "--sync-worktrees",
        action="store_true",
        help="After scaffolding, sync dedicated agent-tracing-trace-* worktrees.",
    )
    parser.add_argument(
        "--regenerate-notebooks",
        action="store_true",
        help="Run write_phase_notebooks.py --all-variants after scaffolding.",
    )
    args = parser.parse_args()

    variants: list[str] = []
    if args.all_variants:
        variants = list(VARIANT_META.keys())
    elif args.all_pending:
        variants = [v for v in VARIANT_META if v != "baseline_column_transformer"]
    if args.variant:
        variants.extend(args.variant)
    if not variants:
        variants = ["baseline_column_transformer"]

    for variant in dict.fromkeys(variants):
        if variant not in VARIANT_META:
            raise SystemExit(f"Unknown variant: {variant}")
        actions = scaffold_variant(variant, phases_only=args.phases_only)
        print(f"\n=== {variant} ===")
        for line in actions or ["(nothing new — already scaffolded)"]:
            print(f"  {line}")
        if args.sync_worktrees:
            for line in sync_dedicated_worktree(variant):
                print(f"  {line}")

    if args.regenerate_notebooks and not args.phases_only:
        wp = TRACES_ROOT / "baseline_column_transformer" / "notebooks" / "write_phase_notebooks.py"
        if wp.is_file():
            subprocess.run(
                [sys.executable, str(wp), "--all-variants"],
                check=False,
                cwd=str(REPO_ROOT),
            )


if __name__ == "__main__":
    main()
