#!/usr/bin/env bash
# Auto-generated from frontier.yaml — submit phases 01–06 for baseline_column_transformer.
# Worktree: agent-tracing
set -euo pipefail
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
export ROGII_ROOT="/lustre/work/sweeden/rogii"
export VARIANT="baseline_column_transformer"
export TRACE_VARIANT="baseline_column_transformer"
exec "${AGENT_TRACING_ROOT}/examples/rogii/hpcc/submit_trace_pipeline.sh" "$@"
