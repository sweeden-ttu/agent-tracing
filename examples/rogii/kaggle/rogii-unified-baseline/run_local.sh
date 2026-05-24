#!/usr/bin/env bash
# Local full pipeline on synthetic/competition data (LightGBM + optional episodic + submit).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${ROGII_DATA_DIR:-/lustre/work/sweeden/rogii/data}"
OUT_DIR="${ROGII_OUT_DIR:-${SCRIPT_DIR}/output}"
SUBMIT="${ROGII_SUBMIT:-1}"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_kaggle_env.sh"
_kaggle_env_check

mkdir -p "${OUT_DIR}"
echo "=== ROGII Kaggle pipeline (local) ==="
echo "PYTHON:   ${KAGGLE_CONDA_PREFIX}/bin/python"
echo "DATA_DIR: ${DATA_DIR}"
echo "OUT_DIR:  ${OUT_DIR}"
echo "KAGGLE_CONFIG_DIR: ${KAGGLE_CONFIG_DIR:-<default>}"

ARGS=(
  "${SCRIPT_DIR}/run_kaggle_pipeline.py"
  --data-dir "${DATA_DIR}"
  --work-dir "${OUT_DIR}"
  --episodic-episodes "${ROGII_EPISODIC_EPISODES:-2}"
  --episodic-epochs "${ROGII_EPISODIC_EPOCHS:-30}"
)
if [[ "${SUBMIT}" == "0" ]]; then
  ARGS+=(--no-submit)
fi

"${KAGGLE_CONDA_PREFIX}/bin/python" "${ARGS[@]}"

if [[ -f "${OUT_DIR}/pipeline_metrics.json" ]]; then
  "${KAGGLE_CONDA_PREFIX}/bin/python" - <<PY
import json
m = json.load(open("${OUT_DIR}/pipeline_metrics.json"))
print(
    f"cv_rmse={m.get('cv_rmse', m.get('final_cv_rmse_feet')):.4f}  "
    f"cumulative={m.get('cumulative_rmse_feet', 0):.4f}  "
    f"backend={m.get('backend', '?')}"
)
ks = m.get("kaggle_submit") or {}
print(f"kaggle_submit={ks.get('submitted', ks)}")
PY
fi
