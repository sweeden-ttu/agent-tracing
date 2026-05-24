"""Tests for synthetic ROGII competition data generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROGII_ROOT = Path("/lustre/work/sweeden/rogii")
if str(ROGII_ROOT) not in sys.path:
    sys.path.insert(0, str(ROGII_ROOT))

from pipeline.agents import SubmissionEnvelopeValidator  # noqa: E402
from pipeline.competition_data import load_competition_frames  # noqa: E402
from pipeline.synthetic_competition_data import (  # noqa: E402
    build_sample_submission_from_tests,
    generate_synthetic_bundle,
    parse_submission_specs,
    prediction_zone_info,
    write_submission_samples,
)


DATA_DIR = ROGII_ROOT / "data"


@pytest.fixture(scope="module")
def sample_submission() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sample_submission.csv")


def test_write_submission_samples_all_nan_tvt_input(tmp_path: Path) -> None:
    """Rows with NaN TVT_input must not call iloc[-1] on an empty Series."""
    train_frames = {
        "well0": pd.DataFrame({"TVT_input": [float("nan"), float("nan")]}),
    }
    sample_sub = pd.DataFrame({"id": ["well0_0", "well0_1"]})
    out = write_submission_samples(
        tmp_path, sample_sub, train_frames, id_col="id", target_col="tvt"
    )
    sub = pd.read_csv(out)
    assert list(sub["tvt"]) == [0.0, 0.0]


def test_parse_submission_specs_three_wells(sample_submission: pd.DataFrame) -> None:
    specs = parse_submission_specs(sample_submission)
    assert len(specs) == 3
    wells = {s.well_id for s in specs}
    assert wells == {"000d7d20", "00bbac68", "00e12e8b"}


def test_generate_synthetic_bundle_tmp(tmp_path: Path, sample_submission: pd.DataFrame) -> None:
    out = tmp_path / "synthetic"
    result = generate_synthetic_bundle(
        DATA_DIR,
        out,
        wells=["00bbac68"],
        write_submission_sample=True,
    )
    assert (out / "_train_00bbac68_horizontal_well.csv").is_file()
    assert (out / "_test_00bbac68_horizontal_well.csv").is_file()
    assert (out / "00bbac68__typewell.csv").is_file()
    assert (out / "submission_samples" / "submission.csv").is_file()

    test_df = pd.read_csv(out / "_test_00bbac68_horizontal_well.csv")
    zone = prediction_zone_info(test_df)
    assert zone["prediction_rows"] == 6014
    assert zone["first_prediction_index"] == 1545

    manifest = json.loads((out / "synthetic_manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_wells"] == 1
    assert manifest["wells"]["00bbac68"]["prediction_zone"]["prediction_rows"] == 6014


def test_submission_sample_passes_envelope_validator(tmp_path: Path) -> None:
    out = tmp_path / "bundle"
    generate_synthetic_bundle(DATA_DIR, out, write_submission_sample=True)
    sub_sample = pd.read_csv(out / "submission_samples" / "submission.csv")
    validator = SubmissionEnvelopeValidator(DATA_DIR / "sample_submission.csv")
    report = validator.validate(sub_sample)
    assert report["ok"] is True


def test_load_competition_frames_after_synthetic_fill(tmp_path: Path) -> None:
    out = tmp_path / "full"
    generate_synthetic_bundle(DATA_DIR, out, layout="flat")
    train_df, test_df, sample_sub, id_col, target_col = load_competition_frames(out)
    assert len(sample_sub) == 14151
    assert id_col == "id"
    assert target_col == "tvt"
    assert train_df["well_id"].nunique() == 3
    assert test_df["well_id"].nunique() == 3

    rebuilt = build_sample_submission_from_tests(
        {wid: test_df[test_df["well_id"] == wid].drop(columns=["well_id", "is_train"])
         for wid in test_df["well_id"].unique()}
    )
    assert set(rebuilt["id"]) == set(sample_sub["id"])
