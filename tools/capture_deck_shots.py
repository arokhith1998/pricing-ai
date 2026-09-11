"""Capture product screenshots for the investor deck.

Shoots the live public surfaces at pricekeel.com into decks/assets/ at 2x device
scale so they stay sharp when a PDF is printed or zoomed. Waits out the KPI
count-up animation so tiles show their final values, never a mid-animation
number.

  python tools/capture_deck_shots.py

Gated surfaces (the full diagnostic, deal desk, CRM workflow) cannot be shot
here because they need a customer access code. Those come from a founder-run
capture saved at the repo root, which this script then crops into deck panels.
decks/ and root PNGs are both gitignored, so the deck is a build artifact:
everything it needs regenerates from this script plus the root capture.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decks" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://pricekeel.com"

# (slug, path, full_page, viewport height)
SHOTS = [
    ("sample-hero", "/", False, 1000),
    ("sample-full", "/", True, 1000),
    ("pricing", "/pricing", False, 1100),
    ("trust", "/trust", False, 1100),
]

# The KPI tiles count up on mount. Anything shorter than this captures a
# mid-animation number, which would put a wrong figure in an investor deck.
SETTLE_MS = 4500


# Panels cropped out of the founder's full-page capture of the gated guidance
# surface. Keyed by output name: (source, top, bottom) in source pixels.
# Aspect matters: the deck sizes screenshots by width and never clips, so a
# panel that is too tall simply overflows its slide.
GUIDANCE_SRC = ROOT / "item3-guidance-evidence.png"
PANELS = {
    "product-recommendation.png": (1200, 2600),  # headline, KPIs, EV curve, why
    "product-evidence.png": (2620, 3560),        # comparables, win rate by band
}


def crop_panels() -> None:
    if not GUIDANCE_SRC.exists():
        print(f"  SKIP panels: {GUIDANCE_SRC.name} not found at repo root.")
        print("       Recapture the /guidance surface with a customer access code.")
        return
    from PIL import Image

    src = Image.open(GUIDANCE_SRC)
    w, h = src.size
    for name, (top, bottom) in PANELS.items():
        im = src.crop((150, top, w - 40, min(bottom, h)))
        im.save(OUT / name)
        print(f"  wrote {(OUT / name).relative_to(ROOT)} ({im.size[0]}x{im.size[1]})")


def main() -> int:
    crop_panels()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=2,
        )
        for slug, path, full, height in SHOTS:
            page.set_viewport_size({"width": 1440, "height": height})
            url = f"{BASE}{path}"
            try:
                page.goto(url, wait_until="networkidle", timeout=45_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  SKIP {slug}: {exc}")
                continue
            page.wait_for_timeout(SETTLE_MS)
            out = OUT / f"{slug}.png"
            page.screenshot(path=str(out), full_page=full)
            print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
