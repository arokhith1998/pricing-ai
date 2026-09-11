"""Record a short screen walkthrough of the live sample for investor follow-up.

  python tools/record_sample_walkthrough.py

Writes decks/assets/sample-walkthrough.webm (1280x720). Roughly 40 seconds:
land on the product page, read the positioning, scroll into the live sample,
let the KPI tiles settle, then walk the read-out.

Deliberately NOT embedded in the PDF. A deck must survive as a flat file in an
inbox, and embedded video bloats it and breaks in most viewers. Host this and
put the link on the follow-up email instead.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decks" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://pricekeel.com"


def _glide(page, to: int, steps: int = 22, pause: int = 55) -> None:
    """Scroll in small increments. A single jump reads as a cut in the video."""
    start = page.evaluate("window.scrollY")
    for i in range(1, steps + 1):
        y = start + (to - start) * i / steps
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(pause)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(OUT),
            record_video_size={"width": 1280, "height": 720},
        )
        page = ctx.new_page()

        # 1. The product page: positioning and the why-now line.
        page.goto(BASE, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(3500)
        _glide(page, 700)
        page.wait_for_timeout(2000)

        # 2. The live sample: let the KPI count-up finish before it is on screen
        #    long enough to read.
        page.goto(f"{BASE}/sample", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(5000)
        page.wait_for_timeout(3000)

        # 3. Walk the read-out.
        for target in (600, 1200, 1800, 2400):
            _glide(page, target)
            page.wait_for_timeout(1800)

        page.wait_for_timeout(1500)
        ctx.close()  # finalizes the video file
        browser.close()

    vids = sorted(OUT.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not vids:
        print("  no video written")
        return 1
    final = OUT / "sample-walkthrough.webm"
    if vids[-1] != final:
        final.unlink(missing_ok=True)
        vids[-1].rename(final)
    print(f"  wrote {final.relative_to(ROOT)} ({final.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
