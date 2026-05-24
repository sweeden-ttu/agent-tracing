#!/usr/bin/env bash
# Auto-generated: submit all six Rogii variant pipelines (one active job per variant).
set -euo pipefail
ROOT="/lustre/work/frontier-evals"
GENERATED="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMIT="${1:-}"
for script in "${GENERATED}"/submit_*.sh; do
  base="$(basename "${script}")"
  [[ "${base}" == submit_all_variants.sh ]] && continue
  tag="${base#submit_}"
  tag="${tag%.sh}"
  if squeue -u "${USER}" -o "%.30j" 2>/dev/null | grep -qE "trace_${tag}|trace_${tag}_p"; then
    echo "SKIP ${script}: job already queued/running"
    continue
  fi
  echo "=== ${script} ==="
  if [[ "${SUBMIT}" == "--submit" ]]; then
    bash "${script}"
  else
    DRY_RUN=1 bash "${script}"
  fi
done
echo "Done. Pass --submit to enqueue Slurm jobs."
