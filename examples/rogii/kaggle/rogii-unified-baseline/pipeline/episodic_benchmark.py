"""Episodic TCN benchmark: track best checkpoint per fold and cross-episode performance."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class EpisodeRecord:
    fold: int
    episode: int
    seed: int
    val_rmse: float
    best_window_rmse: float
    checkpoint: str
    n_epochs: int
    is_best_fold: bool = False


@dataclass
class EpisodicBenchmark:
    """Accumulates episodic training outcomes for benchmark reporting."""

    variant: str
    approach: str = ""
    paper_id: str = ""
    eval_mask: str = "full_well"
    use_log1p: bool = False
    feature_cols: list[str] = field(default_factory=list)
    cv_scheme: str = ""
    episodes_per_fold: int = 3
    max_epochs: int = 60
    patience: int = 8
    episodes: list[EpisodeRecord] = field(default_factory=list)
    fold_best: list[dict[str, Any]] = field(default_factory=list)
    oof_rmse: float | None = None
    oof_rmse_raw_scale: float | None = None
    fold_rmses: list[float] = field(default_factory=list)
    elapsed_seconds: float | None = None

    def record_episode(
        self,
        *,
        fold: int,
        episode: int,
        seed: int,
        val_rmse: float,
        best_window_rmse: float,
        checkpoint: str,
        n_epochs: int,
    ) -> None:
        self.episodes.append(
            EpisodeRecord(
                fold=fold,
                episode=episode,
                seed=seed,
                val_rmse=val_rmse,
                best_window_rmse=best_window_rmse,
                checkpoint=checkpoint,
                n_epochs=n_epochs,
            )
        )

    def set_fold_best(self, fold: int, checkpoint: str, val_rmse: float) -> None:
        self.fold_best.append({"fold": fold, "checkpoint": checkpoint, "val_rmse": val_rmse})
        for ep in self.episodes:
            if ep.fold == fold:
                ep.is_best_fold = ep.checkpoint == checkpoint

    def finalize(
        self,
        *,
        oof_rmse: float,
        fold_rmses: list[float],
        elapsed_seconds: float,
        oof_rmse_raw_scale: float | None = None,
    ) -> dict[str, Any]:
        self.oof_rmse = oof_rmse
        self.oof_rmse_raw_scale = oof_rmse_raw_scale
        self.fold_rmses = fold_rmses
        self.elapsed_seconds = elapsed_seconds
        best_ep = min(self.episodes, key=lambda e: e.val_rmse) if self.episodes else None
        return {
            "variant": self.variant,
            "approach": self.approach,
            "paper_id": self.paper_id,
            "eval_mask": self.eval_mask,
            "use_log1p": self.use_log1p,
            "n_features": len(self.feature_cols),
            "feature_cols": self.feature_cols,
            "cv_scheme": self.cv_scheme,
            "episodes_per_fold": self.episodes_per_fold,
            "max_epochs": self.max_epochs,
            "patience": self.patience,
            "oof_rmse": self.oof_rmse,
            "oof_rmse_raw_scale": self.oof_rmse_raw_scale,
            "mean_fold_rmse": float(sum(fold_rmses) / len(fold_rmses)) if fold_rmses else None,
            "std_fold_rmse": float(
                (sum((x - sum(fold_rmses) / len(fold_rmses)) ** 2 for x in fold_rmses) / len(fold_rmses)) ** 0.5
            )
            if len(fold_rmses) > 1
            else 0.0,
            "fold_rmses": fold_rmses,
            "fold_best": self.fold_best,
            "best_episode_overall": asdict(best_ep) if best_ep else None,
            "episodes": [asdict(e) for e in self.episodes],
            "elapsed_seconds": elapsed_seconds,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    def write_json(self, path: Path) -> Path:
        payload = self.finalize(
            oof_rmse=self.oof_rmse or float("nan"),
            fold_rmses=self.fold_rmses,
            elapsed_seconds=self.elapsed_seconds or 0.0,
            oof_rmse_raw_scale=self.oof_rmse_raw_scale,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path


def load_benchmark(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_variants(benchmark_paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in sorted(benchmark_paths):
        if not p.is_file():
            continue
        b = load_benchmark(p)
        rows.append(
            {
                "variant": b.get("variant"),
                "oof_rmse": b.get("oof_rmse"),
                "oof_rmse_raw_scale": b.get("oof_rmse_raw_scale"),
                "mean_fold_rmse": b.get("mean_fold_rmse"),
                "n_features": b.get("n_features"),
                "eval_mask": b.get("eval_mask"),
                "best_episode_val_rmse": (b.get("best_episode_overall") or {}).get("val_rmse"),
                "path": str(p),
            }
        )
    return rows
