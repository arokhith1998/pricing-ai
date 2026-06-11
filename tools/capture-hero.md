# Capturing the hero demo video

The landing hero (`web/src/components/HeroDemo.tsx`) is a `<video>` that already
ships: until the MP4 exists it shows its **poster frame** (a real diagnostic
screenshot). Drop the two files below into `web/public/` and the motion goes
live with no code change.

| File | Purpose |
|---|---|
| `web/public/hero-poster.png` | still shown before/instead of the video (and under `prefers-reduced-motion`) |
| `web/public/hero-demo.mp4` | the looping demo, muted, autoplay, ≤ 20s |

## What to record

The diagnostic *working*, in one continuous take, on the synthetic sample (never
customer data). The story in ≤ 20 seconds:

1. A CSV is picked on `/upload` (or `/sample`).
2. The metrics animate in (the `CountUp` figures: booked, realization, win rate).
3. The leakage number lands and holds for a beat.

Keep it calm. One idea: *one CSV in, your number out.* No cursor hunting, no
chrome, no narration.

## How to capture

1. Run the app locally:
   ```
   # API
   PYTHONUTF8=1 PRICEKEEL_ENV=dev python -m uvicorn api.main:app --port 8000
   # web
   cd web && PRICEKEEL_API=http://127.0.0.1:8000 npx next dev -p 3000
   ```
2. Open `http://localhost:3000/sample`, unlock with the lead form, land on the
   diagnostic. Size the window to ~1280x800 and record just the content area
   (macOS: Cmd-Shift-5 region; Windows: Xbox Game Bar / OBS region capture).
3. Trim to ≤ 20s and re-encode small, muted, web-friendly:
   ```
   ffmpeg -i raw.mov -t 20 -an -vf "scale=1280:-2,fps=30" \
     -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 26 -movflags +faststart \
     web/public/hero-demo.mp4
   ```
   `-an` strips audio (the element is muted anyway); `+faststart` lets it start
   playing before fully downloaded; aim for < 2 MB.
4. Export a clean poster from the strongest frame (the leakage number on screen):
   ```
   ffmpeg -i web/public/hero-demo.mp4 -ss 00:00:14 -frames:v 1 web/public/hero-poster.png
   ```

## Checks before shipping

- Loops seamlessly (last frame ~ first frame), muted, autoplays on mobile
  (`playsInline` is already set).
- Lighthouse still ≥ 90: keep the file small and `preload="metadata"`.
- `prefers-reduced-motion`: the component already falls back to the poster, so
  confirm the poster reads on its own.
