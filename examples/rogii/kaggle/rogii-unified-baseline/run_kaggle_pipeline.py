#!/usr/bin/env python3
"""Kaggle pipeline: baseline → RMSE gate (12 ft) → episodic TCN → ensemble → auto-submit."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_BUNDLE = Path(__file__).resolve().parent
if str(_BUNDLE) not in sys.path:
    sys.path.insert(0, str(_BUNDLE))

from run_baseline import resolve_data_dir, run as run_baseline, synthetic_oracle_rmse  # noqa: E402
from run_episodic_kaggle import run_episodic  # noqa: E402

RMSE_FEET_THRESHOLD = 12.0
COMPETITION_SLUG = "rogii-wellbore-geology-prediction"


def cumulative_rmse_feet(fold_rmses: list[float]) -> float:
    """Sum of per-fold OOF RMSE values (feet); used alongside mean cv_rmse for the gate."""
    return float(sum(fold_rmses))


def _validate_submission(submission: pd.DataFrame, sample_path: Path) -> dict:
    sample = pd.read_csv(sample_path)
    checks: list[dict] = []
    ok = True
    if len(submission) != len(sample):
        ok = False
        checks.append({"name": "row_count", "status": "fail"})
    else:
        checks.append({"name": "row_count", "status": "pass"})
    if list(submission.columns) != list(sample.columns):
        ok = False
        checks.append({"name": "columns", "status": "fail"})
    else:
        checks.append({"name": "columns", "status": "pass"})
    if submission.isna().any().any():
        ok = False
        checks.append({"name": "no_nans", "status": "fail"})
    else:
        checks.append({"name": "no_nans", "status": "pass"})
    return {"ok": ok, "checks": checks}


def blend_submissions(
    baseline_sub: pd.DataFrame,
    episodic_sub: pd.DataFrame,
    *,
    id_col: str,
    target_col: str,
    baseline_rmse: float,
    episodic_rmse: float,
) -> tuple[pd.DataFrame, dict]:
    """Inverse-RMSE weighted blend of tabular baseline and episodic TCN."""
    b = baseline_sub.copy()
    e = episodic_sub.copy()
    b[id_col] = b[id_col].astype(str)
    e[id_col] = e[id_col].astype(str)
    merged = b.merge(e, on=id_col, suffixes=("_base", "_epi"))
    w_base = 1.0 / max(baseline_rmse, 1e-6)
    w_epi = 1.0 / max(episodic_rmse, 1e-6)
    w_sum = w_base + w_epi
    wb, we = w_base / w_sum, w_epi / w_sum
    pred = wb * merged[f"{target_col}_base"] + we * merged[f"{target_col}_epi"]
    out = pd.DataFrame({id_col: merged[id_col], target_col: pred})
    meta = {
        "blend_weights": {"tabular_baseline": wb, "episodic_tcn": we},
        "baseline_rmse_feet": baseline_rmse,
        "episodic_rmse_feet": episodic_rmse,
    }
    return out, meta


def submit_to_competition(
    submission_path: Path,
    *,
    message: str,
    competition: str = COMPETITION_SLUG,
) -> dict:
    """Submit via Kaggle CLI when available (notebook or login node with credentials)."""
    if not shutil.which("kaggle"):
        return {"submitted": False, "reason": "kaggle CLI not on PATH"}
    if os.environ.get("KAGGLE_KERNEL_RUN_TYPE") and not os.environ.get("KAGGLE_API_TOKEN"):
        # In-notebook: write for competition UI pickup; optional CLI if creds exist
        pass
    cmd = [
        "kaggle",
        "competitions",
        "submit",
        "-c",
        competition,
        "-f",
        str(submission_path),
        "-m",
        message,
        "-q",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        if proc.returncode != 0:
            return {
                "submitted": False,
                "reason": proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}",
                "command": " ".join(cmd),
            }
        return {"submitted": True, "message": message, "stdout": proc.stdout.strip()}
    except Exception as exc:
        return {"submitted": False, "reason": str(exc), "command": " ".join(cmd)}


def run_pipeline(
    data_dir: Path,
    work_dir: Path,
    *,
    rmse_threshold: float = RMSE_FEET_THRESHOLD,
    n_splits: int = 5,
    submit: bool = True,
    episodic_episodes: int = 2,
    episodic_epochs: int = 30,
) -> dict:
    work_dir.mkdir(parents=True, exist_ok=True)
    sample_path = data_dir / "sample_submission.csv"

    print("=== Phase 1: tabular baseline (GroupKFold / well groups) ===")
    baseline_metrics = run_baseline(data_dir, work_dir, n_splits=n_splits)
    cv_rmse = float(baseline_metrics["cv_rmse"])
    fold_rmses = [float(x) for x in baseline_metrics.get("fold_rmses", [])]
    cum_rmse = cumulative_rmse_feet(fold_rmses)

    gate_metric = cv_rmse
    trigger_episodic = gate_metric >= rmse_threshold
    print(
        f"RMSE gate: cv_rmse={cv_rmse:.4f} ft  cumulative_sum={cum_rmse:.4f} ft  "
        f"threshold={rmse_threshold}  trigger={trigger_episodic}"
    )

    baseline_sub = pd.read_csv(work_dir / "submission.csv")
    id_col = str(baseline_metrics.get("id_column", "id"))
    target_col = str(baseline_metrics.get("target_column", "tvt"))
    if sample_path.is_file():
        cols = list(pd.read_csv(sample_path, nrows=0).columns)
        id_col, target_col = cols[0], cols[1]

    final_sub = baseline_sub
    pipeline_meta: dict = {
        "rmse_threshold_feet": rmse_threshold,
        "baseline_cv_rmse_feet": cv_rmse,
        "baseline_cumulative_rmse_feet": cum_rmse,
        "episodic_triggered": trigger_episodic,
        "group_key": baseline_metrics.get("group_key"),
        "cv_scheme": baseline_metrics.get("cv_scheme"),
    }

    if trigger_episodic:
        print("=== Phase 2: episodic TCN (threshold exceeded) ===")
        epi = run_episodic(
            data_dir,
            work_dir,
            n_splits=n_splits,
            episodes_per_fold=episodic_episodes,
            max_epochs=episodic_epochs,
        )
        epi_sub = pd.read_csv(work_dir / "submission_episodic.csv")
        epi_cum = float(epi["cumulative_rmse_feet"])
        epi_oof = float(epi["oof_rmse_feet"])
        use_blend = epi_cum < cum_rmse
        pipeline_meta["episodic"] = epi
        pipeline_meta["ensemble_manifest"] = str(work_dir / "checkpoints" / "episode_manifest.json")

        if use_blend:
            print(
                f"=== Phase 3: ensemble blend (episodic cumulative {epi_cum:.4f} < baseline {cum_rmse:.4f}) ==="
            )
            final_sub, blend_meta = blend_submissions(
                baseline_sub,
                epi_sub,
                id_col=id_col,
                target_col=target_col,
                baseline_rmse=cv_rmse,
                episodic_rmse=epi_oof,
            )
            pipeline_meta["blend"] = blend_meta
        else:
            print(
                f"=== Episodic did not beat baseline cumulative RMSE "
                f"({epi_cum:.4f} >= {cum_rmse:.4f}); keeping tabular submission ==="
            )
            pipeline_meta["blend_skipped"] = {
                "reason": "episodic_cumulative_rmse_not_better_than_baseline",
                "baseline_cumulative_rmse_feet": cum_rmse,
                "episodic_cumulative_rmse_feet": epi_cum,
                "episodic_oof_rmse_feet": epi_oof,
            }

        print("=== Phase 4: re-run tabular with ensemble-informed fallback (optional refine) ===")
        refined = run_baseline(data_dir, work_dir / "refine_tabular", n_splits=n_splits)
        refined_rmse = float(refined["cv_rmse"])
        refined_cum = float(refined.get("cumulative_rmse_feet", cumulative_rmse_feet(refined.get("fold_rmses", []))))
        if refined_rmse < cv_rmse and use_blend:
            print(f"Refined tabular improved {cv_rmse:.4f} -> {refined_rmse:.4f}; re-blending")
            refined_sub = pd.read_csv(work_dir / "refine_tabular" / "submission.csv")
            final_sub, blend_meta = blend_submissions(
                refined_sub,
                epi_sub,
                id_col=id_col,
                target_col=target_col,
                baseline_rmse=refined_rmse,
                episodic_rmse=epi_oof,
            )
            pipeline_meta["refined_tabular_cv_rmse_feet"] = refined_rmse
            pipeline_meta["refined_tabular_cumulative_rmse_feet"] = refined_cum
            pipeline_meta["blend"] = blend_meta
        elif refined_rmse < cv_rmse:
            print(f"Refined tabular improved {cv_rmse:.4f} -> {refined_rmse:.4f}; using refined tabular only")
            final_sub = pd.read_csv(work_dir / "refine_tabular" / "submission.csv")
            pipeline_meta["refined_tabular_cv_rmse_feet"] = refined_rmse
            pipeline_meta["refined_tabular_cumulative_rmse_feet"] = refined_cum
            cv_rmse = refined_rmse
            cum_rmse = refined_cum
    else:
        print("=== Episodic training skipped (cv_rmse below threshold) ===")

    final_path = work_dir / "submission.csv"
    final_sub.to_csv(final_path, index=False)

    val = _validate_submission(final_sub, sample_path)
    pipeline_meta["submission_validation"] = val
    holdout = synthetic_oracle_rmse(
        final_sub,
        data_dir / "submission_samples" / "submission.csv",
        id_col=id_col,
        target_col=target_col,
    )
    pipeline_meta["holdout_rmse_synthetic"] = holdout

    submit_result: dict = {"submitted": False, "reason": "submit=False"}
    if submit:
        print("=== Phase 5: Kaggle competition submit ===")
        msg = (
            f"rogii-trace-unified cv={cv_rmse:.3f} "
            f"epi={'yes' if trigger_episodic else 'no'}"
        )
        submit_result = submit_to_competition(final_path, message=msg)
        pipeline_meta["kaggle_submit"] = submit_result
        if submit_result.get("submitted"):
            print("Kaggle submit OK:", submit_result.get("stdout", ""))
        else:
            print("Kaggle submit skipped/failed:", submit_result.get("reason"))

    out_metrics = {
        **baseline_metrics,
        **pipeline_meta,
        "final_cv_rmse_feet": cv_rmse,
        "final_cumulative_rmse_feet": cum_rmse,
        "final_submission": str(final_path),
    }
    metrics_path = work_dir / "pipeline_metrics.json"
    metrics_path.write_text(json.dumps(out_metrics, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {metrics_path}")
    return out_metrics


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="ROGII Kaggle pipeline with RMSE gate")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--work-dir", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--rmse-threshold", type=float, default=RMSE_FEET_THRESHOLD)
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--no-submit", action="store_true")
    ap.add_argument("--episodic-episodes", type=int, default=2)
    ap.add_argument("--episodic-epochs", type=int, default=30)
    args = ap.parse_args()
    try:
        data_dir = resolve_data_dir(args.data_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    run_pipeline(
        data_dir,
        args.work_dir.resolve(),
        rmse_threshold=args.rmse_threshold,
        n_splits=args.n_splits,
        submit=not args.no_submit,
        episodic_episodes=args.episodic_episodes,
        episodic_epochs=args.episodic_epochs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
