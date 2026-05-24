#!/usr/bin/env bash
# Copy Rogii pipeline + train_predict into this kernel folder for Kaggle push.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
ROGII="${ROGII_ROOT:-/lustre/work/sweeden/rogii}"

mkdir -p "$ROOT/pipeline"
cp "$ROGII/train_predict.py" "$ROOT/"
for f in \
  __init__.py \
  competition_data.py \
  cv_orchestrator.py \
  nb_support.py \
  preprocessor.py \
  target_diagnostician.py \
  well_group_detector.py \
  temporal_cnn.py \
  episodic_benchmark.py \
  ensemble_blend.py; do
  cp "$ROGII/pipeline/$f" "$ROOT/pipeline/"
done
echo "Synced pipeline from $ROGII -> $ROOT"
echo "Runners: run_baseline.py run_episodic_kaggle.py run_kaggle_pipeline.py (kept in $ROOT)"
