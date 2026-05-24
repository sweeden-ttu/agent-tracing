"""ROGII competition ML pipeline building blocks (download → EDA → train → submit).

Each submodule exposes the functions named in the design grid (see submodule docstrings).
Run from the competition directory with ``PYTHONPATH`` including the repo root if you
use ``data_analyst`` / ``trace_language`` imports.
"""

from __future__ import annotations

__all__ = [
    "data_downloader",
    "eda_profiler",
    "well_group_detector",
    "target_diagnostician",
    "feature_engineer",
    "preprocessor",
    "cv_orchestrator",
    "model_trainer",
    "model_ensembler",
    "predictor",
    "oof_evaluator",
    "error_analyzer",
    "submission_formatter",
    "submission_validator",
    "kaggle_submitter",
]
