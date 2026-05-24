#!/usr/bin/env bash
# Propagate blocker fixes from main bundle to BoN worktrees (episodic z-score, env scripts, embed).
set -euo pipefail

MAIN="/lustre/work/sweeden/agent-tracing-trace-baseline/examples/rogii/kaggle/rogii-unified-baseline"
WORKTREES=(
  "/lustre/scratch/sweeden/rogii-kaggle-a3b7c2f1/agent-tracing-trace-baseline-42fa0c3b8ba4/examples/rogii/kaggle/rogii-unified-baseline"
  "/lustre/scratch/sweeden/opus-rogii-pipeline-a3f7c1e2/agent-tracing-trace-baseline-42fa0c3b8ba4/examples/rogii/kaggle/rogii-unified-baseline"
)

FILES=(
  _kaggle_env.sh
  ensure_kaggle_login_env.sh
  run_with_env.sh
  run_episodic_kaggle.py
  embed_notebook.py
  run_baseline_strong.py
  push_tabular.sh
)

for wt in "${WORKTREES[@]}"; do
  [[ -d "${wt}" ]] || { echo "skip missing ${wt}"; continue; }
  mkdir -p "${wt}"
  for f in "${FILES[@]}"; do
    cp "${MAIN}/${f}" "${wt}/${f}"
  done
  echo "synced -> ${wt}"
done

# GPT worktree: copy episodic fix into their pipeline if present
GPT_ROOT="/lustre/scratch/sweeden/rogii-kaggle-1a2b3c4d/agent-tracing-trace-baseline-42fa0c3b8ba4/examples/rogii/kaggle"
if [[ -d "${GPT_ROOT}/rogii_trace_baseline_smoke" ]]; then
  cp "${MAIN}/run_episodic_kaggle.py" "${GPT_ROOT}/rogii_trace_baseline_smoke/" 2>/dev/null || true
  cp "${MAIN}/_kaggle_env.sh" "${GPT_ROOT}/rogii_trace_baseline_smoke/" 2>/dev/null || true
  echo "synced episodic fix -> gpt rogii_trace_baseline_smoke"
fi

echo "Done. Regenerate notebooks in each worktree with: python embed_notebook.py"
