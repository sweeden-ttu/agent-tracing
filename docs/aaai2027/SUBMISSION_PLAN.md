# AAAI 2027 Submission Plan
## Trace Language Framework for Agent Verification and Validation

**Target Conference:** AAAI Conference on Artificial Intelligence 2027  
**Paper Title:** A Trace-Language Theory of Agents: Goal-Driven Type-0 Producers Bounded by Data-Driven Type-3 Consumers  
**Authors:** Scott Weeden, Ms. of Computer Applications, Texas Tech University  
**Submission Deadline:** September 2026 (Exact date to be confirmed from AAAI 2027 website)  
**Notification Date:** December 2026  
**Conference Dates:** February 2027  

## 0. This ablation / branch (variant worktree)

| Field | Path or value |
|-------|----------------|
| **Worktree (this checkout)** | `/lustre/work/sweeden/agent-tracing-trace-formation` |
| **Unified repo (canonical traces)** | `/lustre/work/sweeden/agent-tracing` |
| **Git branch** | `trace/formation-plane-spatial` |
| **GitHub PR** | [#22](https://github.com/sweeden-ttu/agent-tracing/pull/22) · Issue [#15](https://github.com/sweeden-ttu/agent-tracing/issues/15) |
| **Variant slug** | `formation_plane_spatial` |
| **Approach** | Drilling geometry + formation KNN |
| **Base paper(s)** | Cover & Hart 1967 k-NN (formation-plane spatial features) |
| **Trace language CSV (canonical)** | `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/trace_language.csv` |
| **Trace bundle (this worktree)** | `/lustre/work/sweeden/agent-tracing-trace-formation/examples/rogii/traces/preprocessing/formation_plane_spatial/` |
| **Experiment descriptor** | `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/experiment_descriptor.json` |
| **Ablation plan** | `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/ablation_plan.json` |
| **Conda env (`environment.yml`)** | `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/environment.yml` (env name = `formation_plane_spatial`) |
| **HPCC ablation runs** | `/lustre/work/sweeden/rogii/ablation_runs/formation_plane_spatial/` |
| **HPCC pipeline / Slurm** | `/lustre/work/sweeden/rogii/hpcc/` (`run_ablation_variant.slurm`, `train_tcn_episodic.slurm`, `train_tcn.slurm`) |
| **Kaggle competition** | [rogii-wellbore-geology-prediction](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction) |
| **Trace-theory paper sections** | sec/3 Type-0 envelope |
| **Merge order** | See `/lustre/work/sweeden/agent-tracing/examples/rogii/MERGE_PATH.md` (baseline merges first) |

Submit Slurm jobs for **this variant only** (one active job per branch):

```bash
cd /lustre/work/sweeden/rogii
VARIANT=formation_plane_spatial bash hpcc/review_slurm_before_submit.sh hpcc/run_ablation_variant.slurm formation_plane_spatial
VARIANT=formation_plane_spatial sbatch hpcc/run_ablation_variant.slurm
```

Mid-trace resume: follow `/lustre/work/sweeden/agent-tracing/.cursor/rules/trace-language-mid-resume-slurm-gate.mdc` — prior `sbatch` steps must be `COMPLETED` and `ablation_runs/formation_plane_spatial/` artifacts must match the resume row in `trace_language.csv`.


## 1. Paper Overview

This submission presents a novel theoretical framework for agent verification and validation based on trace languages and the Chomsky hierarchy. The core contribution is establishing that agent behaviors can be formally specified as trace languages, enabling automated verification through Chomsky hierarchy classification.

### Key Contributions:
1. **Trace Language Specification**: Formal definition of agent behaviors as trace languages in CSV format
2. **Chomsky Hierarchy Classification**: Method for classifying agents into Type-0 through Type-3 based on their trace language properties
3. **Verification Framework**: Implementation of a verification system that checks agent behaviors against trace language specifications
4. **Recursively Enumerable Quality Rubric**: Novel evaluation framework with semi-decidable properties for assessing trace language quality
5. **Empirical Validation**: Application to ROGII Wellbore Geology Prediction competition and PaperBench dataset

## 2. Timeline for Completion (Now Until September 2026)

### Phase 1: Foundation Completion (May - June 2026)
- [x] Complete trace language framework for `formation_plane_spatial` in `/lustre/work/sweeden/agent-tracing-trace-formation` (branch `trace/formation-plane-spatial`)
- [x] Add research paper to PaperBench dataset as "a-trace-language-theory-of-agents"
- [x] Implement Chomsky classifier, validator, recorder, and rubric components
- [x] Create trace language specification: `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/trace_language.csv`

### Phase 2: Empirical Validation (July - August 2026)
- [ ] Run Rogii ablation baseline cells for `formation_plane_spatial` via `/lustre/work/sweeden/rogii/hpcc/run_ablation_variant.slurm`
- [ ] Run full Slurm pipeline (`train_tcn_episodic.slurm` → checkpoints → submit) per `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/trace_language.csv`
- [ ] Measure improvements in security, task breakdown, and competition performance
- [ ] Validate recursively enumerable properties of quality rubric
- [ ] Compare `formation_plane_spatial` RMSE (post-PS) against other five variants under `examples/rogii/ablation_tracking_status.csv`

### Phase 3: Paper Writing and Refinement (September 2026)
- [ ] Write full paper following AAAI format guidelines
- [ ] Incorporate experimental results and theoretical contributions
- [ ] Prepare figures, tables, and supplementary materials
- [ ] Conduct internal review and revisions
- [ ] Finalize submission package

## 3. AAAI 2027 Submission Requirements

Based on typical AAAI requirements (verify exact requirements from aaai.org/conference/aaai/aaai-27/):

### Paper Format:
- Maximum 9 pages (including references) for main submission
- Optional unlimited pages for appendices
- PDF format required
- AAAI style template must be used
- Anonymous submission for review (remove author information)

### Required Sections:
1. Abstract (150-250 words)
2. Introduction
3. Related Work
4. Technical Approach
5. Experimental Evaluation
6. Results and Discussion
7. Conclusion
8. References
9. Appendices (optional)

### Evaluation Criteria:
- Originality and significance of contributions
- Technical correctness and completeness
- Clarity of presentation
- Empirical validation and results
- Relation to existing work

## 4. Research Plan Integration

### Connection to PaperBench:
Our trace language framework has been integrated into the PaperBench dataset as a new research topic:
- **Location**: `/lustre/work/sweeden/frontier-evals/project/paperbench/data/papers/agent-tracing/` (PaperBench bundle)
- **Variant trace orchestrator**: `paperbench.trace_pipeline.orchestrator --variant formation_plane_spatial`
- **Components**:
  - config.yaml: Paper identification and title
  - addendum.md: Brief description of contributions
  - paper.md: Full paper content (from llm.txt)
  - rubric.json: Trace language verification requirements with hierarchical subtasks

### Experimental Validation Plan:
1. **Variant trace CSV**: Execute swim lanes in `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/trace_language.csv` under Type-3 consumer bounds
2. **Ablation factorial**: Grid from `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/ablation_plan.json`; manifests in `/lustre/work/sweeden/rogii/ablation_runs/formation_plane_spatial/`
3. **Comparison Metrics**:
   - Competition performance (RMSE for ROGII)
   - Trace language validation pass/fail rates
   - Security violation detection (unauthorized actions)
   - Task breakdown clarity (phase transition accuracy)
   - Resource utilization efficiency

## 5. HPCC Execution Environment

For running experiments on HPCC cluster to generate results for the paper:

### Software Environment:
- Miniforge virtual environment with Python 3.10
- Required packages: numpy, pandas, scikit-learn, xgboost, lightgbm, tensorflow, torch, kaggle, mlflow
- Ollama with granite4:3b for LLM backbone

### SLURM Job Template:
```bash
#!/bin/bash
#SBATCH --job-name=rogii_formation_plane_spat
#SBATCH --partition=matador
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=6000
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --output=/lustre/work/sweeden/rogii/logs/%x.o%j
#SBATCH --error=/lustre/work/sweeden/rogii/logs/%x.e%j

# Environment setup
module purge
source "${RUN_DIR}/hpcc/slurm_module_init.sh"
init_slurm_modules
source "${RUN_DIR}/hpcc/load_matador_modules.sh"
load_matador_modules

VARIANT=formation_plane_spatial
source "${RUN_DIR}/hpcc/_variant_conda_env.sh"
matador_activate_variant_env

# Experiment execution
RUN_DIR=/lustre/work/sweeden/rogii
cd "${RUN_DIR}"
VARIANT=formation_plane_spatial bash hpcc/review_slurm_before_submit.sh hpcc/run_ablation_variant.slurm formation_plane_spatial
VARIANT=formation_plane_spatial sbatch hpcc/run_ablation_variant.slurm
# Full train (after ablation bootstrap completes):
# sbatch hpcc/train_tcn_episodic.slurm
# Artifacts: ablation_runs/formation_plane_spatial/  artifacts/checkpoints/  submission.csv
```

### Directory Structure on HPCC:
- **Theory + trace CSVs (canonical):** `/lustre/work/sweeden/agent-tracing/`
- **This variant worktree:** `/lustre/work/sweeden/agent-tracing-trace-formation/`
- **Trace bundle:** `/lustre/work/sweeden/agent-tracing/examples/rogii/traces/preprocessing/formation_plane_spatial/`
- **HPCC pipeline + data:** `/lustre/work/sweeden/rogii/` (`data/`, `artifacts/`, `logs/`)
- **Ablation manifests:** `/lustre/work/sweeden/rogii/ablation_runs/formation_plane_spatial/`

## 6. Supplementary Materials for Submission

### Code Repository:
- Main implementation: https://github.com/sweeden-ttu/agent-tracing
- PaperBench integration: frontier-evals repository with added paper
- Experimental results and logs: Available upon request

### Data Availability:
- ROGII Wellbore Geology Prediction dataset: Available through Kaggle
- PaperBench dataset: Available through frontier-evals repository
- Experimental results: Generated during HPCC execution

### Reproducibility:
- All experiments documented with exact command lines
- Environment specifications provided via conda environment.yml
- Random seeds fixed for stochastic components
- HPCC job scripts included for exact replication

## 7. Related Work Positioning

Our work connects to and extends several areas:
- **Agent Verification**: Building on AgentEval, AutoGen evaluation frameworks
- **Formal Methods**: Applying Chomsky hierarchy to agent behaviors
- **Trace Analysis**: Extending software execution trace analysis to AI agents
- **Hierarchical Classification**: Using formal language theory for agent capability assessment

### Key Differentiators:
- First to apply Chomsky hierarchy classification to agent trace languages
- Novel trace language specification format for agent behaviors
- Recursively enumerable quality rubric with semi-decidable properties
- Integration with Rogii Kaggle benchmark and PaperBench agent-tracing bundle
- Practical verification framework with executable components

## 8. Broader Impacts

This work contributes to:
- **AI Safety**: Provides formal methods for verifying agent behaviors
- **Trustworthy AI**: Enables transparent assessment of agent capabilities
- **Reproducible Research**: Standardizes agent evaluation through formal specifications
- **Industry Applications**: Applicable to AI agent development in enterprise settings
- **Theoretical Advancement**: Bridges formal language theory and AI agent research

## 9. Final Checklist Before Submission

### By September 2026:
- [ ] All experimental results collected and analyzed
- [ ] Paper written in AAAI format (9 pages max)
- [ ] Anonymous version prepared for review
- [ ] Supplementary materials organized
- [ ] Code repository tagged with release version
- [ ] Environment documentation completed
- [ ] Submission package assembled and verified

### Submission Process:
1. Verify exact deadline from AAAI 2027 website
2. Prepare anonymous PDF submission
3. Submit through AAAI EasyChair portal
4. Prepare for potential rebuttal period (if applicable)
5. Prepare camera-ready version if accepted

## Conclusion

This plan outlines a comprehensive path to submitting our trace language framework for agent verification to AAAI 2027. By leveraging our implementation in the agent-tracing repository, integration with PaperBench, and planned experimental validation on HPCC resources, we aim to make a significant contribution to the field of AI agent verification and validation.

The theoretical foundation, practical implementation, and empirical results combine to create a strong submission that advances both the theoretical understanding of agent behaviors and provides practical tools for ensuring AI agent safety and reliability.
