#!/usr/bin/env bash
# Auto-generated from frontier.yaml — submit phases 01–06 for typewell_gr_alignment.
<<<<<<< HEAD
# Worktree: agent-tracing-trace-typewell
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-typewell"
=======
# Worktree: agent-tracing
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
>>>>>>> 5b44f64 (Refresh cross-variant MLE plans, ablation tracking, and submit scripts)
export ROGII_ROOT="/lustre/work/sweeden/rogii"
export VARIANT="typewell_gr_alignment"
export TRACE_VARIANT="typewell_gr_alignment"
exec "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/submit_trace_pipeline.sh" "$@"
