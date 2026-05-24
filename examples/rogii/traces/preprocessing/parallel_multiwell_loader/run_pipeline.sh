#!/usr/bin/env bash
# Auto-generated from frontier.yaml — login-node dry-run gate for parallel_multiwell_loader.
set -euo pipefail
export ROGII_ROOT="/lustre/work/sweeden/agent-tracing-trace-parallel"
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-parallel"
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.trace_pipeline.orchestrator \
  --variant parallel_multiwell_loader \
  --trace-path "/lustre/work/sweeden/agent-tracing-trace-parallel/examples/rogii/traces/preprocessing/parallel_multiwell_loader/trace_language.csv" \
  --dry-run
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
