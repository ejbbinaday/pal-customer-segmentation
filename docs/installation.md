# Installation Reference — everything needed to run the model

**Verified:** 7 August 2026, against the project `.venv` (`pip list`) and `requirements-*.txt`.
**Python:** 3.14.2 in the working venv; wheels available for **3.11–3.14** (Docker image pins 3.11).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-pipeline.txt   # the model / pipeline
pip install -r requirements-dev.txt        # lint + security tooling (optional)
```

---

## 1. Core pipeline (`requirements-pipeline.txt` — pinned, all verified installed)

> ⚠️ Clustering output is **sensitive to `scikit-learn` / `hdbscan` versions** — keep these pinned.

### Numerics & ML

| Package | Version | Role in this project |
|---|---|---|
| `numpy` | 2.5.1 | array layer under everything |
| `pandas` | 3.0.3 | tabular wrangling, markdown report tables |
| `scikit-learn` | 1.9.0 | scaling, GMM/spectral/SVC benchmark models, metrics |
| `scipy` | 1.18.0 | stats + sparse ops backing sklearn/hdbscan |
| `hdbscan` | 0.8.44 | **the main clustering algorithm** (10-segment model) |
| `imbalanced-learn` | 0.14.2 | resampling for the rare-segment experiments |
| `joblib` | 1.5.3 | model persistence / parallelism (transitive, pinned) |
| `threadpoolctl` | 3.6.0 | BLAS thread control (transitive, pinned) |

### Large-data layer (38M-coupon extract)

| Package | Version | Role |
|---|---|---|
| `duckdb` | 1.5.5 | streams the 3.6 GB gz extract out-of-core; all EDA/feature SQL |
| `pyarrow` | 25.0.0 | Parquet backend for `data/interim/` and the Power BI export |
| `tabulate` | 0.10.0 | renders the profiler's markdown tables |

### Mixed-type clustering & sub-segmentation

| Package | Version | Role |
|---|---|---|
| `stepmix` | 3.0.0 | Latent Class Analysis — sub-types within large segments |
| `kmodes` | 0.12.2 | k-prototypes comparison (`cluster_diagnostic.py`, `kproto_compare.py`) |

### Topological data analysis (model benchmark / stress test)

| Package | Version | Role |
|---|---|---|
| `kmapper` | 2.1.0 | Mapper algorithm in the ten-method benchmark |
| `ripser` | 0.6.15 | persistent homology — "clusters vs continuum" check |
| `persim` | 0.3.8 | diagram utilities (ripser dependency) |

> Do **not** substitute `giotto-tda` — it has no Python 3.14 wheel and fails to build here.

### Plotting

| Package | Version | Role |
|---|---|---|
| `matplotlib` | 3.11.0 | all static figures (report + slides) |
| `seaborn` | 0.13.2 | statistical plot styling |

## 2. Dashboard only (`requirements.txt` — what Streamlit Cloud installs)

Floor-pinned (`>=`), **not installed in the local pipeline venv** — the dashboard runs on
Streamlit Cloud:

| Package | Constraint | Role |
|---|---|---|
| `streamlit` | >=1.29.0 | `src/dashboard.py` |
| `plotly` | >=5.18.0 | interactive dashboard charts |
| `pandas` / `numpy` | >=2.0.0 / >=1.24.0 | lean data layer for the dashboard |

## 3. Dev / CI tooling (`requirements-dev.txt` — not required at runtime)

| Package | Constraint | Installed | Role |
|---|---|---|---|
| `ruff` | >=0.8 | 0.15.22 | lint + format (pre-commit) |
| `bandit[toml]` | >=1.8 | 1.9.4 | security scan (pre-commit) |
| `pre-commit` | >=4.0 | — | hook runner (`pre-commit install`) |

## 4. Beyond requirements files (needed by specific scripts)

| Tool | Version here | Needed by | Install |
|---|---|---|---|
| `playwright` (py pkg) | 1.61.0 | `src/capture_slides.py` (slide PNGs) | pip; script auto-runs `playwright install chromium` |
| Chromium (playwright browser) | via playwright | `src/capture_slides.py` | `python -m playwright install chromium` |
| `Jinja2` | 3.1.6 | status-report templating | installed as a transitive dep |
| `pandoc` | 3.10 (Homebrew) | `docs/tuesday-punchlist.md` → `.docx` conversion | `brew install pandoc` |
| Docker | optional | reproducible env / handoff (image pins Python 3.11) | Docker Desktop |

## 5. Not code, but required inputs

- `data/PAL-data/*.txt.gz` — the 38M-coupon extract (4 files, ~3.6 GB; **not in git**).
- ~8 GB RAM headroom for the DuckDB stages (`SET memory_limit='8GB'` in the scripts).
- Disk for `data/interim/` Parquet (several GB) and `outputs/` artifacts (both git-ignored).

---

*If any pin changes, regenerate this file's tables from `pip list --format=freeze` and bump the
date at the top. Reproducibility of the clustering results depends on §1 staying pinned.*
