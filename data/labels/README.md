# SME ground-truth labels

Drop a file named **`sme_sample.csv`** here to enable non-circular hold-out validation.

Format (see `sme_sample_TEMPLATE.csv`):

| column | meaning |
|---|---|
| `Unique Identifier` | the PNR id from `PAL_PNR_Synthetic_Data_1000-v3.csv` |
| `true_segment` | the SME-assigned segment (one of the 10 canonical names in `src/pal_colors.py`) |

`src/prototype_v3.py` auto-detects `sme_sample.csv`, joins it to the held-out test set, and reports a
**real** (non-circular) per-segment recall + weighted cost alongside the proxy-referenced numbers.
Even 100–200 labelled rows are enough to replace the circular proxy recall with a defensible metric.

Only rows that fall in the held-out split contribute to the SME metric, so labelling a spread across
segments (especially the high-penalty Corporate / OFW) is most valuable.
