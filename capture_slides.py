"""
capture_slides.py — Export each .slide div from pal_executive_deck.html as a 1600×900 PNG.
Usage: python3 capture_slides.py
"""

import os
import sys

HTML_FILE = os.path.abspath("kick-off-call/pal_executive_deck.html")
OUT_DIR   = "executive_slides"

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing playwright …")
        os.system(f"{sys.executable} -m pip install playwright -q")
        os.system(f"{sys.executable} -m playwright install chromium")
        from playwright.sync_api import sync_playwright

    os.makedirs(OUT_DIR, exist_ok=True)
    file_url = f"file://{HTML_FILE}"

    SLIDE_LABELS = [
        "01_Methodology",
        "02_ML_Deep_Dive",
        "03_POC_Results",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.goto(file_url)

        # Wait for Google Fonts to load (2 s is sufficient for local file access)
        page.wait_for_timeout(2500)

        slides = page.query_selector_all(".slide")
        print(f"Found {len(slides)} slides\n")

        for i, slide in enumerate(slides):
            label = SLIDE_LABELS[i] if i < len(SLIDE_LABELS) else f"Slide_{i+1:02d}"
            out_path = os.path.join(OUT_DIR, f"PAL_{label}.png")
            slide.screenshot(path=out_path)
            print(f"  ✓  {out_path}")

        browser.close()

    print(f"\nAll slides exported to ./{OUT_DIR}/")


if __name__ == "__main__":
    main()
