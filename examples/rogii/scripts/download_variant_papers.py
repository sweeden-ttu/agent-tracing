#!/usr/bin/env python3
"""Download open-access PDFs for the six Rogii trace variant base papers.

Writes to ``examples/rogii/papers/<variant>/`` and updates ``papers/manifest.json``.

Usage::

    python examples/rogii/scripts/download_variant_papers.py
    python examples/rogii/scripts/download_variant_papers.py --verify-only
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from download_layer_papers import LAYERS_ROOT, MIN_PDF_BYTES, REPO_ROOT, _fetch_urls, _valid_pdf

PAPERS_ROOT = REPO_ROOT / "papers"

# variant slug -> list of paper entries
VARIANT_PAPERS: list[dict] = [
    {
        "variant": "baseline_column_transformer",
        "paper_id": "ke2017_lightgbm",
        "title": "LightGBM: A Highly Efficient Gradient Boosting Decision Tree",
        "authors": "Ke et al.",
        "year": 2017,
        "doi": "10.5555/3294996.3295074",
        "urls": [
            "https://proceedings.neurips.cc/paper_files/paper/2017/file/6449f44a102fde848469bdd6eb6b03f7-Paper.pdf",
            "https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree.pdf",
        ],
    },
    {
        "variant": "baseline_column_transformer",
        "paper_id": "pedregosa2011_sklearn",
        "title": "Scikit-learn: Machine Learning in Python",
        "authors": "Pedregosa et al.",
        "year": 2011,
        "doi": "10.5555/1953048.2029494",
        "urls": [
            "https://jmlr.org/papers/volume12/pedregosa11a/pedregosa11a.pdf",
        ],
    },
    {
        "variant": "typewell_gr_alignment",
        "paper_id": "sakoe1978_dtw",
        "title": "Dynamic Programming Algorithm Optimization for Spoken Word Recognition",
        "authors": "Sakoe, Chiba",
        "year": 1978,
        "doi": "10.1109/TASSP.1978.1163055",
        "urls": [
            "http://jeffe.cs.illinois.edu/teaching/compgeom/refs/Sakoe-Chiba-DTW.pdf",
        ],
        "layer_copy": "01_alignment/sakoe1978_dtw.pdf",
    },
    {
        "variant": "ps_point_leakage_aware",
        "paper_id": "kaufman2012_leakage",
        "title": "Leakage in Data Mining: Formulation, Detection, and Avoidance",
        "authors": "Kaufman et al.",
        "year": 2012,
        "doi": "10.1145/2382575.2382577",
        "urls": [
            "https://arxiv.org/pdf/1208.2019.pdf",
        ],
        "layer_copy": "02_physics/kaufman2012_leakage.pdf",
    },
    {
        "variant": "robust_scale_log1p",
        "paper_id": "hampel1986_robust",
        "title": "Robust Statistics: The Approach Based on Influence Functions",
        "authors": "Hampel et al.",
        "year": 1986,
        "doi": "10.1002/9781118186435",
        "urls": [],
        "substitute_id": "pedregosa2011_sklearn_robust_substitute",
        "substitute_title": "Scikit-learn: Machine Learning in Python (RobustScaler)",
        "substitute_authors": "Pedregosa et al.",
        "substitute_year": 2011,
        "substitute_urls": [
            "https://jmlr.org/papers/volume12/pedregosa11a/pedregosa11a.pdf",
        ],
        "note": "Hampel (1986) Wiley book is paywalled; Pedregosa JMLR covers RobustScaler.",
    },
    {
        "variant": "parallel_multiwell_loader",
        "paper_id": "rocklin2015_dask",
        "title": "Dask: Parallel Computation with Blocked algorithms and Task Scheduling",
        "authors": "Rocklin",
        "year": 2015,
        "doi": "10.25080/Majora-7b98e3ed-013",
        "urls": [
            "https://conference.scipy.org/proceedings/scipy2015/pdfs/matthew_rocklin.pdf",
            "https://conference.scipy.org/proceedings/scipy2015/matthew_rocklin.pdf",
        ],
    },
    {
        "variant": "formation_plane_spatial",
        "paper_id": "cover1967_knn",
        "title": "Nearest Neighbor Pattern Classification",
        "authors": "Cover, Hart",
        "year": 1967,
        "doi": "10.1109/TIT.1967.1053964",
        "urls": [
            "https://www.cs.cmu.edu/~tom/740/reading/CoverHart.pdf",
            "https://web.stanford.edu/class/ee378/Readings/Cover-Hart-1967-NN.pdf",
        ],
        "layer_copy": "03_spatial/cover1967_knn.pdf",
    },
    {
        "variant": "formation_plane_spatial",
        "paper_id": "shepard1968_interpolation",
        "title": "A Two-dimensional Interpolation Function for Irregularly-spaced Data",
        "authors": "Shepard",
        "year": 1968,
        "doi": "10.1145/321267.321298",
        "urls": [
            "https://ptacts.uspto.gov/ptacts/public-informations/petitions/1553584/download-documents?artifactId=PCb8zqv9cWljsfwGBMGd2TTIutcZfeN77LVXOh1DcTci-5pB3fM6wxc",
        ],
        "layer_copy": "03_spatial/shepard1968_interpolation.pdf",
        "note": "Supporting reference for formation-plane interpolation.",
        "supporting": True,
    },
]


def _try_layer_copy(entry: dict, dest: Path) -> bool:
    rel = entry.get("layer_copy")
    if not rel:
        return False
    src = LAYERS_ROOT / rel
    if _valid_pdf(src):
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not _valid_pdf(dest):
            shutil.copy2(src, dest)
        return True
    return False


def _resolve(entry: dict, dry_run: bool) -> dict:
    variant_dir = PAPERS_ROOT / entry["variant"]
    primary = variant_dir / f"{entry['paper_id']}.pdf"
    rec = {
        "variant": entry["variant"],
        "paper_id": entry["paper_id"],
        "title": entry["title"],
        "authors": entry["authors"],
        "year": entry["year"],
        "doi": entry.get("doi"),
        "note": entry.get("note"),
        "supporting": entry.get("supporting", False),
        "downloaded": False,
        "repo_pdf": None,
        "source_url": None,
        "is_substitute": False,
    }

    if _valid_pdf(primary):
        rec["downloaded"] = True
        rec["repo_pdf"] = str(primary.relative_to(REPO_ROOT))
        rec["source_url"] = "(existing)"
        return rec

    if not dry_run:
        _try_layer_copy(entry, primary)

    if _valid_pdf(primary):
        rec["downloaded"] = True
        rec["repo_pdf"] = str(primary.relative_to(REPO_ROOT))
        rec["source_url"] = "(layer copy)"
        return rec

    ok, src = _fetch_urls(entry.get("urls", []), primary, entry["paper_id"], dry_run)
    if ok:
        rec["downloaded"] = True
        rec["repo_pdf"] = str(primary.relative_to(REPO_ROOT))
        rec["source_url"] = src
        return rec

    sub_id = entry.get("substitute_id")
    if sub_id:
        sub_path = variant_dir / f"{sub_id}.pdf"
        sub_ok, sub_src = _fetch_urls(entry.get("substitute_urls", []), sub_path, sub_id, dry_run)
        if sub_ok:
            rec["downloaded"] = True
            rec["repo_pdf"] = str(sub_path.relative_to(REPO_ROOT))
            rec["source_url"] = sub_src
            rec["is_substitute"] = True
            rec["substitute_for"] = entry["paper_id"]
            rec["substitute_title"] = entry.get("substitute_title")
            return rec

    return rec


def _primary_satisfied(entry: dict) -> bool:
    variant_dir = PAPERS_ROOT / entry["variant"]
    primary = variant_dir / f"{entry['paper_id']}.pdf"
    if _valid_pdf(primary):
        return True
    sub_id = entry.get("substitute_id")
    if sub_id and _valid_pdf(variant_dir / f"{sub_id}.pdf"):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    primaries = [e for e in VARIANT_PAPERS if not e.get("supporting")]
    if args.verify_only:
        missing = [e["paper_id"] for e in primaries if not _primary_satisfied(e)]
        if missing:
            print("MISSING:", ", ".join(missing))
            return 1
        print(f"OK all {len(primaries)} variant primaries satisfied")
        return 0

    results = [_resolve(e, args.dry_run) for e in VARIANT_PAPERS]
    missing = [r["paper_id"] for r in results if not r.get("supporting") and not r["downloaded"]]

    if not args.dry_run:
        manifest = {
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "papers": results,
        }
        PAPERS_ROOT.mkdir(parents=True, exist_ok=True)
        (PAPERS_ROOT / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    if missing:
        print("MISSING:", ", ".join(missing))
        return 1
    print(f"OK {sum(1 for r in results if r['downloaded'])}/{len(results)} variant papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
