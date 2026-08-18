"""Canonical PAL segment colour palette — import this everywhere.

⚠️ **`SEG_ORDER` is the *current model output*; `SEG_APPROVED` is the taxonomy PAL has agreed.**
They diverge until the waterfall change in `docs/waterfall-v2-design.md` lands. Plot with
`SEG_ORDER` (what the data contains); plan with `SEG_APPROVED` (what PAL asked for). A chart legend
must never advertise a segment the model does not assign — an empty category reads as "zero
customers", not "not built yet".

Settled by PAL 17–18 Aug 2026 (`wishlist/pal-questions-answered-2026-08-18.csv`):

  • **added** MICE · Ultra Wealthy Leisure · Intl. Student · Outbound International Leisure
  • **renamed** `Budget/Adventure` → **`Leisure`** (D4). A rename, not a mapping — reversing the
    17 Aug position, so the palette, Power BI dimension, personas and decks all follow.
  • **dropped `Family`** (A6/C6). It had no positive definition: 100% of it was "a group booking no
    other rule claimed". RM's own read was that the only further signal would be group travel over
    long weekends, which needs a PH holiday calendar we do not have.
  • **dropped `Digital Nomad`** (D2). The one segment in the original requirement never implemented;
    resolved by deletion rather than by a definition.
  • **`Last-Minute` becomes a flag**, not a peer segment — it describes a booking, not a traveller.

Net: **11 segments + `Unassigned`**, down from a nominal 10 named + Unassigned but with four
additions and three removals.
"""

SEG_COLORS = {
    "Corporate": "#38BDF8",  # sky blue
    "Mabuhay Loyalist": "#FBBF24",  # gold / amber
    "OFW/Migrant": "#EF4444",  # red
    "Premium Bleisure": "#C084FC",  # violet / purple
    "Balikbayan/VFR": "#22C55E",  # emerald green
    "Pilgrimage": "#F97316",  # orange
    "Leisure": "#A3E635",  # lime — was Budget/Adventure, renamed 18 Aug
    "MICE": "#0EA5E9",  # deep cyan — adjacent to Corporate, which it splits off from
    "Ultra Wealthy Leisure": "#A855F7",  # deep purple — adjacent to Premium Bleisure, its parent
    "Intl. Student": "#84CC16",  # olive-lime — adjacent to Leisure
    "Outbound International Leisure": "#14B8A6",  # teal — freed by dropping Digital Nomad
    "Unassigned": "#4B5563",  # dark gray
    # ── retired, kept so historical artifacts still render ────────────────────────
    "Budget/Adventure": "#A3E635",  # renamed to Leisure (same hue, so old charts stay comparable)
    "Last-Minute": "#94A3B8",  # slate — now a flag, see SEG_FLAGS
    "Family": "#E879F9",  # fuchsia — dropped 18 Aug
    "Digital Nomad": "#2DD4BF",  # never implemented; dropped 18 Aug
}

# What the shipped model emits TODAY. Use for any chart or table built from `proxy_segment`.
SEG_ORDER = [
    "Corporate",
    "Mabuhay Loyalist",
    "OFW/Migrant",
    "Premium Bleisure",
    "Balikbayan/VFR",
    "Pilgrimage",
    "Family",
    "Budget/Adventure",
    "Last-Minute",
    "Digital Nomad",
    "Unassigned",
]

# The taxonomy PAL has approved. Becomes SEG_ORDER when the waterfall change lands.
SEG_APPROVED = [
    "Corporate",
    "MICE",
    "Mabuhay Loyalist",
    "OFW/Migrant",
    "Balikbayan/VFR",
    "Outbound International Leisure",
    "Premium Bleisure",
    "Ultra Wealthy Leisure",
    "Pilgrimage",
    "Intl. Student",
    "Leisure",
    "Unassigned",
]

# Booking-level flags: they accompany a segment rather than competing with one.
SEG_FLAGS = ["Last-Minute"]

# Segments that existed and no longer do. Kept explicit so a stale reference is a lookup, not a
# mystery — and so `dim_segment` can carry a retirement note instead of a row vanishing.
SEG_RETIRED = {
    "Budget/Adventure": "renamed to 'Leisure' (PAL, 18 Aug 2026)",
    "Family": "dropped — no positive definition beyond `is_group` (PAL, 18 Aug 2026)",
    "Digital Nomad": "dropped — never implementable in anonymous data (PAL, 18 Aug 2026)",
    "Last-Minute": "became a booking flag, not a segment (PAL, 17 Aug 2026)",
}

# Renames, as a machine-readable map. Anything comparing an old label to a new one MUST apply this
# first, or the rename shows up as a disagreement — it produced a fake 6.9M-booking "finding" in
# src/apply_soft_priors.py before this map existed.
SEG_RENAMED = {"Budget/Adventure": "Leisure"}


def canonical(seg: str) -> str:
    """Old label -> current label. Identity for everything that was not renamed."""
    return SEG_RENAMED.get(seg, seg)


# Sequential lists matching the orders above (for palette= args)
SEG_PALETTE = [SEG_COLORS[s] for s in SEG_ORDER]
SEG_APPROVED_PALETTE = [SEG_COLORS[s] for s in SEG_APPROVED]

assert set(SEG_ORDER) <= set(SEG_COLORS), "every emitted segment needs a colour"
assert set(SEG_APPROVED) <= set(SEG_COLORS), "every approved segment needs a colour"
assert set(SEG_FLAGS) <= set(SEG_COLORS), "every flag needs a colour"
assert set(SEG_RETIRED) <= set(SEG_COLORS), "retired segments keep their colour for old artifacts"
assert not set(SEG_APPROVED) & set(SEG_RETIRED), "a segment cannot be both approved and retired"
