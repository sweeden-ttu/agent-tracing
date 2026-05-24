#!/usr/bin/env bash
# Bootstrap conda env for local Kaggle pipeline runs (LightGBM + kaggle CLI).
#
#   cd examples/rogii/kaggle/rogii-unified-baseline
#   bash ensure_kaggle_login_env.sh
#
# Creates (or refreshes):
#   /lustre/work/sweeden/sweeden/envs/kc-rogii-wellbore-geology-prediction  (from rogii/environment.yml)
# Falls back to extending rogii-trace-slurm with `kaggle` if mamba env create fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROGII_ROOT="${ROGII_ROOT:-/lustre/work/sweeden/rogii}"
ENV_YML="${ROGII_ROOT}/environment.yml"
KC_PREFIX="${KAGGLE_CONDA_PREFIX:-/lustre/work/sweeden/sweeden/envs/kc-rogii-wellbore-geology-prediction}"
SLURM_PREFIX="/lustre/work/sweeden/sweeden/envs/rogii-trace-slurm"
MINIFORGE="${MINIFORGE_ROOT:-/home/sweeden/miniforge3}"
PKGS_DIR="${CONDA_PKGS_DIRS:-/lustre/scratch/sweeden/conda-pkgs}"

if [[ ! -f "${MINIFORGE}/etc/profile.d/conda.sh" ]]; then
  echo "FATAL: miniforge not found at ${MINIFORGE}" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "${MINIFORGE}/etc/profile.d/conda.sh"
export CONDA_NO_PLUGINS=true
export CONDA_PKGS_DIRS="${PKGS_DIR}"
mkdir -p "${PKGS_DIR}" "$(dirname "${KC_PREFIX}")"

_need_rebuild() {
  local py="${1}/bin/python"
  [[ -x "${py}" ]] || return 0
  "${py}" -c "import lightgbm, kaggle" 2>/dev/null && return 1
  return 0
}

if [[ -f "${ENV_YML}" ]] && _need_rebuild "${KC_PREFIX}"; then
  echo "=== mamba env create: kc-rogii-wellbore-geology-prediction ==="
  if [[ -d "${KC_PREFIX}" ]]; then
    rm -rf "${KC_PREFIX}"
  fi
  mamba env create --prefix "${KC_PREFIX}" -f "${ENV_YML}" -y || {
    echo "WARN: mamba create from ${ENV_YML} failed; extending rogii-trace-slurm instead" >&2
  }
fi

if [[ -x "${KC_PREFIX}/bin/python" ]] && "${KC_PREFIX}/bin/python" -c "import lightgbm" 2>/dev/null; then
  if ! "${KC_PREFIX}/bin/python" -c "import kaggle" 2>/dev/null; then
    echo "=== pip install kaggle into ${KC_PREFIX} ==="
    "${KC_PREFIX}/bin/pip" install --no-cache-dir kaggle
  fi
  echo "OK: ${KC_PREFIX}"
  "${KC_PREFIX}/bin/python" -c "import lightgbm, kaggle; print('lightgbm+kaggle ready')"
  exit 0
fi

# Fallback: shared Slurm env + kaggle pip
if [[ ! -x "${SLURM_PREFIX}/bin/python" ]]; then
  echo "=== creating rogii-trace-slurm (no kc env) ==="
  bash "${SCRIPT_DIR}/../../hpcc/ensure_trace_slurm_env.sh"
fi

if ! "${SLURM_PREFIX}/bin/python" -c "import kaggle" 2>/dev/null; then
  echo "=== pip install kaggle into ${SLURM_PREFIX} ==="
  "${SLURM_PREFIX}/bin/pip" install --no-cache-dir kaggle
fi

echo "OK: ${SLURM_PREFIX} (fallback; export KAGGLE_CONDA_PREFIX=${SLURM_PREFIX})"
"${SLURM_PREFIX}/bin/python" -c "import lightgbm, kaggle; print('lightgbm+kaggle ready')"
