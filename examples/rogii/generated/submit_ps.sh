#!/usr/bin/env bash
# Auto-generated from frontier.yaml — submit phases 01–06 for ps_point_leakage_aware.
# Worktree: agent-tracing
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
export ROGII_ROOT="/lustre/work/sweeden/rogii"
export VARIANT="ps_point_leakage_aware"
export TRACE_VARIANT="ps_point_leakage_aware"
exec "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/submit_trace_pipeline.sh" "$@"
