#!/usr/bin/env bash
# Submit a chained GPU Slurm pipeline: phase 01 → 02 → … → 06.
#
# Each job preboot-validates prior-phase artifacts (verify_phase_handoff.py --preboot)
# before running phase_runner for the current phase.
#
# Usage:
#   cd /lustre/work/sweeden/agent-tracing-trace-baseline/examples/rogii
#   VARIANT=baseline_column_transformer ./hpcc/submit_trace_pipeline.sh
#   VARIANT=baseline_column_transformer START_PHASE=03_feature_engineering ./hpcc/submit_trace_pipeline.sh
#
# Rules: one active pipeline job per trace branch — script refuses if a matching job exists.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROGII_EXAMPLES="$(cd "${SCRIPT_DIR}/.." && pwd)"
AGENT_TRACING_ROOT="${AGENT_TRACING_ROOT:-$(cd "${ROGII_EXAMPLES}/../.." && pwd)}"
ROGII_ROOT="${ROGII_ROOT:-/lustre/work/sweeden/rogii}"

VARIANT="${VARIANT:-baseline_column_transformer}"
TRACE_VARIANT="${TRACE_VARIANT:-${VARIANT}}"
START_PHASE="${START_PHASE:-01_data_analysis}"
DRY_RUN="${DRY_RUN:-0}"

PHASES=(
  01_data_analysis
  02_statistical_framework
  03_feature_engineering
  04_model_training
  05_evaluation
  06_submission
)

VARIANT_DIR="${AGENT_TRACING_ROOT}/examples/rogii/traces/preprocessing/${VARIANT}"
SLURM_SCRIPT="${AGENT_TRACING_ROOT}/examples/rogii/hpcc/run_trace_phase.slurm"

if [[ ! -f "${SLURM_SCRIPT}" ]]; then
  echo "FATAL: missing ${SLURM_SCRIPT}" >&2
  exit 1
fi

# Map variant → short job tag (trace_baseline, trace_typewell, …)
case "${VARIANT}" in
  baseline_column_transformer) JOB_TAG=trace_baseline ;;
  typewell_gr_alignment) JOB_TAG=trace_typewell ;;
  ps_point_leakage_aware) JOB_TAG=trace_ps ;;
  robust_scale_log1p) JOB_TAG=trace_robust ;;
  parallel_multiwell_loader) JOB_TAG=trace_parallel ;;
  formation_plane_spatial) JOB_TAG=trace_formation ;;
  *) JOB_TAG="trace_${VARIANT%%_*}" ;;
esac

echo "=== existing jobs for ${JOB_TAG} ==="
if squeue -u "${USER}" -o "%.18i %.30j %.8T" 2>/dev/null | grep -qE "${JOB_TAG}|${JOB_TAG}_p"; then
  echo "REFUSE: a ${JOB_TAG} pipeline job is already queued or running." >&2
  squeue -u "${USER}" -o "%.18i %.9P %.30j %.8T %.10M %R" | grep -E "${JOB_TAG}|trace_" || true
  exit 1
fi

echo "=== handoff review (login node) ==="
python "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/verify_phase_handoff.py" \
  --variant "${VARIANT}" \
  --agent-tracing-root "${AGENT_TRACING_ROOT}" \
  --review-chain || true

start_idx=0
for i in "${!PHASES[@]}"; do
  [[ "${PHASES[$i]}" == "${START_PHASE}" ]] && start_idx=$i && break
done

mkdir -p "${VARIANT_DIR}/logs"
cd "${VARIANT_DIR}"

prev_job=""
declare -a job_ids=()

for ((i=start_idx; i<${#PHASES[@]}; i++)); do
  phase="${PHASES[$i]}"
  phase_num="${phase%%_*}"
  job_name="${JOB_TAG}_p${phase_num}"

  extra=()
  case "${phase}" in
    01_data_analysis|02_statistical_framework|05_evaluation)
      extra=(--time=01:00:00 --mem=32G)
      ;;
    03_feature_engineering)
      extra=(--time=02:00:00 --mem=64G)
      ;;
    04_model_training)
      extra=(--time=04:00:00 --mem=100G)
      ;;
    06_submission)
      extra=(--time=00:30:00 --mem=16G)
      ;;
  esac

  dep=()
  if [[ -n "${prev_job}" ]]; then
    dep=(--dependency=afterok:"${prev_job}")
  fi

  cmd=(
    sbatch
    --parsable
    -J "${job_name}"
    "${dep[@]}"
    --export=ALL,VARIANT="${VARIANT}",TRACE_VARIANT="${TRACE_VARIANT}",TRACE_PHASE="${phase}",AGENT_TRACING_ROOT="${AGENT_TRACING_ROOT}",ROGII_ROOT="${ROGII_ROOT}"
    "${extra[@]}"
    "${SLURM_SCRIPT}"
  )

  echo "submit: ${job_name} phase=${phase} dep=${prev_job:-none}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "  DRY_RUN: ${cmd[*]}"
    prev_job="DRY_${phase_num}"
  else
    jid="$("${cmd[@]}")"
    echo "  job_id=${jid}"
    job_ids+=("${jid}")
    prev_job="${jid}"
  fi
done

echo
echo "=== pipeline submitted ==="
echo "variant: ${VARIANT}"
echo "jobs: ${job_ids[*]:-DRY_RUN}"
echo "logs: ${VARIANT_DIR}/logs/"
echo
echo "Monitor:"
echo "  squeue -u \$USER | grep ${JOB_TAG}"
echo "  sacct -j ${job_ids[0]:-JOBID} --format=JobID,JobName,State,ExitCode,Elapsed"
