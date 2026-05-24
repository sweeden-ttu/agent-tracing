#!/usr/bin/env bash
# Shared setup for trace phase Slurm jobs (sourced by run_trace_phase.slurm).
set -euo pipefail

: "${VARIANT:?set VARIANT=baseline_column_transformer|...}"
: "${TRACE_PHASE:?set TRACE_PHASE=01_data_analysis|...}"

AGENT_TRACING_ROOT="${AGENT_TRACING_ROOT:-/lustre/work/sweeden/agent-tracing-trace-baseline}"
ROGII_ROOT="${ROGII_ROOT:-/lustre/work/sweeden/rogii}"
TRACE_VARIANT="${TRACE_VARIANT:-${VARIANT}}"
TRACE_CONDA_PREFIX="${TRACE_CONDA_PREFIX:-/lustre/work/sweeden/sweeden/envs/rogii-trace-slurm}"
DATA_DIR="${DATA_DIR:-${ROGII_ROOT}/data}"
MAX_TRAIN_ROWS="${MAX_TRAIN_ROWS:-}"
SLURM_PARTITION="${SLURM_PARTITION:-matador}"

VARIANT_DIR="${AGENT_TRACING_ROOT}/examples/rogii/traces/preprocessing/${VARIANT}"
NB_DIR="${VARIANT_DIR}/notebooks"
ARTIFACTS_DIR="${VARIANT_DIR}/artifacts"
LOG_DIR="${VARIANT_DIR}/logs"
HPCC_DIR="${AGENT_TRACING_ROOT}/examples/rogii/hpcc"

mkdir -p "${LOG_DIR}" "${ARTIFACTS_DIR}"

export AGENT_TRACING_ROOT ROGII_ROOT TRACE_VARIANT VARIANT VARIANT_DIR DATA_DIR TRACE_CONDA_PREFIX

echo "=== trace phase job ==="
echo "variant:      ${VARIANT}"
echo "trace_phase:  ${TRACE_PHASE}"
echo "partition:    ${SLURM_JOB_PARTITION:-local}"
echo "node:         ${SLURMD_NODENAME:-${SLURM_JOB_NODELIST:-local}}"
echo "variant_dir:  ${VARIANT_DIR}"
echo "conda_prefix: ${TRACE_CONDA_PREFIX}"

# Hard gate: trace GPU jobs must run on matador, not nocona/login
if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  if [[ "${SLURM_JOB_PARTITION:-}" != "matador" ]]; then
    echo "FATAL: wrong partition '${SLURM_JOB_PARTITION}' — trace jobs require -p matador" >&2
    exit 1
  fi
  if [[ "${SLURM_GPUS_ON_NODE:-0}" -lt 1 && "${SLURM_GPUS_PER_NODE:-0}" -lt 1 ]]; then
    echo "FATAL: no GPU allocated — matador jobs require --gpus-per-node=1" >&2
    exit 1
  fi
fi

# Matador module stack (gcc / cuda / python) — sourced from rogii hpcc helpers
RUN_DIR="${ROGII_ROOT}"
# shellcheck disable=SC1091
source "${RUN_DIR}/hpcc/slurm_module_init.sh"
init_slurm_modules
# shellcheck disable=SC1091
source "${RUN_DIR}/hpcc/load_matador_modules.sh"
load_matador_modules

# Pre-built lustre conda env (never create envs on compute nodes)
# shellcheck disable=SC1091
source "${HPCC_DIR}/_trace_phase_env.sh"
trace_phase_activate_env

echo "=== preboot: verify prior-phase handoff ==="
python "${HPCC_DIR}/verify_phase_handoff.py" \
  --variant "${VARIANT}" \
  --agent-tracing-root "${AGENT_TRACING_ROOT}" \
  --phase "${TRACE_PHASE}" \
  --preboot
