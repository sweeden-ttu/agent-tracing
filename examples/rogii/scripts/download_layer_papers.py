#!/usr/bin/env python3
"""Download open-access PDFs for Rogii leaderboard ensemble layers.

Writes to ``examples/rogii/papers/layers/<layer_id>/`` and updates
``papers/layers/manifest.json``.

Primary papers are fetched when an open PDF mirror exists. Paywalled
primaries use ``substitute_id`` entries (also open access) and are recorded
in the manifest with ``is_substitute: true``.

Usage::

    python examples/rogii/scripts/download_layer_papers.py
    python examples/rogii/scripts/download_layer_papers.py --dry-run
    python examples/rogii/scripts/download_layer_papers.py --verify-only
"""

from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYERS_ROOT = REPO_ROOT / "papers" / "layers"

# Verified open-access mirrors (May 2026). Order matters — first success wins.
LAYER_PAPERS: list[dict] = [
    {
        "layer_id": "01_alignment",
        "paper_id": "sakoe1978_dtw",
        "title": "Dynamic Programming Algorithm Optimization for Spoken Word Recognition",
        "authors": "Sakoe, Chiba",
        "year": 1978,
        "doi": "10.1109/TASSP.1978.1163055",
        "urls": [
            "http://jeffe.cs.illinois.edu/teaching/compgeom/refs/Sakoe-Chiba-DTW.pdf",
        ],
        "note": "DTW alignment basis for GR–typewell tie points.",
    },
    {
        "layer_id": "01_alignment",
        "paper_id": "lowerre1976_harpy_beam",
        "title": "The HARPY Speech Recognition System (beam search)",
        "authors": "Lowerre",
        "year": 1976,
        "doi": None,
        "urls": [
            "https://publications.ri.cmu.edu/storage/publications/pub_files/1976/1/Lowerre_1976_1_The_HARPY_Speech_Recognition_System.pdf",
            "https://apps.dtic.mil/sti/pdfs/ADA035146.pdf",
        ],
        "substitute_id": "lowerre1976_harpy_beam_substitute",
        "substitute_title": "Sequence-to-Sequence Learning as Beam-Search Optimization",
        "substitute_authors": "Wiseman, Rush",
        "substitute_year": 2016,
        "substitute_urls": [
            "https://arxiv.org/pdf/1606.02960.pdf",
        ],
        "note": "Classic HARPY beam-search decoder; open substitute covers beam-search optimization theory.",
    },
    {
        "layer_id": "02_physics",
        "paper_id": "gordon1993_particle_filter",
        "title": "Novel approach to nonlinear and non-Gaussian Bayesian state estimation (particle filter)",
        "authors": "Gordon, Salmond, Smith",
        "year": 1993,
        "doi": "10.1049/ip-f-2.1993.0015",
        "urls": [],
        "substitute_id": "doucet2011_tutorial_smc",
        "substitute_title": "A Tutorial on Particle Filtering and Smoothing: Fifteen Years Later",
        "substitute_authors": "Doucet, Johansen",
        "substitute_year": 2011,
        "substitute_urls": [
            "https://arxiv.org/pdf/1301.0056.pdf",
        ],
        "note": "Gordon (1993) is paywalled; Doucet tutorial is the canonical open SMC reference.",
    },
    {
        "layer_id": "02_physics",
        "paper_id": "kaufman2012_leakage",
        "title": "Leakage in Data Mining: Formulation, Detection, and Avoidance",
        "authors": "Kaufman et al.",
        "year": 2012,
        "doi": "10.1145/2382575.2382577",
        "urls": [
            "https://arxiv.org/pdf/1208.2019.pdf",
        ],
        "note": "Point-wise leakage guard for physics / CV splits (also under ps_point_leakage_aware variant).",
    },
    {
        "layer_id": "03_spatial",
        "paper_id": "cover1967_knn",
        "title": "Nearest Neighbor Pattern Classification",
        "authors": "Cover, Hart",
        "year": 1967,
        "doi": "10.1109/TIT.1967.1053964",
        "urls": [
            "https://www.cs.cmu.edu/~tom/740/reading/CoverHart.pdf",
            "https://web.stanford.edu/class/ee378/Readings/Cover-Hart-1967-NN.pdf",
        ],
    },
    {
        "layer_id": "03_spatial",
        "paper_id": "shepard1968_interpolation",
        "title": "A Two-dimensional Interpolation Function for Irregularly-spaced Data",
        "authors": "Shepard",
        "year": 1968,
        "doi": "10.1145/321267.321298",
        "urls": [
            "https://ptacts.uspto.gov/ptacts/public-informations/petitions/1553584/download-documents?artifactId=PCb8zqv9cWljsfwGBMGd2TTIutcZfeN77LVXOh1DcTci-5pB3fM6wxc",
            "https://www.cs.cmu.edu/~quake-papers/shepard-1968.pdf",
        ],
        "note": "Inverse-distance spatial interpolation for formation-plane propagation.",
    },
    {
        "layer_id": "04_features",
        "paper_id": "lewis1995_fast_ncc",
        "title": "Fast Normalized Cross-Correlation",
        "authors": "Lewis",
        "year": 1995,
        "doi": None,
        "urls": [
            "https://scribblethink.org/Work/nvisionInterface/nip.pdf",
            "http://www.cs.cmu.edu/~dst/COWI/Papers/lewis95.pdf",
        ],
        "substitute_id": "briechle2001_fast_ncc_substitute",
        "substitute_title": "Template Matching using Fast Normalized Cross Correlation",
        "substitute_authors": "Briechle, Hanebeck",
        "substitute_year": 2001,
        "substitute_urls": [
            "https://isas.iar.kit.edu/pdf/SPIE01_BriechleHanebeck_CrossCorr.pdf",
        ],
        "note": "Lewis (1995) CMU mirror is often offline; Briechle (2001) extends Lewis sum-table NCC.",
    },
    {
        "layer_id": "04_features",
        "paper_id": "wolpert1992_stacked_generalization",
        "title": "Stacked Generalization",
        "authors": "Wolpert",
        "year": 1992,
        "doi": None,
        "urls": [
            "http://www.mlresearch.org/reproducing-model-ensembles/wolpert92.pdf",
            "https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=10.1.1.133.4560",
        ],
        "note": "Theoretical basis for learned convex blends / reference stacking.",
    },
    {
        "layer_id": "05_models",
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
        "layer_id": "05_models",
        "paper_id": "prokhorenkova2018_catboost",
        "title": "CatBoost: unbiased boosting with categorical features",
        "authors": "Prokhorenkova et al.",
        "year": 2018,
        "doi": "10.48550/arXiv.1706.09516",
        "urls": ["https://arxiv.org/pdf/1706.09516.pdf"],
    },
    {
        "layer_id": "05_models",
        "paper_id": "chen2016_xgboost",
        "title": "XGBoost: A Scalable Tree Boosting System",
        "authors": "Chen, Guestrin",
        "year": 2016,
        "doi": "10.1145/2939672.2939785",
        "urls": [
            "https://arxiv.org/pdf/1603.02754.pdf",
            "https://homes.cs.washington.edu/~tqchen/data/papers/xgboost-kdd.pdf",
        ],
    },
    {
        "layer_id": "06_sequence",
        "paper_id": "bai2018_tcn",
        "title": "An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling",
        "authors": "Bai, Kolter, Koltun",
        "year": 2018,
        "doi": "10.48550/arXiv.1803.01271",
        "urls": ["https://arxiv.org/pdf/1803.01271.pdf"],
    },
    {
        "layer_id": "06_sequence",
        "paper_id": "qu2025_tabicl",
        "title": "TabICL: A Tabular Foundation Model for In-Context Learning on Large Data",
        "authors": "Qu et al.",
        "year": 2025,
        "doi": "10.48550/arXiv.2502.05564",
        "urls": [
            "https://arxiv.org/pdf/2502.05564.pdf",
            "https://raw.githubusercontent.com/mlresearch/v267/main/assets/qu25d/qu25d.pdf",
        ],
    },
    {
        "layer_id": "07_blend",
        "paper_id": "hoerl1970_ridge",
        "title": "Ridge Regression: Biased Estimation for Nonorthogonal Problems",
        "authors": "Hoerl, Kennard",
        "year": 1970,
        "doi": "10.2307/1267351",
        "urls": [
            "https://www.stat.berkeley.edu/~ryantibs/papers/Ridge.pdf",
        ],
        "substitute_id": "tibshirani2016_ridge_lecture_notes",
        "substitute_title": "Lecture notes on ridge regression",
        "substitute_authors": "Tibshirani",
        "substitute_year": 2015,
        "substitute_urls": [
            "https://arxiv.org/pdf/1509.09169.pdf",
        ],
        "note": "Technometrics (1970) is paywalled; Tibshirani ridge lecture notes are the open L2 meta-learner reference.",
    },
    {
        "layer_id": "07_blend",
        "paper_id": "breiman1996_stacking",
        "title": "Stacked Regressions",
        "authors": "Breiman",
        "year": 1996,
        "doi": "10.1007/BF00117832",
        "urls": [
            "https://www.stat.berkeley.edu/~breiman/stacked.pdf",
            "https://link.springer.com/content/pdf/10.1007/BF00117832.pdf",
        ],
    },
    {
        "layer_id": "07_blend",
        "paper_id": "tibshirani1996_ridge_lasso_survey",
        "title": "Statistical Learning with Sparsity: The Lasso and Generalizations",
        "authors": "Hastie, Tibshirani, Wainwright",
        "year": 2016,
        "doi": "10.48550/arXiv.1606.02147",
        "urls": [
            "https://arxiv.org/pdf/1606.02147.pdf",
        ],
        "note": "Open L1/L2 regularization context for ridge stacks and hill-climbing blend search.",
    },
    {
        "layer_id": "08_post",
        "paper_id": "savitzky1964_smoothing",
        "title": "Smoothing and Differentiation of Data by Simplified Least Squares Procedures",
        "authors": "Savitzky, Golay",
        "year": 1964,
        "doi": "10.1021/ac60214a047",
        "urls": [
            "https://www.cs.tut.fi/~sjg/nyrk/papers/Savitzky-Golay.pdf",
            "https://constans.pbworks.com/f/Savitzky-Golay%20Filter.pdf",
        ],
    },
]

MIN_PDF_BYTES = 5000


def _download(url: str, dest: Path, timeout: int = 120) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Rogii-paper-fetch/1.0; research)"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    if len(data) < MIN_PDF_BYTES or not data[:5].startswith(b"%PDF"):
        return False
    dest.write_bytes(data)
    return True


def _valid_pdf(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= MIN_PDF_BYTES and path.read_bytes()[:5].startswith(b"%PDF")


def _fetch_urls(urls: list[str], dest: Path, label: str, dry_run: bool) -> tuple[bool, str | None]:
    if _valid_pdf(dest):
        return True, "(existing)"
    if dry_run:
        return False, urls[0] if urls else None
    for url in urls:
        print(f"TRY {label} <- {url}")
        if _download(url, dest):
            print(f"OK {dest}")
            return True, url
    return False, None


def _resolve_entry(entry: dict, dry_run: bool) -> list[dict]:
    """Return one or two manifest records (primary + optional substitute file)."""
    layer_dir = LAYERS_ROOT / entry["layer_id"]
    primary_path = layer_dir / f"{entry['paper_id']}.pdf"
    records: list[dict] = []

    primary_ok, primary_src = _fetch_urls(entry.get("urls", []), primary_path, entry["paper_id"], dry_run)

    primary_rec = {
        "layer_id": entry["layer_id"],
        "paper_id": entry["paper_id"],
        "title": entry["title"],
        "authors": entry["authors"],
        "year": entry["year"],
        "doi": entry.get("doi"),
        "note": entry.get("note"),
        "repo_pdf": str(primary_path.relative_to(REPO_ROOT)) if primary_ok else None,
        "downloaded": primary_ok,
        "source_url": primary_src,
        "is_substitute": False,
    }
    records.append(primary_rec)

    sub_id = entry.get("substitute_id")
    if not sub_id:
        return records

    sub_path = layer_dir / f"{sub_id}.pdf"
    sub_ok, sub_src = _fetch_urls(entry.get("substitute_urls", []), sub_path, sub_id, dry_run)

    if not primary_ok and sub_ok:
        primary_rec["downloaded"] = True
        primary_rec["repo_pdf"] = str(sub_path.relative_to(REPO_ROOT))
        primary_rec["source_url"] = sub_src
        primary_rec["is_substitute"] = True
        primary_rec["substitute_for"] = entry["paper_id"]
        primary_rec["substitute_title"] = entry.get("substitute_title")
        primary_rec["substitute_authors"] = entry.get("substitute_authors")
        primary_rec["substitute_year"] = entry.get("substitute_year")

    if sub_ok and sub_id != entry["paper_id"]:
        records.append(
            {
                "layer_id": entry["layer_id"],
                "paper_id": sub_id,
                "title": entry.get("substitute_title"),
                "authors": entry.get("substitute_authors"),
                "year": entry.get("substitute_year"),
                "doi": None,
                "note": f"Open-access substitute file for {entry['paper_id']}.",
                "repo_pdf": str(sub_path.relative_to(REPO_ROOT)),
                "downloaded": True,
                "source_url": sub_src,
                "is_substitute": True,
                "substitute_for": entry["paper_id"],
            }
        )
    elif not sub_ok and entry.get("substitute_urls") and not dry_run:
        print(f"FAIL substitute {sub_id} for {entry['paper_id']}")

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Check manifest expectations without downloading.",
    )
    args = parser.parse_args()

    results: list[dict] = []
    missing: list[str] = []

    for entry in LAYER_PAPERS:
        if args.verify_only:
            layer_dir = LAYERS_ROOT / entry["layer_id"]
            primary = layer_dir / f"{entry['paper_id']}.pdf"
            sub_id = entry.get("substitute_id")
            sub = layer_dir / f"{sub_id}.pdf" if sub_id else None
            ok = _valid_pdf(primary) or (sub is not None and _valid_pdf(sub))
            if not ok:
                missing.append(entry["paper_id"])
            continue

        for rec in _resolve_entry(entry, args.dry_run):
            results.append(rec)
            if not rec.get("downloaded"):
                missing.append(rec["paper_id"])

    if args.verify_only:
        if missing:
            print("MISSING:", ", ".join(missing))
            return 1
        print(f"OK all {len(LAYER_PAPERS)} README layer primaries satisfied")
        return 0

    manifest = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "layers": [
            "01_alignment",
            "02_physics",
            "03_spatial",
            "04_features",
            "05_models",
            "06_sequence",
            "07_blend",
            "08_post",
        ],
        "papers": results,
    }
    if not args.dry_run:
        LAYERS_ROOT.mkdir(parents=True, exist_ok=True)
        (LAYERS_ROOT / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    if missing and not args.dry_run:
        print("MISSING:", ", ".join(sorted(set(missing))))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
