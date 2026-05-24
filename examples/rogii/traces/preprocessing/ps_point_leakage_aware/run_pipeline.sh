#!/usr/bin/env bash
set -euo pipefail
source ~/.bash_profile 2>/dev/null || source ~/.profile 2>/dev/null
mamba activate kc-rogii-wellbore-geology-prediction 2>/dev/null || true
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.trace_pipeline.orchestrator --variant ps_point_leakage_aware --dry-run
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
