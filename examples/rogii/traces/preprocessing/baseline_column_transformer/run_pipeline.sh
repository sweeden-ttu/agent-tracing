#!/usr/bin/env bash
# Auto-generated from frontier.yaml — login-node dry-run gate for baseline_column_transformer.
set -euo pipefail
export ROGII_ROOT="/lustre/work/sweeden/agent-tracing"
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.trace_pipeline.orchestrator \
  --variant baseline_column_transformer \
  --trace-path "/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/baseline_column_transformer/trace_language.csv" \
  --dry-run
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
