"""Regression tests for phase_runner and episodic benchmark fixes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROGII_ROOT = Path("/lustre/work/sweeden/rogii")
SHARED = Path(__file__).resolve().parents[1] / "traces" / "preprocessing" / "_shared"
if str(ROGII_ROOT) not in sys.path:
    sys.path.insert(0, str(ROGII_ROOT))
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

import phase_runner_core as prc  # noqa: E402
from pipeline.episodic_benchmark import EpisodicBenchmark  # noqa: E402


def test_numeric_feature_cols_extra_requires_numeric_in_test() -> None:
    train = pd.DataFrame({"MD": [1.0], "good": [2.0], "bad": [3.0], "TVT": [10.0]})
    test = pd.DataFrame({"MD": [1.0], "good": [2.0], "bad": ["x"], "TVT_input": [1.0]})
    cols = prc._numeric_feature_cols(
        train, test, id_col="id", target="TVT", extra_cols=["good", "bad"]
    )
    assert "good" in cols
    assert "bad" not in cols


def test_episodic_benchmark_write_json_includes_fold_rmses(tmp_path: Path) -> None:
    bench = EpisodicBenchmark(variant="test_variant")
    bench.oof_rmse = 0.42
    bench.oof_rmse_raw_scale = 0.42
    bench.fold_rmses = [0.5, 0.6, 0.55]
    bench.elapsed_seconds = 12.0
    out = tmp_path / "episodic_benchmark.json"
    bench.write_json(out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["fold_rmses"] == [0.5, 0.6, 0.55]
    assert payload["mean_fold_rmse"] == pytest.approx(0.55)
    assert payload["std_fold_rmse"] is not None and payload["std_fold_rmse"] > 0
