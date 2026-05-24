"""Phase notebook runner: artifact handoffs for parallel_multiwell_loader.

Thin wrapper around ``_shared/phase_runner_core.py`` + ``_shared/variant_hooks.py``.
Regenerate: ``python examples/rogii/scripts/scaffold_trace_variant.py --variant parallel_multiwell_loader``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_VARIANT_DIR = Path(__file__).resolve().parents[1]
_SHARED = _VARIANT_DIR.parent / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from variant_hooks import load_hooks  # noqa: E402

import phase_runner_core as _core  # noqa: E402

_core.init_runner(_VARIANT_DIR, load_hooks(_VARIANT_DIR.name))

# Re-export for notebooks and hpcc/run_trace_phase.py
from phase_runner_core import *  # noqa: E402, F401, F403

run_phase = _core.run_phase
PHASE_RUNNERS = _core.PHASE_RUNNERS


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run trace phase ({_VARIANT_DIR.name})")
    parser.add_argument("phase", choices=list(PHASE_RUNNERS.keys()))
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--n-splits", type=int, default=5)
    args = parser.parse_args()
    kwargs: dict = {}
    if args.phase == "04_model_training":
        kwargs["max_rows"] = args.max_rows
        kwargs["n_splits"] = args.n_splits
    elif args.phase == "03_feature_engineering":
        kwargs["n_splits"] = args.n_splits
    manifest = run_phase(args.phase, **kwargs)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
