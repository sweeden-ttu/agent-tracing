#!/usr/bin/env bash
# Auto-generated from frontier.yaml — submit phases 01–06 for formation_plane_spatial.
<<<<<<< HEAD
# Worktree: agent-tracing-trace-formation
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-formation"
=======
# Worktree: agent-tracing
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
>>>>>>> 5b44f64 (Refresh cross-variant MLE plans, ablation tracking, and submit scripts)
export ROGII_ROOT="/lustre/work/sweeden/rogii"
export VARIANT="formation_plane_spatial"
export TRACE_VARIANT="formation_plane_spatial"
exec "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/submit_trace_pipeline.sh" "$@"
