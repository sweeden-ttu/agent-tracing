#!/usr/bin/env bash
# Submit trace_language.csv Matador GPU work: episodic TCN per variant + six-agent ensemble.
#
# Episodic (~48h, one job per variant):
#   VARIANT=baseline_column_transformer sbatch hpcc/train_tcn_episodic.slurm
#
# Ensemble (~3h, after all episodic jobs succeed):
#   sbatch hpcc/train_ensemble.slurm
#
# Usage:
#   bash examples/rogii/hpcc/submit_trace_matador_training.sh              # dry-run
#   bash examples/rogii/hpcc/submit_trace_matador_training.sh --submit
#   bash examples/rogii/hpcc/submit_trace_matador_training.sh --submit --ensemble-only

set -euo pipefail

ROGII_ROOT="${ROGII_ROOT:-/lustre/work/sweeden/rogii}"
EPISODIC_SLURM="${ROGII_ROOT}/hpcc/train_tcn_episodic.slurm"
ENSEMBLE_SLURM="${ROGII_ROOT}/hpcc/train_ensemble.slurm"
SUBMIT="${1:-}"
ENSEMBLE_ONLY="${2:-}"
JOB_IDS_FILE="${ROGII_ROOT}/logs/trace_episodic_job_ids.tsv"

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

cd "${ROGII_ROOT}"
mkdir -p logs artifacts/checkpoints

submit_episodic() {
  local -a submitted_ids=()
  : > "${JOB_IDS_FILE}"
  echo -e "variant\tjob_id\tjob_name" >> "${JOB_IDS_FILE}"

  for v in "${VARIANTS[@]}"; do
    tag="$(variant_job_tag "${v}")"
    if squeue -u "${USER}" -o "%.30j" 2>/dev/null | grep -qE "rogii_epi_${tag}"; then
      echo "SKIP episodic ${v}: rogii_epi_${tag} already active"
      # Recover job id from squeue if possible
      jid="$(squeue -u "${USER}" -h -o "%i %j" | awk -v n="rogii_epi_${tag}" '$2 ~ n {print $1; exit}')"
      if [[ -n "${jid}" ]]; then
        echo -e "${v}\t${jid}\trogii_epi_${tag}" >> "${JOB_IDS_FILE}"
        submitted_ids+=("${jid}")
      fi
      continue
    fi

    ckpt="artifacts/checkpoints/${v}"
    mkdir -p "${ckpt}/episodes" "artifacts/variants/${v}" "artifacts/model_card/${v}"

    echo "=== episodic ${v} ==="
    if [[ "${SUBMIT}" != "--submit" ]]; then
      echo "  DRY_RUN: review + sbatch VARIANT=${v} -J rogii_epi_${tag}"
      continue
    fi

    bash "${ROGII_ROOT}/hpcc/review_slurm_before_submit.sh" "${EPISODIC_SLURM}" "${v}"

    jid="$(
      sbatch --parsable \
        -J "rogii_epi_${tag}" \
        --export=ALL,VARIANT="${v}",TRACE_VARIANT="${v}" \
        "${EPISODIC_SLURM}"
    )"
    echo "  episodic job_id=${jid}"
    echo -e "${v}\t${jid}\trogii_epi_${tag}" >> "${JOB_IDS_FILE}"
    submitted_ids+=("${jid}")
  done

  EPISODIC_JOB_IDS=("${submitted_ids[@]}")
}

submit_ensemble() {
  if squeue -u "${USER}" -o "%.30j" 2>/dev/null | grep -qE 'rogii_ensemble'; then
    echo "SKIP ensemble: rogii_ensemble already queued or running"
    return 0
  fi

  local dep_args=()
  if [[ ${#EPISODIC_JOB_IDS[@]} -gt 0 ]]; then
    local dep="afterok"
    for jid in "${EPISODIC_JOB_IDS[@]}"; do
      dep="${dep}:${jid}"
    done
    dep_args=(--dependency="${dep}")
    echo "=== ensemble (starts after episodic jobs: ${EPISODIC_JOB_IDS[*]}) ==="
  else
    echo "=== ensemble (no episodic dependency — episodic jobs not tracked) ==="
  fi

  if [[ "${SUBMIT}" != "--submit" ]]; then
    echo "  DRY_RUN: sbatch ${dep_args[*]:-} -J rogii_ensemble ${ENSEMBLE_SLURM}"
    return 0
  fi

  bash "${ROGII_ROOT}/hpcc/review_slurm_before_submit.sh" "${ENSEMBLE_SLURM}" baseline_column_transformer || true

  local ens_jid
  ens_jid="$(
    sbatch --parsable \
      "${dep_args[@]}" \
      -J rogii_ensemble \
      "${ENSEMBLE_SLURM}"
  )"
  echo "  ensemble job_id=${ens_jid}"
  echo "rogii_ensemble\t${ens_jid}\trogii_ensemble" >> "${JOB_IDS_FILE}"
}

echo "=== trace_language Matador training (${ROGII_ROOT}) ==="

EPISODIC_JOB_IDS=()
if [[ "${ENSEMBLE_ONLY}" != "--ensemble-only" ]]; then
  submit_episodic
fi

if [[ "${ENSEMBLE_ONLY}" == "--ensemble-only" ]]; then
  # Load job ids from file for dependency
  if [[ -f "${JOB_IDS_FILE}" ]]; then
    mapfile -t EPISODIC_JOB_IDS < <(awk -F'\t' 'NR>1 && $2 ~ /^[0-9]+$/ {print $2}' "${JOB_IDS_FILE}")
  fi
  # Or use currently running episodic jobs
  if [[ ${#EPISODIC_JOB_IDS[@]} -eq 0 ]]; then
    mapfile -t EPISODIC_JOB_IDS < <(squeue -u "${USER}" -h -o "%i %j" | awk '/rogii_epi_/ {print $1}')
  fi
fi

submit_ensemble

echo "Job registry: ${JOB_IDS_FILE}"
echo "Monitor: squeue -u \$USER | grep -E 'rogii_epi|rogii_ensemble'"
