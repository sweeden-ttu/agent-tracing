#!/usr/bin/env bash
# Regenerate notebook, push kernel, optionally poll status.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_kaggle_env.sh"
_kaggle_env_check

if ! command -v kaggle >/dev/null 2>&1; then
  echo "FATAL: kaggle CLI not found after sourcing _kaggle_env.sh" >&2
  exit 1
fi

bash sync_bundle.sh
"${KAGGLE_CONDA_PREFIX}/bin/python" embed_notebook.py

echo "=== kaggle kernels push ==="
kaggle kernels push -p .

KERNEL_SLUG="${KAGGLE_KERNEL_SLUG:-scottweeden/rogii-trace-baseline-smoke}"
if [[ "${KAGGLE_POLL:-0}" == "1" ]]; then
  kaggle kernels status "${KERNEL_SLUG}"
fi

echo "Done. Kernel: https://www.kaggle.com/code/${KERNEL_SLUG}"
