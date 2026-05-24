#!/usr/bin/env python3
"""Aggregate episodic TCN benchmark JSON across trace variants.

Reads ``artifacts/variants/{variant}/episodic_benchmark.json`` under the rogii
tree and prints a comparison table. Optionally writes a combined report.

Usage::

    python examples/rogii/scripts/benchmark_episodic_training.py
    python examples/rogii/scripts/benchmark_episodic_training.py --rogii-root /lustre/work/sweeden/rogii --write-json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROGII_ROOT = Path("/lustre/work/sweeden/rogii")
sys.path.insert(0, str(ROGII_ROOT))

from pipeline.episodic_benchmark import compare_variants  # noqa: E402

VARIANTS = (
    "baseline_column_transformer",
    "typewell_gr_alignment",
    "ps_point_leakage_aware",
    "robust_scale_log1p",
    "parallel_multiwell_loader",
    "formation_plane_spatial",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rogii-root", type=Path, default=ROGII_ROOT)
    parser.add_argument("--write-json", type=Path, help="Write combined benchmark report JSON")
    args = parser.parse_args()

    paths = [
        args.rogii_root / "artifacts" / "variants" / v / "episodic_benchmark.json"
        for v in VARIANTS
    ]
    rows = compare_variants(paths)
    if not rows:
        print("No episodic_benchmark.json files found.", file=sys.stderr)
        print("Run: sbatch hpcc/train_tcn_episodic.slurm with TRACE_VARIANT set per variant.")
        return 1

    print(f"{'variant':32} {'n_feat':6} {'eval_mask':14} {'oof_fit':10} {'oof_raw':10} {'best_ep':10}")
    print("-" * 90)
    for r in rows:
        print(
            f"{r['variant']:32} "
            f"{r.get('n_features') or '—':>6} "
            f"{str(r.get('eval_mask', '—')):14} "
            f"{_fmt(r.get('oof_rmse')):>10} "
            f"{_fmt(r.get('oof_rmse_raw_scale')):>10} "
            f"{_fmt(r.get('best_episode_val_rmse')):>10}"
        )

    if args.write_json:
        out = {"variants": rows}
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nwrote {args.write_json}")

    return 0


def _fmt(x) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):.4f}"
    except (TypeError, ValueError):
        return str(x)


if __name__ == "__main__":
    raise SystemExit(main())
