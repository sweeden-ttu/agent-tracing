#!/usr/bin/env python3
"""Wire Rogii trace variants to PaperBench (frontier-evals) for paper-driven reproduction.

Uses PDFs under ``agent-tracing-trace-baseline/examples/rogii/papers/`` and the
live Rogii ML pipeline at ``/lustre/work/sweeden/rogii``.

Usage::

    python examples/rogii/scripts/run_paperbench_rogii_gate.py
    python examples/rogii/scripts/run_paperbench_rogii_gate.py --write-descriptors
    python examples/rogii/scripts/run_paperbench_rogii_gate.py --execute-orchestrator typewell_gr_alignment
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROGII_EXAMPLES = Path(__file__).resolve().parents[1]
TRACE_BASELINE = ROGII_EXAMPLES
ROGII_ROOT = Path("/lustre/work/sweeden/rogii")
FRONTIER_PAPERBENCH = Path("/lustre/work/sweeden/frontier-evals/project/paperbench")

VARIANTS = (
    "baseline_column_transformer",
    "typewell_gr_alignment",
    "ps_point_leakage_aware",
    "robust_scale_log1p",
    "parallel_multiwell_loader",
    "formation_plane_spatial",
)


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-descriptors", action="store_true")
    parser.add_argument("--sync-papers", action="store_true")
    parser.add_argument("--validate-traces", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run-all", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--execute-orchestrator", metavar="VARIANT")
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    if not FRONTIER_PAPERBENCH.is_dir():
        print(f"PaperBench not found: {FRONTIER_PAPERBENCH}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["ROGII_ROOT"] = str(TRACE_BASELINE)
    env["ROGII_PAPERS_ROOT"] = str(TRACE_BASELINE / "papers")

    if args.sync_papers or args.write_descriptors:
        _run(
            [sys.executable, "-m", "paperbench.scripts.sync_rogii_papers"],
            cwd=FRONTIER_PAPERBENCH,
            env=env,
        )

    if args.write_descriptors:
        _run(
            [
                sys.executable,
                "-m",
                "paperbench.scripts.write_experiment_descriptors",
                "--all-variants",
                "--rogii-root",
                str(TRACE_BASELINE),
            ],
            cwd=FRONTIER_PAPERBENCH,
            env=env,
        )

    if not args.skip_pytest:
        _run(
            [sys.executable, "-m", "pytest", "tests/unit/chomsky", "tests/unit/trace_pipeline", "-q"],
            cwd=FRONTIER_PAPERBENCH,
            env=env,
        )

    if args.validate_traces:
        _run(
            [sys.executable, "-m", "paperbench.scripts.implement_agent_tracing", "--validate-traces"],
            cwd=FRONTIER_PAPERBENCH,
            env=env,
        )

    if args.execute_orchestrator:
        _run(
            [
                sys.executable,
                "-m",
                "paperbench.trace_pipeline.orchestrator",
                "--variant",
                args.execute_orchestrator,
                "--execute",
            ],
            cwd=FRONTIER_PAPERBENCH,
            env={**env, "ROGII_ROOT": str(ROGII_ROOT)},
        )
    elif args.dry_run_all:
        for variant in VARIANTS:
            _run(
                [
                    sys.executable,
                    "-m",
                    "paperbench.trace_pipeline.orchestrator",
                    "--variant",
                    variant,
                    "--dry-run",
                ],
                cwd=FRONTIER_PAPERBENCH,
                env=env,
            )
            print(f"dry-run OK: {variant}")

    print("PaperBench Rogii gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
