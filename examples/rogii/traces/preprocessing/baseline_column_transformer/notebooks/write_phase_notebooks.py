#!/usr/bin/env python3
"""Write six competition-depth phase notebooks with artifact handoffs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TRACES_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VARIANT = "baseline_column_transformer"

ALL_VARIANTS = [
    "baseline_column_transformer",
    "typewell_gr_alignment",
    "ps_point_leakage_aware",
    "robust_scale_log1p",
    "parallel_multiwell_loader",
    "formation_plane_spatial",
]


def _cell(cell_type: str, source: str) -> dict:
    lines = source.rstrip("\n").split("\n")
    return {"cell_type": cell_type, "metadata": {}, "source": [ln + "\n" for ln in lines]}


def build_notebook(phase: str, builders: dict) -> dict:
    builder = builders[phase]
    cells = [_cell(t, src) for t, src in builder()]
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": cells,
    }


def configure_variant(variant: str) -> tuple[Path, object]:
    variant_dir = TRACES_ROOT / variant
    nb_dir = variant_dir / "notebooks"
    if not nb_dir.is_dir():
        raise FileNotFoundError(f"Missing notebooks dir: {nb_dir}")

    baseline_nb = TRACES_ROOT / DEFAULT_VARIANT / "notebooks"
    if str(baseline_nb) not in sys.path:
        sys.path.insert(0, str(baseline_nb))

    import phase_notebook_cells as pnc  # noqa: WPS433

    pnc.VARIANT = variant
    pnc.VARIANT_DIR = variant_dir
    pnc.NB_DIR = nb_dir
    return nb_dir, pnc


def write_variant(variant: str) -> None:
    nb_dir, pnc = configure_variant(variant)
    nb_dir.mkdir(parents=True, exist_ok=True)
    for phase in pnc.PHASE_CELL_BUILDERS:
        nb = build_notebook(phase, pnc.PHASE_CELL_BUILDERS)
        path = nb_dir / f"{phase}.ipynb"
        path.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")
        n_cells = len(nb["cells"])
        n_md = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
        print(f"[{variant}] Wrote {path.name}: {n_cells} cells ({n_md} markdown)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default=DEFAULT_VARIANT, help="Trace variant folder name")
    parser.add_argument(
        "--all-variants",
        action="store_true",
        help="Regenerate notebooks for all six preprocessing trace variants",
    )
    args = parser.parse_args()

    variants = ALL_VARIANTS if args.all_variants else [args.variant]
    for variant in variants:
        write_variant(variant)


if __name__ == "__main__":
    main()
