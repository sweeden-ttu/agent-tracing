#!/usr/bin/env bash
# Auto-generated from frontier.yaml — submit phases 01–06 for parallel_multiwell_loader.
<<<<<<< HEAD
# Worktree: agent-tracing-trace-parallel
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-parallel"
=======
# Worktree: agent-tracing
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
>>>>>>> 5b44f64 (Refresh cross-variant MLE plans, ablation tracking, and submit scripts)
export ROGII_ROOT="/lustre/work/sweeden/rogii"
export VARIANT="parallel_multiwell_loader"
export TRACE_VARIANT="parallel_multiwell_loader"
exec "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/submit_trace_pipeline.sh" "$@"
