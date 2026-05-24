#!/bin/bash
#SBATCH -J trace_phase
#SBATCH -o logs/%x.o%j
#SBATCH -e logs/%x.e%j
#SBATCH -p matador
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gpus-per-node=1
#SBATCH -t 02:00:00
#SBATCH -A default
#SBATCH --mail-user=sweeden@ttu.edu
#SBATCH --mail-type=BEGIN,END,FAIL
#
# Run one Rogii trace pipeline phase (01–06) for a preprocessing variant.
#
# Required exports (submit_trace_pipeline.sh sets these):
#   VARIANT=baseline_column_transformer
#   TRACE_VARIANT=baseline_column_transformer
#   TRACE_PHASE=01_data_analysis|02_statistical_framework|...
#
# Optional:
#   AGENT_TRACING_ROOT=/lustre/work/sweeden/agent-tracing-trace-baseline
#   ROGII_ROOT=/lustre/work/sweeden/rogii
#   DATA_DIR=/lustre/work/sweeden/rogii/data
#   MAX_TRAIN_ROWS=   (empty = full train for phase 04)
#
# Phase 04 override example:
#   sbatch --export=ALL,VARIANT,TRACE_VARIANT,TRACE_PHASE=04_model_training,MAX_TRAIN_ROWS= \
#     --time=04:00:00 --mem=100G hpcc/run_trace_phase.slurm

set -euo pipefail

AGENT_TRACING_ROOT="${AGENT_TRACING_ROOT:-/lustre/work/sweeden/agent-tracing-trace-baseline}"
VARIANT="${VARIANT:?}"
TRACE_PHASE="${TRACE_PHASE:?}"
TRACE_VARIANT="${TRACE_VARIANT:-${VARIANT}}"

VARIANT_DIR="${AGENT_TRACING_ROOT}/examples/rogii/traces/preprocessing/${VARIANT}"
cd "${VARIANT_DIR}"
mkdir -p logs

# Job name suffix (trace_baseline_p04, etc.)
PHASE_TAG="${TRACE_PHASE%%_*}"
export SLURM_JOB_NAME="trace_${TRACE_VARIANT%%_*}_${PHASE_TAG}"

# Per-phase walltime/memory are set via sbatch flags in submit_trace_pipeline.sh.

source "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/_trace_phase_common.sh"

echo "=== GPU check (matador) ==="
echo "SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-?}"
echo "SLURM_GPUS_ON_NODE=${SLURM_GPUS_ON_NODE:-?}"
nvidia-smi -L 2>/dev/null || echo "(no nvidia-smi)"
python - <<'PY'
try:
    import torch
    print("torch", torch.__version__, "cuda", torch.cuda.is_available())
except ImportError:
    print("torch not installed (OK for LightGBM trace phases)")
PY

RUN_ARGS=(
  --variant "${VARIANT}"
  --phase "${TRACE_PHASE}"
  --agent-tracing-root "${AGENT_TRACING_ROOT}"
  --data-dir "${DATA_DIR}"
)
if [[ -n "${MAX_TRAIN_ROWS}" ]]; then
  RUN_ARGS+=(--max-train-rows "${MAX_TRAIN_ROWS}")
fi

echo "=== execute phase ==="
srun --ntasks=1 python "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/run_trace_phase.py" "${RUN_ARGS[@]}"

echo "=== post-run: verify phase manifest outputs ==="
manifest="${ARTIFACTS_DIR}/${TRACE_PHASE}/phase_manifest.json"
if [[ ! -f "${manifest}" ]]; then
  echo "FATAL: phase manifest missing after run: ${manifest}" >&2
  exit 1
fi
python - <<PY
import json
from pathlib import Path
m = json.loads(Path("${manifest}").read_text())
root = Path("${VARIANT_DIR}")
missing = []
for k, rel in m.get("outputs", {}).items():
    p = root / rel
    if not p.is_file():
        missing.append(f"{k} -> {p}")
if missing:
    raise SystemExit("Missing outputs: " + "; ".join(missing))
print("POST-RUN OK:", m["phase"], "outputs:", list(m["outputs"]))
PY

echo "=== done ${TRACE_PHASE} @ $(date -Iseconds) ==="
ls -la "${ARTIFACTS_DIR}/${TRACE_PHASE}/" || true
