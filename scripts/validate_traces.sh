#!/usr/bin/env bash
# Validate trace_language.csv on this branch (single variant or all under preprocessing/).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FE="${FRONTIER_EVALS_ROOT:-/lustre/work/sweeden/frontier-evals/project/paperbench}"
if [[ ! -d "$FE" ]]; then
  echo "Set FRONTIER_EVALS_ROOT to paperbench checkout" >&2
  exit 1
fi
export ROGII_ROOT="$ROOT/examples/rogii"
cd "$FE"
uv run python -m paperbench.scripts.implement_agent_tracing --validate-traces
