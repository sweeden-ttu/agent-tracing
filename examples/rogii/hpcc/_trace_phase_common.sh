#!/usr/bin/env bash
# Shared setup for trace phase Slurm jobs (sourced by run_trace_phase.slurm).
set -euo pipefail

: "${VARIANT:?set VARIANT=baseline_column_transformer|...}"
: "${TRACE_PHASE:?set TRACE_PHASE=01_data_analysis|...}"

AGENT_TRACING_ROOT="${AGENT_TRACING_ROOT:-/lustre/work/sweeden/agent-tracing-trace-baseline}"
ROGII_ROOT="${ROGII_ROOT:-/lustre/work/sweeden/rogii}"
TRACE_VARIANT="${TRACE_VARIANT:-${VARIANT}}"
DATA_DIR="${DATA_DIR:-${ROGII_ROOT}/data}"
MAX_TRAIN_ROWS="${MAX_TRAIN_ROWS:-}"

VARIANT_DIR="${AGENT_TRACING_ROOT}/examples/rogii/traces/preprocessing/${VARIANT}"
NB_DIR="${VARIANT_DIR}/notebooks"
ARTIFACTS_DIR="${VARIANT_DIR}/artifacts"
LOG_DIR="${VARIANT_DIR}/logs"
HPCC_DIR="${AGENT_TRACING_ROOT}/examples/rogii/hpcc"

mkdir -p "${LOG_DIR}" "${ARTIFACTS_DIR}"

export AGENT_TRACING_ROOT ROGII_ROOT TRACE_VARIANT VARIANT VARIANT_DIR DATA_DIR

echo "=== trace phase job ==="
echo "variant:      ${VARIANT}"
echo "trace_phase:  ${TRACE_PHASE}"
echo "variant_dir:  ${VARIANT_DIR}"
echo "artifacts:    ${ARTIFACTS_DIR}"
echo "data_dir:     ${DATA_DIR}"

# Rogii Matador module stack (same as train_tcn.slurm)
RUN_DIR="${ROGII_ROOT}"
# shellcheck disable=SC1091
source "${RUN_DIR}/hpcc/slurm_module_init.sh"
init_slurm_modules
# shellcheck disable=SC1091
source "${RUN_DIR}/hpcc/load_matador_modules.sh"
load_matador_modules
# shellcheck disable=SC1091
source "${RUN_DIR}/hpcc/_variant_conda_env.sh"
matador_activate_variant_env

echo "=== preboot: verify prior-phase handoff ==="
python "${HPCC_DIR}/verify_phase_handoff.py" \
  --variant "${VARIANT}" \
  --agent-tracing-root "${AGENT_TRACING_ROOT}" \
  --phase "${TRACE_PHASE}" \
  --preboot
