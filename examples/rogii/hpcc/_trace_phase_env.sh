#!/usr/bin/env bash
# Activate the pre-built lustre conda env for trace phase Slurm jobs.
#
# Env is created once on a login node:
#   bash examples/rogii/hpcc/ensure_trace_slurm_env.sh
#
# Slurm jobs must NOT create conda envs on compute nodes.

trace_phase_activate_env() {
  export CONDA_NO_PLUGINS=true

  local miniforge="${MINIFORGE_ROOT:-/home/sweeden/miniforge3}"
  if [[ ! -f "${miniforge}/etc/profile.d/conda.sh" ]]; then
    miniforge="/lustre/work/sweeden/miniforge3"
  fi
  if [[ ! -f "${miniforge}/etc/profile.d/conda.sh" ]]; then
    echo "FATAL: miniforge not found" >&2
    return 1
  fi
  # shellcheck disable=SC1091
  source "${miniforge}/etc/profile.d/conda.sh"

  local env_prefix="${TRACE_CONDA_PREFIX:-/lustre/work/sweeden/sweeden/envs/rogii-trace-slurm}"
  if [[ ! -x "${env_prefix}/bin/python" ]]; then
    echo "FATAL: trace Slurm env missing at ${env_prefix}" >&2
    echo "Run on login node: bash ${AGENT_TRACING_ROOT}/examples/rogii/hpcc/ensure_trace_slurm_env.sh" >&2
    return 1
  fi

  # Activate by prefix path (not env name — avoids EnvironmentNameNotFound on compute nodes)
  conda activate "${env_prefix}"
  export CONDA_DEFAULT_ENV="${env_prefix}"
  export PATH="${env_prefix}/bin:${PATH}"

  echo "CONDA_PREFIX=${env_prefix}"
  python -V
  python - <<'PY'
import lightgbm, sklearn, pandas, numpy, scipy
print("trace env deps OK")
PY
}
