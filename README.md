# Darkroom

A background RAW photo editor. Drop photos in, tell it the look you're after — *street*, *architecture*, *portrait*, *Portra film*, *moody black & white* — and it edits them the way a retoucher would, while you carry on working.

It is not a filter pack. Each photo is **measured** (dynamic range, noise, colour cast, sky, faces, backlighting) and the chosen style is **adapted to that picture**: exposure is solved to the style's tonal targets, highlights are recovered only as far as needed, noise reduction is driven by measured sensor noise, skies and faces get their own treatment, and architecture gets straightened. Originals are never touched; every edit writes a JSON recipe next to the output so it can be re-rendered later.

## Quick start

```bash
pip install -e .            # Python 3.10+

darkroom serve              # web app at http://127.0.0.1:8765
darkroom edit IMG_0001.CR3  # asks "What look are you going for?" in the terminal
darkroom edit shoot/ -l "gritty black and white street" -o out --format jpg,tif
darkroom watch ~/Inbox ~/Edited -s arch_clean   # edits anything dropped in a folder
darkroom styles             # list the 35 looks
```

In the web app: add photos → type or click the look you want → **Edit**. A preview appears within seconds; the full-resolution export renders in the background (queue on the left, one photo at a time, state survives restarts). Drag the before/after handle, nudge brightness/contrast/warmth, change strength, re-edit.

`--explain` (CLI) / "What I did" (web) lists the decisions made for that photo, e.g.

```
White balance: measured cast of -18 mired / +3 tint, correcting 70% (confidence 62%)
Noise: measured σ=0.0121 → luminance NR 47%, colour NR 52%
Sky detected (31% of frame): applying sky-specific recovery
Tone: exposure +0.62 EV to reach tonal key 0.55
Tone: highlights -58 to hold 0.31% clipping
```

## What's inside

| Stage | Detail |
|---|---|
| **RAW decode** | LibRaw via `rawpy`: camera WB, DHT demosaic, highlight blending, 16-bit linear **ProPhoto RGB** working space (all common RAW formats; also JPEG/PNG/TIFF) |
| **Colour engine** | Edits in **Oklab** (perceptual, hue-linear; exposure is an exact multiply); hue-preserving gamut compression to sRGB; dithered 8-bit and 16-bit outputs with an sRGB ICC profile |
| **Geometry** | Auto-**upright** (LSD line detection → vertical + horizontal keystone + rotation, inscribed crop), horizon levelling |
| **White balance** | Mired/tint model; measured-cast neutralisation behind a confidence gate so warm scenes aren't "corrected" |
| **Noise** | Self-calibrating pyramid-coring NR (thresholds measured from the image's own flat areas) + guided chroma NR |
| **Tone** | Exposure solver on the style's histogram targets; filmic base curve (toe/shoulder/pivot); edge-aware highlights/shadows (no halos); whites/blacks; curve; matte fade; auto black point |
| **Presence** | Edge-aware clarity, texture, micro-contrast, dark-channel dehaze |
| **Colour** | Vibrance with skin protection, saturation, 8-band HSL, 3-way colour grade, split-toned B&W with colour-filter mixing |
| **Local** | Sky detection → sky exposure/saturation/blue luminance; graduated filters; face-aware subject dodge and frequency-separation skin smoothing |
| **Effects** | Halation, glow, vignette, luminance-dependent film grain |
| **Output** | Resolution-aware, noise-aware, edge-masked sharpening; JPEG / 16-bit TIFF / PNG |

35 styles in 10 groups — see [docs/STYLES.md](docs/STYLES.md): street (classic, gritty, Tri-X B&W, ultra-grain, neon night, muted urban), architecture (clean, interior, dramatic, B&W, minimal), landscape (natural, golden hour, moody, vivid), portrait (natural, Portra, dark & moody, light & airy, B&W), film (Kodachrome, Velvia, Ektar, CineStill 800T, faded vintage), black & white (HP5, Delta, high-key, noir), cinematic (teal & orange, bleach bypass), commercial (product, food), night, and a neutral pro develop.

Describe a look in words (`"dark moody portrait, warm, grainy"`) and it picks the closest style and turns the adjectives into slider moves.

## Development

```bash
pip install -e '.[dev]'
pytest      # colour maths, RAW decode (synthetic DNGs), geometry, every style, web flow, watch folder
```

`tests/synth.py` builds real Bayer-mosaic DNG files (with shot/read noise) from ordinary pictures, so the genuine LibRaw path is exercised without camera files.

## Honest limits

* The styles are hand-authored from established professional practice (genre conventions, film-stock characteristics, standard retouching workflows), not machine-learned from a dataset. They adapt to each photo, but taste is subjective — use *strength* and the fine-tune sliders.
* RAW decoding was verified with synthetic DNGs; real camera files weren't reachable from the build environment. LibRaw handles the real formats, but expect to tune on your own cameras.
* Face detection uses a bundled LBP cascade (frontal faces only); sky detection is colour/gradient based. If nothing is detected, those local steps are skipped.
* Auto-upright needs visible straight lines; with too few lines or low confidence it does nothing.
* A 24 MP RAW takes about 40 s and ~3 GB RAM on 4 cores; previews take 1–2 s.
