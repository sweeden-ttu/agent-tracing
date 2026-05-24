"""Per-variant hooks for the shared phase runner (six trace branches)."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

ROGII_ROOT = Path("/lustre/work/sweeden/rogii")


def _ensure_rogii_path() -> None:
    if str(ROGII_ROOT) not in sys.path:
        sys.path.insert(0, str(ROGII_ROOT))


@dataclass
class VariantHooks:
    slug: str
    approach: str
    phase02_rationale: str
    force_log1p: bool | None = None
    numeric_scaler: str = "median"  # median | robust
    eval_mask: str = "full_well"  # full_well | post_ps_only
    typewell_align: bool = False
    typewell_interpolator: Literal["linear", "pchip"] = "linear"
    parallel_workers: int = 4
    formation_knn: bool = False
    formation_knn_k: int = 5
    extra_feature_cols: list[str] = field(default_factory=list)
    loader_meta: dict[str, Any] = field(default_factory=dict)

    def phase01_extra(self, train_df: pd.DataFrame, target: str) -> dict[str, Any]:
        out: dict[str, Any] = {"variant_slug": self.slug, "approach": self.approach}
        if self.eval_mask == "post_ps_only" and "TVT_input" in train_df.columns:
            _ensure_rogii_path()
            from pipeline.leakage_masks import detect_ps_per_well

            out["ps_per_well"] = detect_ps_per_well(train_df)
            out["leakage_audit"] = "strict"
        if self.typewell_align:
            out["typewell_align"] = "on"
            out["interpolator"] = self.typewell_interpolator
        if self.formation_knn:
            out["formation_knn"] = "on"
            out["formation_knn_k"] = self.formation_knn_k
        if self.numeric_scaler == "robust":
            out["feature_scaler"] = "robust"
        if self.slug == "parallel_multiwell_loader" and self.loader_meta:
            out["parallel_loader"] = self.loader_meta
        return out

    def resolve_log1p(self, log_rec: dict) -> bool:
        if self.force_log1p is True:
            return True
        if self.force_log1p is False:
            return False
        return bool(log_rec.get("use_log1p", False))

    def augment_train_test(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        *,
        data_dir: Path,
    ) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
        """Return augmented frames and extra numeric column names."""
        _ensure_rogii_path()
        extra_cols: list[str] = []
        tr, te = train_df.copy(), test_df.copy()

        if self.typewell_align:
            from pipeline.typewell_alignment import add_typewell_alignment_features, find_typewell_path

            tw_path = find_typewell_path(data_dir, tr)
            if tw_path and tw_path.is_file():
                tw = pd.read_csv(tw_path)
                tr, tw_extra = add_typewell_alignment_features(
                    tr, tw, interpolator=self.typewell_interpolator
                )
                te, te_extra = add_typewell_alignment_features(
                    te, tw, interpolator=self.typewell_interpolator
                )
                extra_cols.extend(list(dict.fromkeys(tw_extra + te_extra)))

        if self.formation_knn:
            from pipeline.formation_spatial import add_formation_spatial_features

            tr, te, form_extra = add_formation_spatial_features(tr, te, k=self.formation_knn_k)
            extra_cols.extend(form_extra)

        if self.slug == "parallel_multiwell_loader":
            from pipeline.parallel_loader import attach_geology_surface_features

            tr, surf_extra = attach_geology_surface_features(tr, data_dir)
            te, surf_extra_te = attach_geology_surface_features(te, data_dir)
            extra_cols.extend(list(dict.fromkeys(surf_extra + surf_extra_te)))

        return tr, te, list(dict.fromkeys(extra_cols))

    def eval_mask_indices(self, train_df: pd.DataFrame) -> np.ndarray | None:
        if self.eval_mask != "post_ps_only" or "TVT_input" not in train_df.columns:
            return None
        _ensure_rogii_path()
        from pipeline.leakage_masks import post_ps_mask

        return post_ps_mask(train_df)

    def build_numeric_transformer(self):
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline

        if self.numeric_scaler == "robust":
            from sklearn.preprocessing import RobustScaler

            return Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", RobustScaler()),
            ])
        return Pipeline([("imputer", SimpleImputer(strategy="median"))])


_REGISTRY: dict[str, VariantHooks] = {
    "baseline_column_transformer": VariantHooks(
        slug="baseline_column_transformer",
        approach="ColumnTransformer + LightGBM baseline",
        phase02_rationale="baseline ColumnTransformer + LightGBM; Pedregosa/Ke path",
    ),
    "typewell_gr_alignment": VariantHooks(
        slug="typewell_gr_alignment",
        approach="GR/typewell alignment features",
        phase02_rationale="typewell GR alignment (Sakoe–Chiba DTW proxy features)",
        typewell_align=True,
        typewell_interpolator="pchip",
    ),
    "ps_point_leakage_aware": VariantHooks(
        slug="ps_point_leakage_aware",
        approach="PS-point detection + post-PS RMSE mask",
        phase02_rationale="leakage-aware eval; post-PS RMSE mask (Kaufman et al.)",
        eval_mask="post_ps_only",
    ),
    "robust_scale_log1p": VariantHooks(
        slug="robust_scale_log1p",
        approach="RobustScaler + log1p target",
        phase02_rationale="RobustScaler numeric block + log1p target (Hampel et al.)",
        force_log1p=True,
        numeric_scaler="robust",
    ),
    "parallel_multiwell_loader": VariantHooks(
        slug="parallel_multiwell_loader",
        approach="Parallel IO + geology surfaces",
        phase02_rationale="parallel multiwell loader metadata (Rocklin/Dask pattern)",
        parallel_workers=8,
    ),
    "formation_plane_spatial": VariantHooks(
        slug="formation_plane_spatial",
        approach="Drilling geometry + formation KNN",
        phase02_rationale="formation thickness + plane KNN features (Cover & Hart)",
        formation_knn=True,
        formation_knn_k=5,
    ),
}


def load_hooks(variant_slug: str) -> VariantHooks:
    if variant_slug not in _REGISTRY:
        raise KeyError(f"Unknown variant {variant_slug!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[variant_slug]
