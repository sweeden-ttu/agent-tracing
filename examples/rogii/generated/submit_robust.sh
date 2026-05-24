#!/usr/bin/env bash
# Auto-generated from frontier.yaml — submit phases 01–06 for robust_scale_log1p.
<<<<<<< HEAD
# Worktree: agent-tracing-trace-robust
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-robust"
=======
# Worktree: agent-tracing
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
>>>>>>> 5b44f64 (Refresh cross-variant MLE plans, ablation tracking, and submit scripts)
export ROGII_ROOT="/lustre/work/sweeden/rogii"
export VARIANT="robust_scale_log1p"
export TRACE_VARIANT="robust_scale_log1p"
exec "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/submit_trace_pipeline.sh" "$@"
