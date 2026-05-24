#!/usr/bin/env python3
"""Verify trace phase artifact handoffs (preboot before Slurm phase jobs).

Checks that each phase's required *inputs* exist on disk and match the prior
phase manifest ``outputs`` map. Exits non-zero on misalignment so chain jobs fail fast.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PHASE_ORDER = [
    "01_data_analysis",
    "02_statistical_framework",
    "03_feature_engineering",
    "04_model_training",
    "05_evaluation",
    "06_submission",
]

# Explicit consumer reads from phase_runner.py (paths relative to variant dir).
PHASE_INPUTS: dict[str, list[tuple[str, str, str]]] = {
    # (source_phase, manifest_output_key, description)
    "02_statistical_framework": [
        ("01_data_analysis", "well_groups", "phase 02 reads p01 well_groups"),
        ("01_data_analysis", "target_diagnosis", "phase 02 reads p01 target_diagnosis"),
        ("01_data_analysis", "eda_summary", "phase 02 reads p01 eda_summary"),
    ],
    "03_feature_engineering": [
        ("01_data_analysis", "data_paths", "phase 03 reads p01 data_paths"),
        ("01_data_analysis", "schema", "phase 03 reads p01 schema"),
    ],
    "04_model_training": [
        ("01_data_analysis", "data_paths", "phase 04 reads p01 data_paths"),
        ("01_data_analysis", "target_diagnosis", "phase 04 reads p01 target_diagnosis"),
        ("03_feature_engineering", "cv_config", "phase 04 reads p03 cv_config"),
        ("03_feature_engineering", "feature_config", "phase 04 reads p03 feature_config"),
    ],
    "05_evaluation": [
        ("01_data_analysis", "data_paths", "phase 05 reads p01 data_paths"),
        ("04_model_training", "transform", "phase 05 reads p04 transform"),
        ("04_model_training", "training_metrics", "phase 05 reads p04 training_metrics"),
        ("04_model_training", "oof_predictions", "phase 05 reads p04 oof_predictions"),
    ],
    "06_submission": [
        ("01_data_analysis", "data_paths", "phase 06 reads p01 data_paths"),
        ("01_data_analysis", "schema", "phase 06 reads p01 schema"),
        ("04_model_training", "transform", "phase 06 reads p04 transform"),
        ("04_model_training", "test_preds_per_fold", "phase 06 reads p04 test_preds_per_fold"),
    ],
}

PHASE_VARIANT_FILES: dict[str, list[str]] = {
    "02_statistical_framework": [
        "experiment_descriptor.json",
        "ablation_plan.json",
        "mle_plan.json",
    ],
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(variant_dir: Path, rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (variant_dir / p)


def _phase_index(phase: str) -> int:
    try:
        return PHASE_ORDER.index(phase)
    except ValueError as exc:
        raise SystemExit(f"Unknown phase: {phase}") from exc


def _load_contract(variant_dir: Path, phase: str) -> dict | None:
    path = variant_dir / "artifacts" / phase / "PHASE_CONTRACT.json"
    if not path.is_file():
        return None
    return _load_json(path)


def _expected_outputs(contract: dict) -> dict[str, str]:
    out = dict(contract.get("outputs") or {})
    out.update(contract.get("optional_outputs") or {})
    return out


def verify_preboot(variant_dir: Path, phase: str) -> list[str]:
    """Return list of errors (empty if OK)."""
    errors: list[str] = []
    idx = _phase_index(phase)

    if idx > 0:
        prior = PHASE_ORDER[idx - 1]
        prior_manifest = variant_dir / "artifacts" / prior / "phase_manifest.json"
        if not prior_manifest.is_file():
            errors.append(f"MISSING prior manifest: {prior_manifest}")
        else:
            pm = _load_json(prior_manifest)
            if pm.get("phase") != prior:
                errors.append(f"Prior manifest phase mismatch: {pm.get('phase')} != {prior}")

    for src_phase, key, desc in PHASE_INPUTS.get(phase, []):
        manifest_path = variant_dir / "artifacts" / src_phase / "phase_manifest.json"
        if not manifest_path.is_file():
            errors.append(f"MISSING manifest for input source {src_phase}: {manifest_path}")
            continue
        manifest = _load_json(manifest_path)
        rel = manifest.get("outputs", {}).get(key)
        if not rel:
            errors.append(f"Manifest {src_phase} missing outputs[{key!r}] ({desc})")
            continue
        resolved = _resolve(variant_dir, rel)
        if not resolved.is_file():
            errors.append(f"INPUT FILE MISSING ({desc}): {resolved}")

    for name in PHASE_VARIANT_FILES.get(phase, []):
        p = variant_dir / name
        if not p.is_file():
            errors.append(f"MISSING variant file required by {phase}: {p}")

    return errors


def verify_chain_alignment(variant_dir: Path) -> list[str]:
    """Cross-check manifest output keys vs next-phase inputs for full pipeline."""
    errors: list[str] = []
    for i, phase in enumerate(PHASE_ORDER):
        contract = _load_contract(variant_dir, phase)
        if contract is None:
            continue
        manifest_path = variant_dir / "artifacts" / phase / "phase_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _load_json(manifest_path)
        for key, rel in manifest.get("outputs", {}).items():
            resolved = _resolve(variant_dir, rel)
            if not resolved.is_file():
                errors.append(f"{phase} manifest output missing on disk: {key} -> {resolved}")

        expected = _expected_outputs(contract)
        required_only = dict(contract.get("outputs") or {})
        for key in required_only:
            if key not in manifest.get("outputs", {}):
                errors.append(f"{phase} manifest missing contract output key: {key}")

        if i + 1 < len(PHASE_ORDER):
            nxt = PHASE_ORDER[i + 1]
            for src_phase, key, desc in PHASE_INPUTS.get(nxt, []):
                if src_phase != phase:
                    continue
                if key not in manifest.get("outputs", {}):
                    errors.append(
                        f"CHAIN GAP: {nxt} expects {phase}.outputs[{key}] ({desc})"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, help="e.g. baseline_column_transformer")
    parser.add_argument(
        "--agent-tracing-root",
        default="/lustre/work/sweeden/agent-tracing-trace-baseline",
        type=Path,
    )
    parser.add_argument("--phase", help="Phase to preboot-check (e.g. 04_model_training)")
    parser.add_argument(
        "--preboot",
        action="store_true",
        help="Fail if this phase cannot start (prior outputs + consumer inputs)",
    )
    parser.add_argument(
        "--review-chain",
        action="store_true",
        help="Print alignment table and verify all completed phases",
    )
    args = parser.parse_args()

    variant_dir = args.agent_tracing_root / "examples/rogii/traces/preprocessing" / args.variant
    if not variant_dir.is_dir():
        print(f"FATAL: variant dir not found: {variant_dir}", file=sys.stderr)
        return 2

    if args.preboot:
        if not args.phase:
            print("--preboot requires --phase", file=sys.stderr)
            return 2
        errors = verify_preboot(variant_dir, args.phase)
        if errors:
            print(f"PREBOOT FAILED for {args.variant} / {args.phase}:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print(f"PREBOOT OK: {args.variant} / {args.phase}")
        return 0

    if args.review_chain:
        print(f"=== Handoff review: {args.variant} ===\n")
        print(f"{'Phase':28} {'Prior':28} {'Output key':22} {'Path':40} {'Next consumer'}")
        print("-" * 130)
        for i, phase in enumerate(PHASE_ORDER):
            manifest_path = variant_dir / "artifacts" / phase / "phase_manifest.json"
            if not manifest_path.is_file():
                print(f"{phase:28} {'(no manifest)':28}")
                continue
            manifest = _load_json(manifest_path)
            prior = manifest.get("prior_phase") or "—"
            consumers: dict[str, list[str]] = {}
            for nxt, reqs in PHASE_INPUTS.items():
                for src, key, desc in reqs:
                    if src == phase:
                        consumers.setdefault(key, []).append(nxt)
            for key, rel in manifest.get("outputs", {}).items():
                nxt = ", ".join(consumers.get(key, ["—"]))
                print(f"{phase:28} {str(prior):28} {key:22} {rel:40} {nxt}")

        errors = verify_chain_alignment(variant_dir)
        if errors:
            print("\nCHAIN ALIGNMENT ERRORS:")
            for e in errors:
                print(f"  - {e}")
            return 1
        print("\nCHAIN ALIGNMENT: OK (all manifests on disk match consumer inputs)")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
