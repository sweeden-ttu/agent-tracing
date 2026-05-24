#!/usr/bin/env python3
"""Trace scaffold expander agent — audit gaps, scaffold all variants, verify handoffs.

Runs on the login node (no Slurm training). Use before submitting phase jobs or when
a variant worktree is missing notebooks, contracts, or design artifacts.

Usage::

    python examples/rogii/scripts/expander_agent.py --audit
    python examples/rogii/scripts/expander_agent.py --expand-all
    python examples/rogii/scripts/expander_agent.py --variant formation_plane_spatial --expand
    python examples/rogii/scripts/expander_agent.py --expand-all --validate-traces
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXAMPLES_ROOT.parent.parent
sys.path.insert(0, str(EXAMPLES_ROOT))

from pipeline.trace_scaffold_expander import (  # noqa: E402
    VARIANTS,
    TraceScaffoldExpander,
    audit_variant,
    expand_all_variants,
    expand_variant,
)

FRONTIER_PAPERBENCH = Path("/lustre/work/sweeden/frontier-evals/project/paperbench")


def _default_agent_tracing_root() -> Path:
    env = os.environ.get("AGENT_TRACING_ROOT")
    if env:
        return Path(env)
    return REPO_ROOT


def _print_audit(reports) -> int:
    exit_code = 0
    for report in reports:
        status = "OK" if report.ok else "GAPS"
        print(f"\n=== {report.variant} [{status}] ===")
        if report.missing:
            print("  missing:")
            for m in report.missing:
                print(f"    - {m}")
        if report.errors:
            print("  handoff errors:")
            for e in report.errors:
                print(f"    - {e}")
        if report.warnings:
            print("  warnings:")
            for w in report.warnings:
                print(f"    - {w}")
        if not report.ok:
            exit_code = 1
    return exit_code


def _run_validate_traces(agent_tracing_root: Path) -> int:
    if not FRONTIER_PAPERBENCH.is_dir():
        print(f"PaperBench not found: {FRONTIER_PAPERBENCH}", file=sys.stderr)
        return 1
    env = os.environ.copy()
    env["ROGII_ROOT"] = str(agent_tracing_root / "examples" / "rogii")
    cmd = [
        sys.executable,
        "-m",
        "paperbench.scripts.implement_agent_tracing",
        "--validate-traces",
        "--rogii-root",
        str(env["ROGII_ROOT"]),
    ]
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=FRONTIER_PAPERBENCH, env=env)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-tracing-root",
        type=Path,
        default=None,
        help="Worktree root (default: AGENT_TRACING_ROOT or this repo)",
    )
    parser.add_argument("--variant", action="append", help="Limit to variant slug(s)")
    parser.add_argument("--audit", action="store_true", help="Audit only; exit 1 if gaps remain")
    parser.add_argument("--expand", action="store_true", help="Expand scaffold for --variant")
    parser.add_argument(
        "--expand-all",
        action="store_true",
        help="Scaffold all six variants, sync worktrees, pytest, sync tracking",
    )
    parser.add_argument("--no-sync-worktrees", action="store_true")
    parser.add_argument("--no-design-artifacts", action="store_true")
    parser.add_argument("--no-pytest", action="store_true")
    parser.add_argument(
        "--validate-traces",
        action="store_true",
        help="Run PaperBench Chomsky validate-traces after expand",
    )
    parser.add_argument("--json-report", type=Path, help="Write machine-readable summary JSON")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    agent_root = args.agent_tracing_root or _default_agent_tracing_root()
    examples_root = agent_root / "examples" / "rogii"
    expander = TraceScaffoldExpander(agent_tracing_root=agent_root)

    variants = args.variant or list(VARIANTS)
    if not args.audit and not args.expand and not args.expand_all:
        parser.print_help()
        return 0

    exit_code = 0

    if args.audit:
        reports = expander.audit_scaffold_gaps(variants[0] if len(variants) == 1 and args.variant else None)
        if args.variant and len(variants) > 1:
            reports = [audit_variant(examples_root, v) for v in variants]
        exit_code = _print_audit(reports)

    if args.expand_all:
        summary = expand_all_variants(
            examples_root,
            sync_worktrees=not args.no_sync_worktrees,
            write_design_artifacts=not args.no_design_artifacts,
            run_pytest=not args.no_pytest,
            quiet=args.quiet,
        )
        expander.record_scaffold_expansion(summary)
        if not args.quiet:
            print("\n=== expand-all summary ===")
            for variant, result in summary["variants"].items():
                gap = result.gap_after
                ok = gap.ok if gap else False
                print(f"  {variant}: {'OK' if ok else 'GAPS'} ({len(result.actions)} actions)")
            if summary.get("pytest"):
                print(f"  pytest: {summary['pytest']['status']}")
            if summary.get("tracking_csv"):
                print(f"  tracking: {summary['tracking_csv']}")
        reports = [r.gap_after for r in summary["variants"].values() if r.gap_after]
        if any(not r.ok for r in reports):
            exit_code = 1
        if args.json_report:
            args.json_report.write_text(
                json.dumps(
                    {
                        "agent_tracing_root": str(agent_root),
                        "variants": {
                            v: {
                                "actions": summary["variants"][v].actions,
                                "ok": summary["variants"][v].gap_after.ok
                                if summary["variants"][v].gap_after
                                else None,
                            }
                            for v in summary["variants"]
                        },
                        "pytest": summary.get("pytest"),
                        "tracking_csv": str(summary.get("tracking_csv") or ""),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    elif args.expand:
        for variant in variants:
            if variant not in VARIANTS:
                print(f"Unknown variant: {variant}", file=sys.stderr)
                exit_code = 2
                continue
            result = expand_variant(
                examples_root,
                variant,
                sync_worktree=not args.no_sync_worktrees,
                write_design_artifacts=not args.no_design_artifacts,
                quiet=args.quiet,
            )
            if not args.quiet:
                print(f"\n=== {variant} ===")
                for line in result.actions or ["(no new scaffold actions)"]:
                    print(f"  {line}")
                if result.gap_after and not result.gap_after.ok:
                    exit_code = 1
                    _print_audit([result.gap_after])

    if args.validate_traces and exit_code == 0:
        vc = _run_validate_traces(agent_root)
        exit_code = max(exit_code, vc)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
