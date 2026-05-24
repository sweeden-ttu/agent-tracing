"""Unit tests for variant-specific ML pipeline modules."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROGII_ROOT = Path("/lustre/work/sweeden/rogii")
SHARED = Path(__file__).resolve().parents[1] / "traces" / "preprocessing" / "_shared"
if str(ROGII_ROOT) not in sys.path:
    sys.path.insert(0, str(ROGII_ROOT))
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from pipeline.formation_spatial import add_formation_spatial_features  # noqa: E402
from pipeline.leakage_masks import detect_ps_per_well, post_ps_mask  # noqa: E402
from pipeline.typewell_alignment import add_typewell_alignment_features, beam_search_path  # noqa: E402
from variant_hooks import load_hooks  # noqa: E402


def test_beam_search_path_returns_finite_tvt():
    gr = np.linspace(20, 80, 50)
    tw_tvt = np.linspace(0, 100, 200)
    tw_gr = np.sin(np.linspace(0, 4, 200)) * 30 + 50
    path_tvt, path_gr, cost = beam_search_path(gr, tw_tvt, tw_gr, start_tvt=10.0)
    assert len(path_tvt) == len(gr)
    assert np.all(np.isfinite(path_tvt))
    assert cost >= 0


def test_typewell_alignment_adds_features():
    df = pd.DataFrame({"GR": np.linspace(30, 70, 40), "TVT_input": np.linspace(1, 40, 40)})
    tw = pd.DataFrame({"TVT": np.linspace(0, 50, 100), "GR": np.linspace(25, 75, 100)})
    out, extra = add_typewell_alignment_features(df, tw)
    assert "gr_typewell_diff" in extra
    assert "estimated_tvt" in out.columns


def test_post_ps_mask_after_nan():
    df = pd.DataFrame({"TVT_input": [1.0, 2.0, np.nan, np.nan, 5.0]})
    mask = post_ps_mask(df)
    assert mask.tolist() == [False, False, True, True, True]


def test_detect_ps_per_well():
    df = pd.DataFrame({
        "well_id": ["a", "a", "a", "b", "b"],
        "TVT_input": [1.0, 2.0, np.nan, 4.0, np.nan],
    })
    ps = detect_ps_per_well(df)
    assert ps["a"] == 2
    assert ps["b"] == 4


def test_formation_spatial_test_without_formation_cols():
    rng = np.random.default_rng(1)
    n = 40
    tr = pd.DataFrame({
        "MD": np.linspace(100, 200, n),
        "TVD": np.linspace(90, 180, n),
        "ANCC": rng.random(n),
        "ASTNU": rng.random(n),
        "TVT_input": rng.random(n) * 10,
    })
    te = pd.DataFrame({
        "MD": np.linspace(100, 120, 10),
        "TVD": np.linspace(90, 108, 10),
        "TVT_input": rng.random(10) * 10,
    })
    tr_aug, te_aug, extra = add_formation_spatial_features(tr, te, k=3)
    assert "formation_knn_propagated" in te_aug.columns
    assert "formation_thickness_sum" in te_aug.columns


def test_formation_spatial_adds_knn_features():
    rng = np.random.default_rng(0)
    n = 60
    tr = pd.DataFrame({
        "MD": np.linspace(100, 200, n),
        "TVD": np.linspace(90, 180, n),
        "ANCC": rng.random(n),
        "TVT_input": rng.random(n) * 10,
    })
    te = tr.iloc[:10].copy()
    tr_aug, te_aug, extra = add_formation_spatial_features(tr, te, k=3)
    assert "formation_knn_propagated" in extra
    assert "formation_knn_propagated" in te_aug.columns


@pytest.mark.parametrize(
    "slug,expect",
    [
        ("typewell_gr_alignment", {"typewell_align": True}),
        ("ps_point_leakage_aware", {"eval_mask": "post_ps_only"}),
        ("robust_scale_log1p", {"numeric_scaler": "robust", "force_log1p": True}),
        ("formation_plane_spatial", {"formation_knn": True}),
    ],
)
def test_variant_hooks_registry(slug, expect):
    hooks = load_hooks(slug)
    for k, v in expect.items():
        assert getattr(hooks, k) == v


def test_typewell_hooks_augment_differs_from_baseline():
    data_dir = ROGII_ROOT / "data"
    if not data_dir.is_dir():
        pytest.skip("rogii data dir missing")
    train_candidates = [
        p for p in data_dir.glob("*train*horizontal*.csv")
        if not p.name.startswith("._")
    ]
    if not train_candidates:
        pytest.skip("no train csv in rogii data")
    train_path = train_candidates[0]
    test_candidates = [
        p for p in data_dir.glob("*test*horizontal*.csv")
        if not p.name.startswith("._")
    ]
    test_path = test_candidates[0] if test_candidates else train_path
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    baseline = load_hooks("baseline_column_transformer")
    typewell = load_hooks("typewell_gr_alignment")
    tr_b, te_b, ex_b = baseline.augment_train_test(train, test, data_dir=data_dir)
    tr_t, te_t, ex_t = typewell.augment_train_test(train, test, data_dir=data_dir)
    assert len(ex_t) > len(ex_b)
    assert "gr_typewell_diff" in tr_t.columns
