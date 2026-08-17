"""Canonical PAL segment colour palette — import this everywhere.

⚠️ **`SEG_ORDER` is the *current model output*, not the approved taxonomy.** They diverged on
2026-08-17 when PAL settled the taxonomy decisions from `docs/sme-constraints-intake.md` §7:

  • **MICE · Ultra Wealthy Leisure · Intl. Student** were approved as real segments, taking the
    taxonomy from 10 to 13. They have colours below and appear in `SEG_APPROVED`, but the proxy
    waterfall in `src/features_real.py` does **not emit them yet**, so they are deliberately kept
    out of `SEG_ORDER` — a chart legend must not advertise a segment the model never assigns.
  • **Last-Minute becomes a flag, not a peer segment.** It stays in `SEG_ORDER` because the shipped
    model still emits it (2,945,686 bookings), and leaves once the waterfall changes.

So: plot with `SEG_ORDER` (what the data contains); plan with `SEG_APPROVED` (what PAL agreed).
Reconciling the two is the pending waterfall change — see `docs/methodology.md`.
"""

SEG_COLORS = {
    "Corporate": "#38BDF8",  # sky blue
    "Mabuhay Loyalist": "#FBBF24",  # gold / amber
    "OFW/Migrant": "#EF4444",  # red
    "Premium Bleisure": "#C084FC",  # violet / purple
    "Balikbayan/VFR": "#22C55E",  # emerald green
    "Pilgrimage": "#F97316",  # orange
    "Family": "#E879F9",  # fuchsia / magenta
    "Budget/Adventure": "#A3E635",  # lime
    "Last-Minute": "#94A3B8",  # slate (neutral)
    "Digital Nomad": "#2DD4BF",  # teal
    # approved 2026-08-17, not yet emitted by the waterfall. Hues chosen to stay distinguishable
    # from the ten above in both light and dark renders, and from each other.
    "MICE": "#0EA5E9",  # deep cyan — adjacent to Corporate, which it splits off from
    "Ultra Wealthy Leisure": "#A855F7",  # deep purple — adjacent to Premium Bleisure, its parent
    "Intl. Student": "#84CC16",  # olive-lime — adjacent to Budget/Adventure
    "Unassigned": "#4B5563",  # dark gray
}

# What the shipped model actually emits today. Use for any chart, table or legend built from
# `proxy_segment`, so the categories match the data.
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

# The taxonomy PAL has approved. Differs from SEG_ORDER until the waterfall is updated:
# adds the three new segments; `Last-Minute` is absent because it becomes a flag.
SEG_APPROVED = [
    "Corporate",
    "Mabuhay Loyalist",
    "OFW/Migrant",
    "Premium Bleisure",
    "Balikbayan/VFR",
    "Pilgrimage",
    "Family",
    "Budget/Adventure",
    "Digital Nomad",
    "MICE",
    "Ultra Wealthy Leisure",
    "Intl. Student",
    "Unassigned",
]

# Booking-level flags that may accompany any segment, rather than competing with one.
# `Last-Minute` moves here once the waterfall change lands (PAL decision, 2026-08-17): 84.1% of it
# would otherwise be Budget/Adventure, so it describes a booking, not a kind of traveller.
SEG_FLAGS = ["Last-Minute"]

# Sequential list matching SEG_ORDER (for palette= args)
SEG_PALETTE = [SEG_COLORS[s] for s in SEG_ORDER]

# Same, for the approved taxonomy
SEG_APPROVED_PALETTE = [SEG_COLORS[s] for s in SEG_APPROVED]

assert set(SEG_ORDER) <= set(SEG_COLORS), "every emitted segment needs a colour"
assert set(SEG_APPROVED) <= set(SEG_COLORS), "every approved segment needs a colour"
assert set(SEG_FLAGS) <= set(SEG_COLORS), "every flag needs a colour"
