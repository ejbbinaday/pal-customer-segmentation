# PAL Customer Segmentation

ML framework to auto-classify Philippine Airlines PNRs into actionable revenue segments.
Winning approach: **HDBSCAN** on penalty-weighted features → mapped to **10 named segments**
(see `docs/methodology.md` and `docs/knowledge-base.md`).

## Repository layout

```
data/raw/      Source datasets (not all tracked — see .gitignore)
                 sample-features.csv                  real Jan-2025 PAL snapshot (29,999 rows, 27 cols)
                 PAL_PNR_Synthetic_Data_1000-v3.csv   NEW PNR-level prototype data (1,000 rows, 41 cols)
                 PAL_PNR_Synthetic_Data_1000-v2.csv   data dictionary for the v3 schema
                 synthetic_flight_passenger_data.csv  generic synthetic set used by the POC
src/           All Python (analysis pipeline + report/slide generators + shared palette)
docs/          Business + methodology + EDA + monitoring docs, onboarding guide
reports/       Tracked deliverables: HTML EDA report, exported slide PNGs, POC figures
assets/        Presentation sources: kick-off deck (HTML/MD), pitch deck PDF
outputs/       Regenerable analysis artifacts (git-ignored; created by scripts in src/)
```

All scripts resolve paths relative to the repo root via `ROOT = Path(__file__).resolve().parents[1]`,
so they can be run from anywhere (e.g. `python src/hdbscan_final.py`).

## Core pipeline (runs on `data/raw/sample-features.csv`)

| Script | Purpose | Output |
|---|---|---|
| `src/eda_graphs.py`     | Dataset EDA + feature engineering | `outputs/eda_output/` |
| `src/eda_segments.py`   | Proxy-label waterfall + segment EDA | `outputs/eda_output/` |
| `src/cluster_initial.py`| KMeans k=10 baseline | `outputs/cluster_output/` |
| `src/cluster_compare.py`| 7-algorithm leaderboard | `outputs/cluster_compare_output/` |
| `src/dbscan_viz.py`     | DBSCAN deep-dive | `outputs/dbscan_output/` |
| `src/pca_boundaries.py` | Decision-boundary / PCA zoom | `outputs/boundary_output/` |
| `src/hdbscan_final.py`  | **Final model** (HDBSCAN → 10 segments) | `outputs/hdbscan_output/` |
| `src/resample_compare.py`| Resampling study (rejected) | `outputs/resample_output/` |
| `src/monitor_metrics.py`| Production monitoring (DBCV/PSI/ARI/drift) | `outputs/monitor_output/` |
| `src/pal_colors.py`     | Shared segment names + palette (imported everywhere) | — |

## Generators / deliverables

`src/generate_report.py` (HTML EDA report), `src/poc_synthetic.py` + `src/generate_dark_slides.py`
(POC figures), `src/capture_slides.py` (deck → PNGs), `src/dashboard.py` (Streamlit executive dashboard).

> **Streamlit Cloud:** the dashboard entrypoint is now `src/dashboard.py` — update the deployment config.

## v3 prototype (active track)

`src/features_v3.py` implements Stages **P1–P3** of the PNR-level prototype — clean → engineer →
proxy-label waterfall — on `data/raw/PAL_PNR_Synthetic_Data_1000-v3.csv` (see
`docs/methodology.md` §v3 Prototype Pipeline). It exposes `build()` (enriched frame) and
`build_matrix()` (unscaled model matrix), and profiles the features when run:

```bash
python src/features_v3.py     # P1–P3 → outputs/features_v3_output/
python src/prototype_v3.py    # P4–P5 → outputs/prototype_v3_output/
python src/diagnose_v3.py     # structure check (DBCV/ARI/silhouette) → outputs/diagnose_v3_output/
```

`src/prototype_v3.py` runs Stages **P4–P5** (improved): **hold-out split** → compact 24-feature matrix
(mixed-type scaling) → **unweighted** HDBSCAN discovery → inductive nearest-centroid labelling with an
**Unassigned bucket** → cost-matrix + DBCV validation on the **held-out** set. Penalties are used only in
the cost metric (not the feature space); negative learning (P3b) runs in `features_v3.build()`.

> **SME ground truth:** drop `data/labels/sme_sample.csv` (`Unique Identifier`,`true_segment`) and the
> script reports a **non-circular** hold-out recall automatically — see `data/labels/README.md`.

> **Known gap (v3 data):** OFW/Migrant, Pilgrimage, and Mabuhay Loyalist have no proxy seed in the
> v3 synthetic set, so they are not assignable in this prototype (see `docs/knowledge-base.md` §15).
>
> **Honest verdict:** diagnostics (negative DBCV, flat KMeans silhouette) show the v3 synthetic data has
> **no latent cluster structure** — this validates the *approach*, not a result, and the recall numbers
> are circular. Full analysis + recommendations: **`docs/v3-prototype-findings.md`**.

## Setup

Three dependency files, by purpose:

| File | Use |
|------|-----|
| `requirements.txt` | Lean, dashboard-only — what **Streamlit Cloud** installs |
| `requirements-pipeline.txt` | Full ML/EDA stack to run the `src/` scripts (pinned) |
| `requirements-dev.txt` | ruff · bandit · pre-commit |

```bash
pip install -r requirements-pipeline.txt   # run the pipeline
pip install -r requirements-dev.txt        # + tooling (optional)
```

Tested on Python 3.11–3.14. Clustering output is sensitive to `scikit-learn`/`hdbscan`
versions — keep `requirements-pipeline.txt` pinned.

## Docker (optional — reproducible environment)

Python is pinned to 3.11 in the image, so it builds identically regardless of the host.

```bash
docker build -t pal-segmentation .

# Dashboard (default CMD) → http://localhost:8501
docker run --rm -p 8501:8501 pal-segmentation

# Run a pipeline script, writing figures back to the host
docker run --rm -v "$PWD/outputs:/app/outputs" pal-segmentation python src/hdbscan_final.py
```

Not required for day-to-day prototyping (use the venv above); most useful for guaranteed
reproducibility or an eventual production/PAL handoff.

## Code quality (ruff · bandit · pre-commit)

Dev tooling is configured in `pyproject.toml` (`[tool.ruff]`, `[tool.bandit]`) and
`.pre-commit-config.yaml`. Enable it once:

```bash
pip install -r requirements-dev.txt
pre-commit install                 # run hooks automatically on every git commit
```

Useful commands:

```bash
pre-commit run --all-files         # run every hook across the whole repo
ruff check src/                    # lint
ruff check --fix src/              # lint + auto-fix
ruff format src/                   # format
bandit -c pyproject.toml -r src/   # security scan
pre-commit autoupdate              # bump pinned hook versions
```

Hooks: `ruff` (lint, `--fix`) + `ruff-format`, `bandit` (security), plus whitespace/EOF/YAML/TOML/
large-file checks. `outputs/`, `reports/`, `assets/`, and `scratchpad/` are excluded from linting.
