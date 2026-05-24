#!/usr/bin/env bash
# Auto-generated from frontier.yaml — login-node dry-run gate for formation_plane_spatial.
set -euo pipefail
export ROGII_ROOT="/lustre/work/sweeden/agent-tracing-trace-formation"
export AGENT_TRACING_ROOT="/lustre/work/sweeden/agent-tracing-trace-formation"
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.trace_pipeline.orchestrator \
  --variant formation_plane_spatial \
  --trace-path "/lustre/work/sweeden/agent-tracing-trace-formation/examples/rogii/traces/preprocessing/formation_plane_spatial/trace_language.csv" \
  --dry-run
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
