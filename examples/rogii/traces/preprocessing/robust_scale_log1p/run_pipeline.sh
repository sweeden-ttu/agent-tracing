#!/usr/bin/env bash
# Auto-generated from frontier.yaml — login-node dry-run gate for robust_scale_log1p.
set -euo pipefail
export ROGII_ROOT="/lustre/work/sweeden/agent-tracing-trace-robust"
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-robust"
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.trace_pipeline.orchestrator \
  --variant robust_scale_log1p \
  --trace-path "/lustre/work/sweeden/agent-tracing-trace-robust/examples/rogii/traces/preprocessing/robust_scale_log1p/trace_language.csv" \
  --dry-run
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
