"""
capture_slides.py — Export each .slide div of an HTML deck as a 1600×900 PNG.

Usage:
    python src/capture_slides.py                       # the kick-off executive deck (default)
    python src/capture_slides.py --deck tuesday        # Josh's Tuesday deck
    python src/capture_slides.py --deck path/to.html --out reports/my_slides
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Named decks — so callers pass a short name rather than a path.
# (html, output dir, per-slide labels used as the PNG filename suffix)
DECKS = {
    "executive": (
        ROOT / "assets" / "kick-off-call" / "pal_executive_deck.html",
        ROOT / "reports" / "executive_slides",
        ["01_Methodology", "02_ML_Deep_Dive", "03_POC_Results"],
    ),
    "tuesday": (
        ROOT / "assets" / "tuesday-slides" / "josh-slides.html",
        ROOT / "reports" / "tuesday_slides",
        [
            "01_Current_Methodology",
            "02_Business_Rules",
            "03_Success_Metrics",
            "04_SME_Constraints",
            "05_Persona_Cards",
        ],
    ),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--deck", default="executive", help=f"named deck {tuple(DECKS)} or an .html path"
    )
    ap.add_argument("--out", help="output directory (overrides the deck default)")
    args = ap.parse_args()

    if args.deck in DECKS:
        html, out_dir, labels = DECKS[args.deck]
    else:  # explicit path — label slides positionally
        html, out_dir, labels = Path(args.deck).resolve(), ROOT / "reports" / "slides", []
    if args.out:
        out_dir = Path(args.out)
    if not html.exists():
        sys.exit(f"Deck not found: {html}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing playwright …")
        os.system(f"{sys.executable} -m pip install playwright -q")  # nosec B605
        os.system(f"{sys.executable} -m playwright install chromium")  # nosec B605
        from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.goto(html.as_uri())
        # Google Fonts are remote; without the wait the first slide renders in a fallback face.
        page.wait_for_timeout(2500)

        slides = page.query_selector_all(".slide")
        print(f"{html.name}: found {len(slides)} slides\n")

        for i, slide in enumerate(slides):
            label = labels[i] if i < len(labels) else f"Slide_{i + 1:02d}"
            out_path = out_dir / f"PAL_{label}.png"
            slide.screenshot(path=str(out_path))
            print(f"  ✓  {out_path.relative_to(ROOT)}")

        browser.close()

    print(f"\nExported to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
