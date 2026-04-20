"""Canonical PAL segment colour palette — import this everywhere."""

SEG_COLORS = {
    "Corporate":        "#38BDF8",  # sky blue
    "Mabuhay Loyalist": "#FBBF24",  # gold / amber
    "OFW/Migrant":      "#EF4444",  # red
    "Premium Bleisure": "#C084FC",  # violet / purple
    "Balikbayan/VFR":   "#22C55E",  # emerald green
    "Pilgrimage":       "#F97316",  # orange
    "Family":           "#E879F9",  # fuchsia / magenta
    "Budget/Adventure": "#A3E635",  # lime
    "Last-Minute":      "#94A3B8",  # slate (neutral)
    "Digital Nomad":    "#2DD4BF",  # teal
    "Unassigned":       "#4B5563",  # dark gray
}

SEG_ORDER = [
    "Corporate", "Mabuhay Loyalist", "OFW/Migrant", "Premium Bleisure",
    "Balikbayan/VFR", "Pilgrimage", "Family",
    "Budget/Adventure", "Last-Minute", "Digital Nomad", "Unassigned",
]

# Sequential list matching SEG_ORDER (for palette= args)
SEG_PALETTE = [SEG_COLORS[s] for s in SEG_ORDER]
