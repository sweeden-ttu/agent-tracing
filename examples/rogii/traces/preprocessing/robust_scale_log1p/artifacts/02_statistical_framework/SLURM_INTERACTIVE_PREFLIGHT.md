# Slurm interactive preflight (before episodic / long training)

Use TTU HPCC **`/etc/slurm/scripts/interactive`** on a **compute allocation** with the **same resources** as your `sbatch` script, then run everything **up to** `# LONG_RUNNING_START` and exit before the long train loop.

## What `interactive` does

The site script (`/etc/slurm/scripts/interactive`) is a wrapper around **`salloc`**:

| Flag | Meaning | Rogii `train_tcn*.slurm` |
|------|---------|---------------------------|
| **`-p`** | Partition (**required**) | `matador` |
| **`-c`** | CPU cores | `8` (`--cpus-per-task=8`) |
| **`-g`** | GPUs per node | `1` (`--gpus-per-node=1`) |
| **`-t`** | Wall time | `04:00:00` |
| **`-A`** | Account | `default` |
| **`-m`** | Memory **per CPU** | approximate `12500M` for `--mem=100G` / 8 CPUs |
| **`-J`** | Job name | optional |

Defaults if omitted: partition `nocona`, GPU partition default `matador`, time `12:00:00`.

**Important:** The live script ends with **`salloc` only** (the `srun --pty bash` line is commented out). After the allocation is granted, if you are still on the login node, run:

```bash
srun --pty bash -l
```

## One-line alias

```bash
alias interactive='/etc/slurm/scripts/interactive'
```

## Match `train_tcn_episodic.slurm` / `train_tcn.slurm`

From `/lustre/work/sweeden/rogii`:

```bash
bash hpcc/interactive_preflight_from_slurm.sh hpcc/train_tcn_episodic.slurm
# or launch directly:
bash hpcc/interactive_preflight_from_slurm.sh hpcc/train_tcn_episodic.slurm --run
```

Equivalent manual command:

```bash
interactive -c 8 -g 1 -p matador -t 04:00:00 -A default -m 12500M -J preflight_rogii_tcn_epi
```

## Preflight checklist (on the compute node)

```bash
cd /lustre/work/sweeden/rogii
export VARIANT=baseline_column_transformer

source hpcc/slurm_module_init.sh && init_slurm_modules
source hpcc/load_matador_modules.sh && load_matador_modules
source hpcc/_variant_conda_env.sh && matador_activate_variant_env
source hpcc/_matador_ollama_env.sh
matador_start_ollama_for_job
matador_export_ollama_base_url

nvidia-smi -L
curl -sf "${OLLAMA_BASE_URL}/api/tags" | head

# Smoke: imports only (no full training)
python - <<'PY'
import torch, lightgbm, sklearn
print("cuda", torch.cuda.is_available())
PY

# Optional: one short fold / tiny max_rows via phase_runner (login-style smoke)
# python -c "..."  # only if artifacts path is writable from rogii
```

**Stop before** the batch section marked `# LONG_RUNNING_START` (episodic `train_tcn.py` loop or full CV). Note setup time; set `#SBATCH -t` to setup + estimated train + ~20% buffer.

**Exit the session** when done (`exit` twice if needed) — do not leave GPU allocations idle.

## Consumer review + submit

```bash
cd /lustre/work/sweeden/rogii
export VARIANT=baseline_column_transformer
bash hpcc/review_slurm_before_submit.sh hpcc/train_tcn_episodic.slurm "${VARIANT}"
sbatch --export=ALL,VARIANT="${VARIANT}" hpcc/train_tcn_episodic.slurm
```

## Checkpoint / mid-resume gate

After episodic Slurm completes, before predict/submit resume:

- `sacct` → `COMPLETED` for `train_tcn_episodic.slurm`
- `artifacts/checkpoints/episode_manifest.json` and `fold_*.pkl` exist
- See `.cursor/rules/trace-language-mid-resume-slurm-gate.mdc`

## References

- `hpcc/review_slurm_before_submit.sh` — prints suggested `interactive` line from `#SBATCH`
- `.cursor/rules/slurm-ollama-consumer-review.mdc` — full consumer checklist
- `.cursor/rules/slurm-pipeline-execution.mdc` — one job per variant on Matador
