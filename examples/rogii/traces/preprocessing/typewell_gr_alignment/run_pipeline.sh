#!/usr/bin/env bash
# Auto-generated from frontier.yaml — login-node dry-run gate for typewell_gr_alignment.
set -euo pipefail
export ROGII_ROOT="/lustre/work/sweeden/agent-tracing"
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing"
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.trace_pipeline.orchestrator \
  --variant typewell_gr_alignment \
  --trace-path "/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/typewell_gr_alignment/trace_language.csv" \
  --dry-run
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
