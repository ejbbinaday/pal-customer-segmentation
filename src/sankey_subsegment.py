"""Single-focus Sankey: one parent segment splitting into its LCA sub-types.

Built for the defence deck's refinement slide, which needs **one** worked example rather than all five
parents in text. Default parent is `Balikbayan/VFR` — 12.5% of bookings and 28.4% of revenue, the
segment recommendation 1 tells PAL to protect.

**The PNG is the diagram only — no text.** Every label lives in PowerPoint as an editable text box, so
wording, size and font can be changed in the deck without regenerating anything. To make that possible
the figure is drawn with the axes filling the canvas exactly (`add_axes([0, 0, 1, 1])`, and saved
*without* `bbox_inches="tight"`), so axes coordinates map linearly onto the picture's placement:

    slide_x = left + x * width          slide_y = top + (1 - y) * height

Label anchor points are written beside the PNG as JSON, one per node at that node's **centre**, so a
slide-side text box lands level with its own ribbon and needs no leader line. The geometry is tuned so
the tightest pair of anchors clears the height of a two-line label; each label also carries a colour
chip, so identity never depends on vertical proximity alone.

**Source of truth.** This reads `outputs/sub_segments/summary.md`, the report `sub_segment.py` writes,
rather than re-fitting the LCA. Re-fitting would cost five StepMix sweeps and, worse, create a second
set of sub-type numbers that could disagree with the report the docs already quote. Verified 19 Aug
2026: a refit reproduces the report's shares and medians exactly.

**Encoding.** Ribbon width is share of the parent's bookings; fill and vertical order are median
revenue per booking on a **single-hue sequential ramp** (light → dark, monotonic in OKLab L:
0.884 · 0.757 · 0.560 · 0.392), the sanctioned encoding for an ordinal magnitude — see the palette
note in `src/segment_charts.py`. Colour is redundant: rows are ordered by the same value it encodes and
every flow is labelled on the slide, so nothing rests on hue. The light steps sit below 3:1 against the
surface, so no text is ever set on a fill.

Run:  python src/sankey_subsegment.py [--parent "Corporate"]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib.patches import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "outputs" / "sub_segments" / "summary.md"
OUT = ROOT / "outputs" / "segment_charts"

INK = "#14213A"
INK_FAINT = "#7A8298"
SURFACE = "#FFFFFF"
RAMP = ["#C9DCE9", "#8FB6D0", "#3B7CA2", "#0E4A6E"]  # light → dark, sequential

# geometry in axes fractions — the JSON reports these so the slide can align to them
SRC_X0, SRC_X1 = 0.035, 0.088
TGT_X0, TGT_X1 = 0.925, 0.995
TOP, BOT = 0.955, 0.045
TGT_FRAC = 0.75  # targets take this share of the source's height, so ribbons visibly taper
GAP = 0.045  # surface gap between target fills

mpl.rcParams.update({"figure.facecolor": SURFACE, "savefig.facecolor": SURFACE})


def parse_report(parent: str) -> list[dict]:
    """Pull one parent's sub-type rows out of the sub-segmentation report."""
    for block in re.split(r"\n## ", REPORT.read_text()):
        if not block.startswith(parent):
            continue
        rows = []
        for line in block.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 6 or cells[0] == "sub_name" or set(cells[0]) <= set(":- "):
                continue
            try:
                rows.append(
                    {
                        "name": cells[0],
                        "n": int(cells[1]),
                        "pct": float(cells[2]),
                        "lead": int(float(cells[3])),
                        "rev": float(cells[5]),
                    }
                )
            except ValueError:
                continue
        if rows:
            return rows
    raise SystemExit(f"parent {parent!r} not found in {REPORT}")


def ribbon(x0: float, x1: float, y0a: float, y0b: float, y1a: float, y1b: float) -> MplPath:
    """A cubic-Bezier band from (x0, y0a..y0b) to (x1, y1a..y1b)."""
    cx = (x0 + x1) / 2
    verts = [
        (x0, y0a),
        (cx, y0a),
        (cx, y1a),
        (x1, y1a),
        (x1, y1b),
        (cx, y1b),
        (cx, y0b),
        (x0, y0b),
        (x0, y0a),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    return MplPath(verts, codes)


def draw(parent: str, width_in: float, height_in: float) -> tuple[Path, Path]:
    """Draw the diagram alone and write the label anchors beside it."""
    rows = sorted(parse_report(parent), key=lambda r: -r["rev"])  # value ladder, top = highest
    total = sum(r["pct"] for r in rows)
    shares = [r["pct"] / total for r in rows]

    fig = plt.figure(figsize=(width_in, height_in), dpi=220)
    ax = fig.add_axes((0, 0, 1, 1))  # axes fills the canvas, so coords map onto the slide
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    span = TOP - BOT
    tgt_span = span * TGT_FRAC - GAP * (len(rows) - 1)
    tgt_top = TOP - (span - (tgt_span + GAP * (len(rows) - 1))) / 2

    ax.add_patch(Rectangle((SRC_X0, BOT), SRC_X1 - SRC_X0, span, facecolor=INK, edgecolor="none"))

    src_y, tgt_y = TOP, tgt_top
    anchors = []
    for i, share in enumerate(shares):
        h_src, h_tgt = share * span, share * tgt_span
        colour = RAMP[len(RAMP) - 1 - i] if len(rows) == len(RAMP) else RAMP[-1]

        ax.add_patch(
            PathPatch(
                ribbon(SRC_X1, TGT_X0, src_y, src_y - h_src, tgt_y, tgt_y - h_tgt),
                facecolor=colour,
                edgecolor=SURFACE,
                linewidth=1.0,
                alpha=0.95,
            )
        )
        ax.add_patch(
            Rectangle(
                (TGT_X0, tgt_y - h_tgt),
                TGT_X1 - TGT_X0,
                h_tgt,
                facecolor=colour,
                edgecolor="none",
            )
        )
        anchors.append(tgt_y - h_tgt / 2)
        src_y -= h_src
        tgt_y -= h_tgt + GAP

    OUT.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", parent.lower()).strip("_")
    png = OUT / f"fig_s07_sankey_{slug}.png"
    fig.savefig(png, pad_inches=0)  # no tight bbox — the coord mapping depends on it
    plt.close(fig)

    meta = OUT / f"fig_s07_sankey_{slug}.json"
    meta.write_text(
        json.dumps(
            {
                "parent": parent,
                "png": png.name,
                "width_in": width_in,
                "height_in": height_in,
                "ramp": RAMP,
                "rows": [
                    {**row, "anchor_y": round(a, 5), "colour": RAMP[len(RAMP) - 1 - i]}
                    for i, (row, a) in enumerate(zip(rows, anchors))
                ],
            },
            indent=2,
        )
    )
    return png, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", default="Balikbayan/VFR")
    ap.add_argument("--width", type=float, default=6.4, help="picture width on the slide, inches")
    ap.add_argument(
        "--height", type=float, default=3.30, help="picture height on the slide, inches"
    )
    args = ap.parse_args()
    png, meta = draw(args.parent, args.width, args.height)
    print("wrote", png)
    print("wrote", meta)


if __name__ == "__main__":
    main()
