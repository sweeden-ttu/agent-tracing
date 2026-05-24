#!/usr/bin/env bash
# Source before local Kaggle pipeline runs (login node).
# Provides LightGBM via rogii-trace-slurm and Kaggle CLI credentials.

# shellcheck disable=SC2034
_KAGGLE_ENV_SH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_kaggle_env.sh"

# Prefer kc-rogii (environment.yml) when present; else shared Slurm env with LightGBM.
_KAGGLE_ENV_CANDIDATES=(
  "${KAGGLE_CONDA_PREFIX:-}"
  "/lustre/work/sweeden/sweeden/envs/kc-rogii-wellbore-geology-prediction"
  "/lustre/work/sweeden/sweeden/envs/rogii-trace-slurm"
)

_kaggle_env_prefix=""
for _pfx in "${_KAGGLE_ENV_CANDIDATES[@]}"; do
  [[ -n "${_pfx}" && -x "${_pfx}/bin/python" ]] || continue
  _kaggle_env_prefix="${_pfx}"
  break
done

if [[ -z "${_kaggle_env_prefix}" ]]; then
  echo "FATAL: no Kaggle conda env found. Run:" >&2
  echo "  bash examples/rogii/kaggle/rogii-unified-baseline/ensure_kaggle_login_env.sh" >&2
  return 1 2>/dev/null || exit 1
fi

export KAGGLE_CONDA_PREFIX="${_kaggle_env_prefix}"
export PATH="${KAGGLE_CONDA_PREFIX}/bin:${PATH}"

# Credentials: default CLI location is ~/.kaggle; this node uses ~/.config/kaggle.
if [[ -f "${HOME}/.config/kaggle/kaggle.json" ]]; then
  export KAGGLE_CONFIG_DIR="${KAGGLE_CONFIG_DIR:-${HOME}/.config/kaggle}"
elif [[ -f "${HOME}/.kaggle/kaggle.json" ]]; then
  export KAGGLE_CONFIG_DIR="${KAGGLE_CONFIG_DIR:-${HOME}/.kaggle}"
fi

# User-local kaggle CLI (pip --user) when not in the conda env.
if ! command -v kaggle >/dev/null 2>&1 && [[ -x "${HOME}/.local/bin/kaggle" ]]; then
  export PATH="${HOME}/.local/bin:${PATH}"
fi

_kaggle_env_python() {
  "${KAGGLE_CONDA_PREFIX}/bin/python" "$@"
}

_kaggle_env_check() {
  _kaggle_env_python -c "import lightgbm" 2>/dev/null || {
    echo "FATAL: lightgbm missing in ${KAGGLE_CONDA_PREFIX}" >&2
    return 1
  }
  if [[ -n "${KAGGLE_CONFIG_DIR:-}" && ! -f "${KAGGLE_CONFIG_DIR}/kaggle.json" ]]; then
    echo "WARN: KAGGLE_CONFIG_DIR=${KAGGLE_CONFIG_DIR} but kaggle.json not found" >&2
  fi
  if command -v kaggle >/dev/null 2>&1; then
    # `competitions list` does not accept -q (unlike submit); grep slug instead.
    if ! kaggle competitions list -s rogii 2>/dev/null | grep -q rogii-wellbore-geology-prediction; then
      echo "WARN: kaggle CLI found but auth/list check failed (fix kaggle.json or network)" >&2
    fi
  else
    echo "WARN: kaggle CLI not on PATH; submit will be skipped" >&2
  fi
}
