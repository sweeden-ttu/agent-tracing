#!/usr/bin/env bash
# Submit trace_language.csv episodic TCN training (train_tcn_episodic.slurm) for one or all variants.
#
# trace_language.csv ~R104:
#   cd /lustre/work/sweeden/rogii && sbatch --parsable hpcc/train_tcn_episodic.slurm
#
# One active episodic job per variant; checkpoints under artifacts/checkpoints/${VARIANT}.
#
# Usage:
#   bash examples/rogii/hpcc/submit_trace_tcn_episodic.sh              # dry-run
#   bash examples/rogii/hpcc/submit_trace_tcn_episodic.sh --submit     # all six
#   VARIANT=baseline_column_transformer bash .../submit_trace_tcn_episodic.sh --submit

set -euo pipefail

ROGII_ROOT="${ROGII_ROOT:-/lustre/work/sweeden/rogii}"
SLURM_SCRIPT="${ROGII_ROOT}/hpcc/train_tcn_episodic.slurm"
SUBMIT="${1:-}"

VARIANTS=(
  baseline_column_transformer
  typewell_gr_alignment
  ps_point_leakage_aware
  robust_scale_log1p
  parallel_multiwell_loader
  formation_plane_spatial
)

variant_job_tag() {
  case "$1" in
    baseline_column_transformer) echo baseline ;;
    typewell_gr_alignment) echo typewell ;;
    ps_point_leakage_aware) echo ps ;;
    robust_scale_log1p) echo robust ;;
    parallel_multiwell_loader) echo parallel ;;
    formation_plane_spatial) echo formation ;;
    *) echo "${1%%_*}" ;;
  esac
}

if [[ -n "${VARIANT:-}" ]]; then
  VARIANTS=("${VARIANT}")
fi

cd "${ROGII_ROOT}"
mkdir -p logs artifacts/checkpoints

echo "=== trace_language episodic TCN submit (rogii ${SLURM_SCRIPT}) ==="

for v in "${VARIANTS[@]}"; do
  tag="$(variant_job_tag "${v}")"
  job_pat="rogii_epi_${tag}|rogii_tcn_epi|rogii_tcn"
  if squeue -u "${USER}" -o "%.30j" 2>/dev/null | grep -qE "${job_pat}"; then
    echo "SKIP ${v}: episodic/TCN job already queued or running (tag=${tag})"
    continue
  fi

  ckpt="artifacts/checkpoints/${v}"
  mkdir -p "${ckpt}/episodes" "artifacts/variants/${v}" "artifacts/model_card/${v}"

  echo "=== ${v} (job=rogii_epi_${tag}, checkpoints=${ckpt}) ==="
  if [[ "${SUBMIT}" != "--submit" ]]; then
    echo "  DRY_RUN: VARIANT=${v} sbatch -J rogii_epi_${tag} --export=ALL,VARIANT=${v},TRACE_VARIANT=${v} ${SLURM_SCRIPT}"
    continue
  fi

  if ! bash "${ROGII_ROOT}/hpcc/review_slurm_before_submit.sh" "${SLURM_SCRIPT}" "${v}"; then
    echo "REFUSE ${v}: consumer review failed" >&2
    continue
  fi

  jid="$(
    sbatch --parsable \
      -J "rogii_epi_${tag}" \
      --export=ALL,VARIANT="${v}",TRACE_VARIANT="${v}" \
      "${SLURM_SCRIPT}"
  )"
  echo "  submitted job_id=${jid}"
done

echo "Done. Pass --submit to enqueue. Monitor: squeue -u \$USER | grep rogii_epi"
