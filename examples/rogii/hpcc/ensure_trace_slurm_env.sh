#!/usr/bin/env bash
# Bootstrap the shared Slurm conda env on a login node (once).
#
#   cd /lustre/work/sweeden/agent-tracing-trace-baseline/examples/rogii
#   bash hpcc/ensure_trace_slurm_env.sh
#
# Env lands on lustre (not $HOME) to avoid quota issues on compute nodes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_PREFIX="${TRACE_CONDA_PREFIX:-/lustre/work/sweeden/sweeden/envs/rogii-trace-slurm}"
PKGS_DIR="${CONDA_PKGS_DIRS:-/lustre/scratch/sweeden/conda-pkgs}"
MINIFORGE="${MINIFORGE_ROOT:-/home/sweeden/miniforge3}"

if [[ ! -f "${MINIFORGE}/etc/profile.d/conda.sh" ]]; then
  echo "FATAL: miniforge not found at ${MINIFORGE}" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "${MINIFORGE}/etc/profile.d/conda.sh"
export CONDA_NO_PLUGINS=true
export CONDA_PKGS_DIRS="${PKGS_DIR}"
mkdir -p "${PKGS_DIR}" "$(dirname "${ENV_PREFIX}")"

if [[ -x "${ENV_PREFIX}/bin/python" ]]; then
  if "${ENV_PREFIX}/bin/python" -c "import lightgbm, sklearn, pandas, numpy" 2>/dev/null; then
    echo "Env already OK: ${ENV_PREFIX}"
    exit 0
  fi
  echo "Incomplete env at ${ENV_PREFIX}; rebuilding ..."
  rm -rf "${ENV_PREFIX}"
fi

echo "=== mamba create --prefix ${ENV_PREFIX} ==="
mamba create --prefix "${ENV_PREFIX}" -y \
  python=3.11 pip pandas numpy scikit-learn scipy matplotlib pyarrow pyyaml tqdm \
  -c conda-forge --override-channels

echo "=== pip install lightgbm xgboost ==="
"${ENV_PREFIX}/bin/pip" install --no-cache-dir lightgbm xgboost

echo "=== verify ==="
"${ENV_PREFIX}/bin/python" - <<'PY'
import lightgbm, sklearn, pandas, numpy, scipy
print("rogii-trace-slurm deps OK")
PY

echo "Done. Slurm jobs should set:"
echo "  export TRACE_CONDA_PREFIX=${ENV_PREFIX}"
