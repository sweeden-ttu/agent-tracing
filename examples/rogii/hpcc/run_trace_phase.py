#!/usr/bin/env python3
"""Run one trace pipeline phase on Slurm (invoked from run_trace_phase.slurm)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument(
        "--agent-tracing-root",
        type=Path,
        default=Path("/lustre/work/sweeden/agent-tracing-trace-baseline"),
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/lustre/work/sweeden/rogii/data"))
    parser.add_argument("--max-train-rows", type=int, default=None)
    args = parser.parse_args()

    nb_dir = (
        args.agent_tracing_root
        / "examples/rogii/traces/preprocessing"
        / args.variant
        / "notebooks"
    )
    if not (nb_dir / "phase_runner.py").is_file():
        print(f"FATAL: phase_runner not found under {nb_dir}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(nb_dir))
    rogii_root = Path("/lustre/work/sweeden/rogii")
    if str(rogii_root) not in sys.path:
        sys.path.insert(0, str(rogii_root))

    from phase_runner import run_phase  # noqa: WPS433

    kwargs: dict = {}
    if args.phase == "01_data_analysis":
        kwargs["data_dir"] = args.data_dir
    if args.phase == "04_model_training":
        kwargs["max_rows"] = args.max_train_rows

    print(f"=== run_phase {args.phase} variant={args.variant} ===")
    manifest = run_phase(args.phase, **kwargs)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
