#!/usr/bin/env python3
"""Build Kaggle notebooks from pipeline Python modules (self-contained embed bundles)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Full pipeline bundle (composer winner + shared pipeline/)
FULL_FILES = [
    "run_kaggle_pipeline.py",
    "run_baseline.py",
    "run_episodic_kaggle.py",
    "train_predict.py",
    "pipeline/__init__.py",
    "pipeline/competition_data.py",
    "pipeline/cv_orchestrator.py",
    "pipeline/nb_support.py",
    "pipeline/preprocessor.py",
    "pipeline/target_diagnostician.py",
    "pipeline/well_group_detector.py",
    "pipeline/temporal_cnn.py",
    "pipeline/episodic_benchmark.py",
    "pipeline/ensemble_blend.py",
]

# Largest modules → standalone exploration notebooks (BoN merge: opus tabular + composer episodic)
LARGE_MODULE_NOTEBOOKS: list[tuple[str, str, str | None]] = [
    (
        "train_predict.py",
        "rogii_module_train_predict.ipynb",
        "Tabular CV helpers (`cross_val_and_predict`, LightGBM/HGBR).",
    ),
    (
        "run_baseline_strong.py",
        "rogii_module_run_baseline_strong.ipynb",
        "Strong tabular pipeline (physics + raw LightGBM, Ridge/coordinate-descent blend).",
    ),
    (
        "run_episodic_kaggle.py",
        "rogii_module_run_episodic.ipynb",
        "Episodic TCN with global target z-score (composer fix).",
    ),
    (
        "run_kaggle_pipeline.py",
        "rogii_module_run_kaggle_pipeline.ipynb",
        "Orchestrator: baseline → 12 ft gate → episodic → blend → submit.",
    ),
    (
        "pipeline/temporal_cnn.py",
        "rogii_module_temporal_cnn.ipynb",
        "Dilated 1D-CNN backbone for episodic training.",
    ),
]

TABULAR_FILES = ["run_baseline_strong.py"]

KERNEL_META = {
    "language": "python",
    "kernel_type": "notebook",
    "is_private": "true",
    "enable_gpu": "true",
    "enable_internet": "true",
    "competition_sources": ["rogii-wellbore-geology-prediction"],
    "dataset_sources": ["scottweeden/rogii-synthetic-trace-smoke-data"],
    "kernel_sources": [],
}


def _read_bundle(rels: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in rels:
        p = ROOT / rel
        if not p.is_file():
            raise FileNotFoundError(p)
        out[rel] = p.read_text(encoding="utf-8")
    return out


def _md(lines: list[str]) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": lines}


def _code(lines: list[str], cell_id: str = "") -> dict:
    c: dict = {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": lines,
    }
    if cell_id:
        c["id"] = cell_id
    return c


def _write_bundle_cell(payload: dict[str, str]) -> dict:
    blob = json.dumps(json.dumps(payload))
    return _code(
        [
            "from pathlib import Path\n",
            "import json\n",
            "ROOT = Path.cwd()\n",
            f"payload = json.loads({blob})\n",
            "for rel, content in payload.items():\n",
            "    p = ROOT / rel\n",
            "    p.parent.mkdir(parents=True, exist_ok=True)\n",
            "    p.write_text(content, encoding='utf-8')\n",
            "print('wrote', len(payload), 'files under', ROOT)\n",
        ],
        "write-files",
    )


def _resolve_data_dir_snippet() -> list[str]:
    return [
        "from pathlib import Path\n",
        "def resolve_data_dir():\n",
        "    for p in (\n",
        "        Path('/kaggle/input/rogii-wellbore-geology-prediction'),\n",
        "        Path('/kaggle/input/rogii-synthetic-trace-smoke-data'),\n",
        "        Path('/lustre/work/sweeden/rogii/data'),\n",
        "        Path('data'),\n",
        "    ):\n",
        "        if (p / 'sample_submission.csv').is_file():\n",
        "            return p\n",
        "    raise FileNotFoundError('No competition data (sample_submission.csv)')\n",
        "DATA_DIR = resolve_data_dir()\n",
        "print('DATA_DIR', DATA_DIR)\n",
    ]


def _kaggle_submit_snippet(submission_name: str = "submission.csv") -> list[str]:
    return [
        "from pathlib import Path\n",
        "import json\n",
        "sub_path = Path('/kaggle/working') / '" + submission_name + "'\n",
        "if not sub_path.is_file():\n",
        "    sub_path = Path('output') / '" + submission_name + "'\n",
        "submit_info = {'submitted': False}\n",
        "if sub_path.is_file() and Path('/kaggle/working').is_dir():\n",
        "    try:\n",
        "        from kaggle.api.kaggle_api_extended import KaggleApi\n",
        "        api = KaggleApi()\n",
        "        api.authenticate()\n",
        "        api.competition_submit(\n",
        "            str(sub_path),\n",
        "            'rogii trace tabular strong (BoN merge)',\n",
        "            'rogii-wellbore-geology-prediction',\n",
        "        )\n",
        "        submit_info = {'submitted': True, 'path': str(sub_path)}\n",
        "        print('Kaggle submit OK')\n",
        "    except Exception as exc:\n",
        "        submit_info = {'submitted': False, 'error': str(exc)}\n",
        "        print('Kaggle submit skipped:', exc)\n",
        "else:\n",
        "    import os, shutil, subprocess\n",
        "    if sub_path.is_file() and shutil.which('kaggle'):\n",
        "        r = subprocess.run([\n",
        "            'kaggle', 'competitions', 'submit',\n",
        "            '-c', 'rogii-wellbore-geology-prediction',\n",
        "            '-f', str(sub_path), '-m', 'rogii tabular strong local',\n",
        "        ], capture_output=True, text=True)\n",
        "        submit_info = {'submitted': r.returncode == 0, 'stdout': r.stdout, 'stderr': r.stderr}\n",
        "print(json.dumps(submit_info, indent=2))\n",
    ]


def _notebook(cells: list[dict]) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }


def _save(nb: dict, path: Path) -> None:
    path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size / 1024:.1f} KiB)")


def build_full_pipeline_notebook() -> Path:
    payload = _read_bundle(FULL_FILES)
    cells = [
        _md(
            [
                "# ROGII full pipeline (tabular + episodic gate)\n",
                "\n",
                "Merged from **composer** (episodic z-score fix, blend) + shared `pipeline/` bundle.\n",
                "\n",
                "1. Tabular GroupKFold baseline\n",
                "2. If CV RMSE ≥ 12 ft → episodic TCN\n",
                "3. Inverse-RMSE blend + optional refine\n",
                "4. Competition submit\n",
            ]
        ),
        _write_bundle_cell(payload),
        _code(_resolve_data_dir_snippet(), "data-dir"),
        _code(
            [
                "from pathlib import Path\n",
                "import json, sys\n",
                "BUNDLE = Path.cwd().resolve()\n",
                "sys.path.insert(0, str(BUNDLE))\n",
                "from run_kaggle_pipeline import run_pipeline\n",
                "work_dir = Path('/kaggle/working') if Path('/kaggle/working').is_dir() else Path('output')\n",
                "work_dir.mkdir(parents=True, exist_ok=True)\n",
                "metrics = run_pipeline(\n",
                "    DATA_DIR, work_dir,\n",
                "    rmse_threshold=12.0,\n",
                "    submit=False,\n",
                "    episodic_episodes=2,\n",
                "    episodic_epochs=30,\n",
                ")\n",
                "print(json.dumps({k: metrics[k] for k in sorted(metrics) if k != 'fold_rmses'}, indent=2))\n",
            ],
            "run-pipeline",
        ),
        _code(_kaggle_submit_snippet("submission.csv"), "submit"),
    ]
    out = ROOT / "rogii_trace_baseline_smoke.ipynb"
    _save(_notebook(cells), out)
    return out


def build_tabular_submit_notebook() -> Path:
    payload = _read_bundle(TABULAR_FILES)
    cells = [
        _md(
            [
                "# ROGII competition submit — strong tabular only\n",
                "\n",
                "Merged from **opus** BoN run: dual LightGBM agents (`lgb_physics`, `lgb_baseline`), "
                "Ridge + coordinate-descent ensemble, Savgol smoothing.\n",
                "\n",
                "**Primary kernel for competition submission** (fast, no GPU required for tabular).\n",
            ]
        ),
        _write_bundle_cell(payload),
        _code(_resolve_data_dir_snippet(), "data-dir"),
        _code(
            [
                "from pathlib import Path\n",
                "import json, subprocess, sys\n",
                "out_dir = Path('/kaggle/working') if Path('/kaggle/working').is_dir() else Path('output')\n",
                "out_dir.mkdir(parents=True, exist_ok=True)\n",
                "cmd = [\n",
                "    sys.executable, 'run_baseline_strong.py',\n",
                "    '--data-dir', str(DATA_DIR),\n",
                "    '--out-dir', str(out_dir),\n",
                "    '--skip-tcn',\n",
                "]\n",
                "print(' '.join(cmd))\n",
                "subprocess.run(cmd, check=True)\n",
                "metrics = json.loads((out_dir / 'pipeline_metrics.json').read_text())\n",
                "print(\n",
                "    f\"cv_rmse={metrics['cv_rmse']:.4f}  \"\n",
                "    f\"cumulative_rmse_feet={metrics['cumulative_rmse_feet']:.4f}\"\n",
                ")\n",
            ],
            "run-tabular",
        ),
        _code(_kaggle_submit_snippet("submission.csv"), "submit"),
    ]
    out = ROOT / "rogii_trace_tabular_submit.ipynb"
    _save(_notebook(cells), out)
    return out


def build_compiled_single_notebook() -> Path:
    """One notebook with a section per largest module (read + optional smoke run)."""
    section_files = [rel for rel, _, _ in LARGE_MODULE_NOTEBOOKS]
    payload = _read_bundle(section_files + FULL_FILES)
    cells: list[dict] = [
        _md(
            [
                "# ROGII compiled pipeline — all major modules\n",
                "\n",
                "Single notebook embedding the five largest Python modules plus the full "
                "`pipeline/` support bundle. Runs the **strong tabular** path then optional "
                "**full orchestrator** (episodic gate).\n",
            ]
        ),
        _write_bundle_cell(payload),
        _code(_resolve_data_dir_snippet(), "data-dir"),
    ]
    for rel, _, blurb in LARGE_MODULE_NOTEBOOKS:
        mod_name = Path(rel).stem
        cells.append(_md([f"## `{rel}`\n", f"\n{blurb}\n"]))
        cells.append(
            _code(
                [
                    f"import importlib.util\n",
                    f"from pathlib import Path\n",
                    f"p = Path('{rel}')\n",
                    f"print(p.read_text()[:800], '... ({p.stat().st_size} bytes total)')\n",
                ],
                f"peek-{mod_name}",
            )
        )
    cells.append(
        _md(
            [
                "## Run strong tabular + metrics\n",
                "\n",
                "Uses `run_baseline_strong.py` (opus) for competition-grade tabular CV.\n",
            ]
        )
    )
    cells.append(
        _code(
            [
                "from pathlib import Path\n",
                "import json, subprocess, sys\n",
                "out_dir = Path('/kaggle/working') if Path('/kaggle/working').is_dir() else Path('output')\n",
                "out_dir.mkdir(parents=True, exist_ok=True)\n",
                "subprocess.run([\n",
                "    sys.executable, 'run_baseline_strong.py',\n",
                "    '--data-dir', str(DATA_DIR), '--out-dir', str(out_dir), '--skip-tcn',\n",
                "], check=True)\n",
                "tabular = json.loads((out_dir / 'pipeline_metrics.json').read_text())\n",
                "print('tabular', {k: tabular[k] for k in ('cv_rmse', 'cumulative_rmse_feet', 'ensemble_method')})\n",
            ],
            "run-tabular",
        )
    )
    cells.append(
        _md(
            [
                "## Run full orchestrator (optional episodic)\n",
                "\n",
                "Set `RUN_EPISODIC=False` on Kaggle CPU smoke; enable on GPU for gate path.\n",
            ]
        )
    )
    cells.append(
        _code(
            [
                "from pathlib import Path\n",
                "import json, sys\n",
                "RUN_EPISODIC = Path('/kaggle/working').is_dir()  # GPU kernel\n",
                "sys.path.insert(0, str(Path.cwd()))\n",
                "from run_kaggle_pipeline import run_pipeline\n",
                "full_dir = Path('/kaggle/working/full') if Path('/kaggle/working').is_dir() else Path('output/full')\n",
                "full_dir.mkdir(parents=True, exist_ok=True)\n",
                "if RUN_EPISODIC:\n",
                "    full = run_pipeline(DATA_DIR, full_dir, rmse_threshold=12.0, submit=False,\n",
                "                        episodic_episodes=2, episodic_epochs=30)\n",
                "    print('full', full.get('cv_rmse'), full.get('cumulative_rmse_feet'),\n",
                "          full.get('episodic_triggered'))\n",
                "else:\n",
                "    print('Skipping full episodic orchestrator (set RUN_EPISODIC=True on GPU)')\n",
            ],
            "run-full",
        )
    )
    cells.append(_code(_kaggle_submit_snippet("submission.csv"), "submit"))
    out = ROOT / "rogii_trace_compiled_submit.ipynb"
    _save(_notebook(cells), out)
    return out


def build_module_notebooks() -> list[Path]:
    written: list[Path] = []
    for rel, nb_name, blurb in LARGE_MODULE_NOTEBOOKS:
        payload = {rel: (ROOT / rel).read_text(encoding="utf-8")}
        cells = [
            _md([f"# Module: `{rel}`\n", f"\n{blurb}\n"]),
            _write_bundle_cell(payload),
            _code(
                [
                    f"from pathlib import Path\n",
                    f"p = Path('{rel}')\n",
                    f"print('Loaded', p, '—', p.stat().st_size, 'bytes')\n",
                ],
                "loaded",
            ),
        ]
        if rel == "run_baseline_strong.py":
            cells.append(_code(_resolve_data_dir_snippet(), "data-dir"))
            cells.append(
                _code(
                    [
                        "import subprocess, sys\n",
                        "from pathlib import Path\n",
                        "out = Path('output'); out.mkdir(exist_ok=True)\n",
                        "subprocess.run([sys.executable, 'run_baseline_strong.py',\n",
                        "    '--data-dir', str(DATA_DIR), '--out-dir', str(out), '--skip-tcn'], check=True)\n",
                    ],
                    "smoke-run",
                )
            )
        out = ROOT / nb_name
        _save(_notebook(cells), out)
        written.append(out)
    return written


def write_kernel_metadata() -> None:
  entries = [
      (
          "rogii_trace_tabular_submit.ipynb",
          {
              "id": "scottweeden/rogii-trace-tabular-submit",
              "title": "ROGII Trace Tabular Submit",
              "code_file": "rogii_trace_tabular_submit.ipynb",
          },
      ),
      (
          "rogii_trace_compiled_submit.ipynb",
          {
              "id": "scottweeden/rogii-trace-compiled-submit",
              "title": "ROGII Trace Compiled Submit",
              "code_file": "rogii_trace_compiled_submit.ipynb",
          },
      ),
      (
          "rogii_trace_baseline_smoke.ipynb",
          {
              "id": "scottweeden/rogii-trace-baseline-smoke",
              "title": "ROGII Trace Full Pipeline",
              "code_file": "rogii_trace_baseline_smoke.ipynb",
          },
      ),
  ]
  for _, extra in entries:
      meta = {**KERNEL_META, **extra}
      path = ROOT / f"kernel-metadata-{extra['code_file'].replace('.ipynb', '')}.json"
      path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
      print("wrote", path)
  # Default push target = tabular submit
  default = {**KERNEL_META, **entries[0][1]}
  (ROOT / "kernel-metadata.json").write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")
  print("wrote", ROOT / "kernel-metadata.json", "(default → tabular submit)")


def main() -> None:
    build_full_pipeline_notebook()
    build_tabular_submit_notebook()
    build_compiled_single_notebook()
    build_module_notebooks()
    write_kernel_metadata()


if __name__ == "__main__":
    main()
