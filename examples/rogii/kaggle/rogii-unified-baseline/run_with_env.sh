#!/usr/bin/env bash
# Run any command under the Kaggle login-node conda env + credentials.
# Usage: bash run_with_env.sh python run_kaggle_pipeline.py --data-dir ... --work-dir ...

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_kaggle_env.sh"
_kaggle_env_check
exec "${KAGGLE_CONDA_PREFIX}/bin/python" "$@"
