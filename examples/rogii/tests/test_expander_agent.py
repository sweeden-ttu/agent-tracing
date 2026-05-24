"""Tests for trace scaffold expander."""

from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1]
sys_path = EXAMPLES
import sys

sys.path.insert(0, str(EXAMPLES))

from pipeline.trace_scaffold_expander import (  # noqa: E402
    audit_variant,
    slurm_six_phase_status,
)


@pytest.mark.parametrize(
    "variant",
    [
        "baseline_column_transformer",
        "typewell_gr_alignment",
        "ps_point_leakage_aware",
        "robust_scale_log1p",
        "parallel_multiwell_loader",
        "formation_plane_spatial",
    ],
)
def test_baseline_variants_have_core_scaffold(variant: str) -> None:
    report = audit_variant(EXAMPLES, variant)
    assert "trace_language.csv" not in report.missing
    assert "notebooks/phase_runner.py" not in report.missing
    for phase in (
        "01_data_analysis",
        "02_statistical_framework",
        "03_feature_engineering",
        "04_model_training",
        "05_evaluation",
        "06_submission",
    ):
        assert f"artifacts/{phase}/PHASE_CONTRACT.json" not in report.missing


def test_slurm_six_phase_done_for_completed_pipeline() -> None:
    vdir = EXAMPLES / "traces" / "preprocessing" / "baseline_column_transformer"
    assert slurm_six_phase_status(vdir) == "done"


def test_slurm_six_phase_not_started_empty(tmp_path: Path) -> None:
    vdir = tmp_path / "empty_variant"
    vdir.mkdir()
    assert slurm_six_phase_status(vdir) == "not_started"
