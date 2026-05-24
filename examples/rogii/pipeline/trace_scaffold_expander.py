"""Trace scaffold expander: audit gaps, apply scaffolding, verify handoffs.

Type-2 utility agent used by ``expander_agent.py`` CLI and
:class:`TraceScaffoldExpander`` in ``rogii.pipeline.agents`` (when importable).
"""

from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

PHASE_ORDER = [
    "01_data_analysis",
    "02_statistical_framework",
    "03_feature_engineering",
    "04_model_training",
    "05_evaluation",
    "06_submission",
]

VARIANTS = (
    "baseline_column_transformer",
    "typewell_gr_alignment",
    "ps_point_leakage_aware",
    "robust_scale_log1p",
    "parallel_multiwell_loader",
    "formation_plane_spatial",
)

SCAFFOLD_FILES = (
    "trace_language.csv",
    "experiment_descriptor.json",
    "ablation_plan.json",
    "mle_plan.json",
    "run_pipeline.sh",
    "statistical_framework.md",
    "paper_refs.md",
)

NOTEBOOKS = tuple(f"notebooks/{p}.ipynb" for p in PHASE_ORDER)


@dataclass
class GapReport:
    variant: str
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.errors


@dataclass
class ExpandResult:
    variant: str
    actions: list[str] = field(default_factory=list)
    gap_after: GapReport | None = None


def _variant_dir(examples_root: Path, variant: str) -> Path:
    return examples_root / "traces" / "preprocessing" / variant


def _import_handoff_verifier(examples_root: Path):
    script = examples_root / "hpcc" / "verify_phase_handoff.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("verify_phase_handoff", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slurm_six_phase_status(variant_dir: Path) -> str:
    """Return done/partial/not_started for the 6-phase Slurm scaffold pipeline."""
    manifests = [
        variant_dir / "artifacts" / phase / "phase_manifest.json" for phase in PHASE_ORDER
    ]
    present = sum(1 for m in manifests if m.is_file())
    if present == 0:
        return "not_started"
    submission = variant_dir / "artifacts" / "06_submission" / "submission.csv"
    if present == len(PHASE_ORDER) and submission.is_file():
        return "done"
    return "partial"


def audit_variant(examples_root: Path, variant: str) -> GapReport:
    """List missing scaffold files and handoff errors for one variant."""
    report = GapReport(variant=variant)
    vdir = _variant_dir(examples_root, variant)
    if not vdir.is_dir():
        report.errors.append(f"variant directory missing: {vdir}")
        return report

    for phase in PHASE_ORDER:
        contract = vdir / "artifacts" / phase / "PHASE_CONTRACT.json"
        if not contract.is_file():
            report.missing.append(f"artifacts/{phase}/PHASE_CONTRACT.json")

    for name in SCAFFOLD_FILES:
        if not (vdir / name).is_file():
            report.missing.append(name)

    for nb in NOTEBOOKS:
        if not (vdir / nb).is_file():
            report.missing.append(nb)

    for path in ("notebooks/phase_runner.py", "notebooks/phase_notebook_cells.py"):
        if not (vdir / path).is_file():
            report.missing.append(path)

    verifier = _import_handoff_verifier(examples_root)
    if verifier is not None:
        errors = verifier.verify_chain_alignment(vdir)
        report.errors.extend(errors)
    elif any((vdir / "artifacts" / p / "phase_manifest.json").is_file() for p in PHASE_ORDER):
        report.warnings.append("verify_phase_handoff.py unavailable; skipped chain check")

    return report


def _run(cmd: list[str], *, cwd: Path, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    if not quiet:
        print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _write_design_artifacts(variant: str, *, quiet: bool) -> list[str]:
    """Write ablation plan, experiment descriptor, and enriched mle_plan via rogii script."""
    actions: list[str] = []
    rogii_root = Path("/lustre/work/sweeden/rogii")
    eda_script = rogii_root / "scripts" / "experiment_design_architect.py"
    if not eda_script.is_file():
        return actions
    for flag in ("--write-ablation-plan", "--write-experiment-descriptor", "--enrich-mle-plan"):
        proc = _run(
            [sys.executable, str(eda_script), "--variant", variant, flag, "-q"],
            cwd=rogii_root,
            quiet=quiet,
        )
        if proc.returncode == 0:
            actions.append(f"experiment_design_architect {flag}")
    return actions


def expand_variant(
    examples_root: Path,
    variant: str,
    *,
    sync_worktree: bool = False,
    write_design_artifacts: bool = True,
    quiet: bool = False,
) -> ExpandResult:
    """Scaffold one variant and optionally write experiment-design artifacts."""
    result = ExpandResult(variant=variant)
    repo_root = examples_root.parent.parent
    scaffold_script = examples_root / "scripts" / "scaffold_trace_variant.py"

    if scaffold_script.is_file():
        cmd = [sys.executable, str(scaffold_script), "--variant", variant]
        if sync_worktree:
            cmd.append("--sync-worktrees")
        proc = _run(cmd, cwd=repo_root, quiet=quiet)
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            result.actions.append(f"scaffold FAILED: {err}")
        else:
            for line in proc.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("===") or stripped.startswith("("):
                    continue
                if stripped:
                    result.actions.append(stripped)

    if write_design_artifacts:
        result.actions.extend(_write_design_artifacts(variant, quiet=quiet))

    index_script = examples_root / "scripts" / "write_trace_row_index.py"
    trace_csv = _variant_dir(examples_root, variant) / "trace_language.csv"
    index_csv = _variant_dir(examples_root, variant) / "trace_row_index.csv"
    if index_script.is_file() and trace_csv.is_file() and not index_csv.is_file():
        proc = _run(
            [sys.executable, str(index_script), "--variant", variant],
            cwd=repo_root,
            quiet=quiet,
        )
        if proc.returncode == 0 and index_csv.is_file():
            result.actions.append("generated trace_row_index.csv")

    result.gap_after = audit_variant(examples_root, variant)
    return result


def expand_all_variants(
    examples_root: Path,
    *,
    sync_worktrees: bool = True,
    write_design_artifacts: bool = True,
    run_pytest: bool = True,
    quiet: bool = False,
) -> dict[str, Any]:
    """Expand scaffolding for all six trace variants."""
    summary: dict[str, Any] = {"variants": {}, "pytest": None, "tracking_csv": None}
    for variant in VARIANTS:
        summary["variants"][variant] = expand_variant(
            examples_root,
            variant,
            sync_worktree=sync_worktrees,
            write_design_artifacts=write_design_artifacts,
            quiet=quiet,
        )

    if run_pytest:
        tests = examples_root / "tests" / "test_variant_hooks.py"
        if tests.is_file():
            proc = _run(
                [sys.executable, "-m", "pytest", str(tests), "-q"],
                cwd=examples_root,
                quiet=quiet,
            )
            summary["pytest"] = {
                "status": "pass" if proc.returncode == 0 else "fail",
                "exit_code": proc.returncode,
                "output": (proc.stdout + proc.stderr)[-4000:],
            }

    summary["tracking_csv"] = sync_tracking_with_pipeline_status(examples_root)
    return summary


def sync_tracking_with_pipeline_status(examples_root: Path) -> Path | None:
    """Refresh ablation_tracking_status.csv including slurm six-phase completion."""
    rogii_root = Path("/lustre/work/sweeden/rogii")
    eda_script = rogii_root / "scripts" / "experiment_design_architect.py"
    tracking_csv = examples_root / "ablation_tracking_status.csv"
    if not eda_script.is_file():
        return None

    _run(
        [sys.executable, str(eda_script), "--variant", VARIANTS[0], "--sync-tracking", "-q"],
        cwd=rogii_root,
        quiet=True,
    )

    canonical = Path("/lustre/work/sweeden/agent-tracing/examples/rogii/ablation_tracking_status.csv")
    source = canonical if canonical.is_file() else tracking_csv
    if not source.is_file():
        return None

    rows: list[dict[str, str]] = []
    with source.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        skip_cols = {
            "overall_pct",
            "status",
            "last_updated",
            "experiment_id",
            "variant_slug",
            "branch",
            "mle_approach",
            "github_issue",
            "pr_agent_tracing",
        }
        for row in reader:
            variant = row.get("variant_slug", "")
            if variant:
                vdir = _variant_dir(examples_root, variant)
                row["slurm_full_pipeline"] = slurm_six_phase_status(vdir)
                check_cols = [k for k in row if k not in skip_cols]
                done = sum(1 for k in check_cols if row.get(k) == "done")
                partial = sum(1 for k in check_cols if row.get(k) == "partial")
                total = len(check_cols)
                row["overall_pct"] = str(int(round(100 * (done + 0.5 * partial) / max(total, 1))))
                row["status"] = "done" if done >= total else ("partial" if done + partial > 0 else "not_started")
                row["last_updated"] = date.today().isoformat()
            rows.append(row)

    for dest in (tracking_csv, canonical):
        if dest.parent.is_dir():
            with dest.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

    return tracking_csv


class TraceScaffoldExpander:
    """Type-2 agent: expand trace variant scaffolding and repair handoff gaps."""

    def __init__(self, agent_tracing_root: Path | str | None = None) -> None:
        root = Path(agent_tracing_root or "/lustre/work/sweeden/agent-tracing-trace-baseline")
        self.examples_root = root / "examples" / "rogii"
        self.audit_log: list[dict] = []

    def audit_scaffold_gaps(self, variant: str | None = None) -> list[GapReport]:
        variants = [variant] if variant else list(VARIANTS)
        reports = [audit_variant(self.examples_root, v) for v in variants]
        for r in reports:
            self.audit_log.append(
                {"variant": r.variant, "ok": r.ok, "missing": r.missing, "errors": r.errors}
            )
        return reports

    def expand_variant_scaffold(self, variant: str, *, sync_worktree: bool = True) -> ExpandResult:
        return expand_variant(
            self.examples_root,
            variant,
            sync_worktree=sync_worktree,
            write_design_artifacts=True,
        )

    def expand_all_variant_scaffolds(self, *, sync_worktrees: bool = True) -> dict[str, Any]:
        return expand_all_variants(self.examples_root, sync_worktrees=sync_worktrees)

    def repair_phase_handoff_chain(self, variant: str) -> list[str]:
        expand_variant(self.examples_root, variant, sync_worktree=False, write_design_artifacts=False)
        return audit_variant(self.examples_root, variant).errors

    def sync_tracking_matrix(self) -> Path | None:
        return sync_tracking_with_pipeline_status(self.examples_root)

    def record_scaffold_expansion(self, summary: dict[str, Any]) -> dict:
        entry = {
            "recorded": True,
            "variants": len(summary.get("variants", {})),
            "pytest": summary.get("pytest"),
        }
        self.audit_log.append(entry)
        return entry
