#!/usr/bin/env bash
# Push strong tabular competition kernel (primary submit target).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_kaggle_env.sh"
_kaggle_env_check

"${KAGGLE_CONDA_PREFIX}/bin/python" embed_notebook.py
cp kernel-metadata-rogii_trace_tabular_submit.json kernel-metadata.json

echo "=== kaggle kernels push (tabular submit) ==="
kaggle kernels push -p .
echo "https://www.kaggle.com/code/scottweeden/rogii-trace-tabular-submit"
