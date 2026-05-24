#!/usr/bin/env bash
# Auto-generated from frontier.yaml — login-node dry-run gate for ps_point_leakage_aware.
set -euo pipefail
export ROGII_ROOT="/lustre/work/sweeden/agent-tracing-trace-ps"
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-ps"
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.trace_pipeline.orchestrator \
  --variant ps_point_leakage_aware \
  --trace-path "/lustre/work/sweeden/agent-tracing-trace-ps/examples/rogii/traces/preprocessing/ps_point_leakage_aware/trace_language.csv" \
  --dry-run
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
