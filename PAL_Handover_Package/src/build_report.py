"""Assemble the shareable status report: embed figures into a self-contained HTML, render a PDF.

Reads the print template `docs/_status-report.template.html`, replaces each `__FIG_<name>__`
token with a base64 data URI of `outputs/report_real/figs/<name>.png`, writes the self-contained
`docs/status-report.html`, then renders `docs/status-report.pdf` via headless Google Chrome.

Run (figures must exist — see src/report_figures.py):  python src/build_report.py
"""

import base64
import subprocess  # nosec B404 — invokes a fixed local Chrome path, no user input
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "outputs" / "report_real" / "figs"
DOCS = ROOT / "docs"
TEMPLATE = DOCS / "_status-report.template.html"
HTML_OUT = DOCS / "status-report.html"
PDF_OUT = DOCS / "status-report.pdf"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def data_uri(png: Path) -> str:
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def main() -> None:
    html = TEMPLATE.read_text()
    for png in sorted(FIGS.glob("*.png")):
        token = f"__FIG_{png.stem}__"
        if token in html:
            html = html.replace(token, data_uri(png))
            print("  embedded", png.name)
    HTML_OUT.write_text(html)
    print("Wrote", HTML_OUT.relative_to(ROOT), f"({HTML_OUT.stat().st_size / 1e6:.1f} MB)")

    subprocess.run(  # nosec B603 — fixed executable + local file, no shell, no user input
        [
            CHROME,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={PDF_OUT}",
            "--no-margins",
            HTML_OUT.as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    print("Wrote", PDF_OUT.relative_to(ROOT), f"({PDF_OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
