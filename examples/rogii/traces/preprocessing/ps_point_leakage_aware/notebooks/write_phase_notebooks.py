#!/usr/bin/env python3
"""Write six phase notebooks that call phase_runner with artifact handoffs."""

from __future__ import annotations

import json
from pathlib import Path

VARIANT = "ps_point_leakage_aware"
VARIANT_DIR = Path(__file__).resolve().parents[1]
NB_DIR = VARIANT_DIR / "notebooks"

PHASES = [
    (
        "01_data_analysis",
        "01 — Data analysis (schema, EDA, wells, target)",
        "run_01_data_analysis()",
        "Reads Rogii competition CSVs from ``ROGII_ROOT/data``. Writes ``artifacts/01_data_analysis/``.",
    ),
    (
        "02_statistical_framework",
        "02 — Statistical framework (experiment design, ablations)",
        "run_02_statistical_framework()",
        "Reads ``artifacts/01_data_analysis/phase_manifest.json``. Writes ``artifacts/02_statistical_framework/``.",
    ),
    (
        "03_feature_engineering",
        "03 — Feature engineering & CV (ColumnTransformer, folds)",
        "run_03_feature_engineering()",
        "Reads phase 01 artifacts. Writes ``artifacts/03_feature_engineering/`` (feature + CV config, fold indices).",
    ),
    (
        "04_model_training",
        "04 — Model training (LightGBM cross-validation)",
        "run_04_model_training(max_rows=MAX_TRAIN_ROWS)",
        "Reads phases 01 + 03. Writes ``artifacts/04_model_training/`` (transform.json, OOF, test preds).",
    ),
    (
        "05_evaluation",
        "05 — OOF evaluation & residuals",
        "run_05_evaluation()",
        "Reads phases 01 + 04. Writes ``artifacts/05_evaluation/metrics.json`` and ``residuals.csv``.",
    ),
    (
        "06_submission",
        "06 — Submission formatting & validation",
        "run_06_submission()",
        "Reads phases 01 + 04. Writes ``artifacts/06_submission/submission.csv``.",
    ),
]


def _cell(cell_type: str, source: str) -> dict:
    lines = source.rstrip("\n").split("\n")
    return {"cell_type": cell_type, "metadata": {}, "source": [ln + "\n" for ln in lines]}


def build_notebook(phase: str, title: str, run_expr: str, io_note: str) -> dict:
    md = f"""# {title}

**Variant:** `{VARIANT}`

{io_note}

Trace steps for this phase are indexed in ``../trace_row_index.csv``.

**Artifact root:** ``../artifacts/{phase}/``

Prior phase gate: ``require_prior_phase("{phase}")`` in ``phase_runner.py``.
"""
    setup = f'''import sys
from pathlib import Path

NB_DIR = Path.cwd()
if not (NB_DIR / "phase_runner.py").is_file():
    NB_DIR = Path(r"{NB_DIR}")
VARIANT_DIR = NB_DIR.parent
sys.path.insert(0, str(NB_DIR))

from phase_runner import (
    ARTIFACTS_ROOT,
    TRACE_INDEX,
    run_phase,
    run_{phase},
    require_prior_phase,
    trace_steps_for_phase,
)

PHASE = "{phase}"
print("Artifacts:", ARTIFACTS_ROOT)
print("Trace index:", TRACE_INDEX)
print("Steps in phase:", len(trace_steps_for_phase(PHASE)))
'''
    if phase == "04_model_training":
        setup += """
# Set MAX_TRAIN_ROWS = None for full train CSV (slow on login node; prefer Slurm for production).
MAX_TRAIN_ROWS = None
"""
    run = f"""prior = require_prior_phase(PHASE)
if prior:
    print("Prior phase OK:", prior["phase"], prior["completed_at"])
else:
    print("First phase — no prior artifact required")

manifest = {run_expr}
print("Phase manifest:")
for k, v in manifest.items():
    print(f"  {{k}}: {{v}}")
"""
    inspect = f"""import json
from pathlib import Path

phase_dir = ARTIFACTS_ROOT / PHASE
print("Outputs in", phase_dir)
for p in sorted(phase_dir.iterdir()):
    print(" ", p.name)
"""
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": [
            _cell("markdown", md),
            _cell("code", setup),
            _cell("code", run),
            _cell("code", inspect),
        ],
    }


def main() -> None:
    NB_DIR.mkdir(parents=True, exist_ok=True)
    for phase, title, run_expr, io_note in PHASES:
        nb = build_notebook(phase, title, run_expr, io_note)
        path = NB_DIR / f"{phase}.ipynb"
        path.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")
        print("Wrote", path)


if __name__ == "__main__":
    main()
