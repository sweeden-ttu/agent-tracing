# Papers library

Base scientific papers linked to each variant and ensemble layers for leaderboard blending.

## Locations

| Path | Content |
|------|---------|
| `examples/rogii/papers/{variant}/` | Variant primary PDFs |
| `examples/rogii/papers/layers/` | Ensemble / layer papers |
| `examples/rogii/papers/manifest.json` | Machine-readable index |
| `examples/rogii/BASE_PAPERS.md` | Full catalog with DOIs |

## Download scripts

```bash
# Variant primaries (7 entries including substitutes)
python examples/rogii/scripts/download_variant_papers.py
python examples/rogii/scripts/download_variant_papers.py --verify-only

# Leaderboard layer papers (17 primaries)
python examples/rogii/scripts/download_layer_papers.py --verify-only
```

## Variant → paper mapping

| Variant | Primary PDF | Substitute (if paywalled) |
|---------|-------------|---------------------------|
| baseline | Ke 2017 LightGBM, Pedregosa 2011 sklearn | — |
| typewell | Sakoe & Chiba 1978 DTW | — |
| ps | Kaufman et al. 2012 leakage | — |
| robust | Hampel 1986 robust stats | Pedregosa 2011 RobustScaler |
| parallel | Rocklin 2015 Dask | — |
| formation | Cover & Hart 1967 k-NN | Shepard 1968 (interpolation) |

## experiment_descriptor.json link

Each variant descriptor includes:

- `base_paper` / `base_papers[]` — structured metadata (claims, trace_tokens, DOI)
- `paper_file` — relative path to PDF under `examples/rogii/papers/`
- `trace_theory_paper` — PaperBench `agent-tracing` bundle reference

Written/refreshed by:

```bash
cd /lustre/work/sweeden/frontier-evals/project/paperbench
uv run python -m paperbench.scripts.write_experiment_descriptors --all-variants \
  --rogii-root /lustre/work/sweeden/agent-tracing-trace-baseline
```

## PaperBench bundle sync

```bash
uv run python -m paperbench.scripts.sync_rogii_papers
# → frontier-evals/project/paperbench/data/rogii/papers/
```

Resolved at runtime by `paperbench/trace_pipeline/paper_registry.py` (checks trace-baseline, agent-tracing, bundled data).

## Layer papers

See `papers/layers/README.md` for ensemble stack papers (TCN, attention, calibration, etc.) used in leaderboard ensemble work separate from the six trace variants.
