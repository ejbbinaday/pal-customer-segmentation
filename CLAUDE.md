# CLAUDE.md — PAL Customer Segmentation

## Knowledge base is the single source of truth — keep it live

`docs/knowledge-base.md` is a **living document**. Its **§15 Learning Log** is the append-only
working memory of the project.

**Whenever we learn something new** about the airline industry, clustering, customer segmentation,
our data, or a project decision — during any session — **append it to §15 before finishing the turn.**

- Format each entry: `#### YYYY-MM-DD — Title`, a **Domain** tag
  (`Airline Industry` · `Clustering / Methodology` · `Data & Features` · `Project Decision`),
  the learning, and a **Source** (paper/URL, script, dataset, or "our analysis"). Newest first.
- If a new learning supersedes a curated fact in §§1–14, update that section too and note it.
- Bump the footer `Last updated` date on every change.
- Sections 1–14 stay deliverable-grade and stable; put evolving/working knowledge in §15.

## Project orientation (see README.md for the full layout)

- Approach: **anonymous trip-purpose × value segmentation** at the PNR level (Sabre's anonymous lens) —
  HDBSCAN → 10 named segments, penalty-weighted, validated by asymmetric cost matrix + per-segment recall.
- Code: `src/` (flat, shares `from pal_colors import`); data: `data/raw/`; artifacts: `outputs/` (git-ignored).
- Scripts resolve paths via `ROOT = Path(__file__).resolve().parents[1]` — runnable from anywhere.
- Active work: prototyping the clustering model on the v3 PNR dataset (`data/raw/PAL_PNR_Synthetic_Data_1000-v3.csv`).

## Code quality

Tooling: **ruff** (lint + format) and **bandit** (security), run via **pre-commit**. Config lives in
`pyproject.toml` and `.pre-commit-config.yaml`; dev deps in `requirements-dev.txt`. Keep new code in
`src/` ruff-clean and bandit-clean. Suppress a genuine bandit false positive with an inline
`# nosec <ID> — reason`. Lint excludes `outputs/`, `reports/`, `assets/`, `scratchpad/`, `docs/`.
