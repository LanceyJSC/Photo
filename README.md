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
darkroom serve --lan        # same, reachable from your phone (prints a private link + QR code)
darkroom styles             # list the 59 looks
```

In the web app you never edit anything yourself: **add photos → Darkroom shows *your* photo rendered in looks chosen for it (portrait looks for faces, architecture looks for buildings, night looks for night…) → tap one → done.** The full list of 59 looks (including the photographer ones) is below the recommendations, with search. The full-resolution export renders in the background (queue on the left, one photo at a time, state survives restarts); drag the before/after handle to compare.

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

59 styles in 11 groups — see [docs/STYLES.md](docs/STYLES.md): street (classic, gritty, Tri-X B&W, ultra-grain, neon night, muted urban), architecture (clean, interior, dramatic, B&W, minimal), landscape (natural, golden hour, moody, vivid), portrait (natural, Portra, dark & moody, light & airy, B&W), film (Kodachrome, Velvia, Ektar, CineStill 800T, faded vintage), black & white (HP5, Delta, high-key, noir), cinematic (teal & orange, bleach bypass), commercial (product, food), night, and a neutral pro develop.

**In the manner of a photographer** (21 looks, researched — see below): Ansel Adams, Daido Moriyama, Henri Cartier-Bresson, Fan Ho, Vivian Maier, Sebastião Salgado, Josef Koudelka, Robert Frank, Saul Leiter, William Eggleston, Fred Herzog, Alex Webb, Steve McCurry, Annie Leibovitz, Peter Lindbergh, Todd Hido, Ezra Stoller, Julius Shulman, Iwan Baan, Hélène Binet, Hiroshi Sugimoto. Just type e.g. `like Salgado` or `Moriyama`.

Describe a look in words (`"dark moody portrait, warm, grainy"`) and it picks the closest style and turns the adjectives into slider moves.

## Phone-only version (nothing to install or host)

`browser/darkroom.html` is the whole editor as one static page: the same 59 looks, exposure/highlight/skin/sky analysis, face detection (OpenCV's Haar model ported to JS) and auto-straightening, all running in the phone's browser. Open it from any static host (e.g. GitHub Pages) or as a Claude artifact; photos never leave the device. Limits versus the full app: JPEG/HEIC/PNG input only (no RAW), exports up to ~2600 px on the long side, no noise reduction. Rebuild it with `python scripts/build_browser.py` after changing `darkroom/styles.py` or `browser/darkroom.template.html`.

### iPhone RAW in the phone version

`browser/dng_decoder.js` reads DNG files directly in the browser: **Apple ProRAW** (tiled, lossless-JPEG-compressed LinearRaw) and **Bayer RAW DNG** from camera apps. The photo is decoded tile by tile and reduced as it goes (never the full 48 MP in memory), converted to linear light with the file's own colour matrices and white balance, and edited as floating-point data so highlights and shadows keep their RAW latitude. Apple's photo picker converts RAW to JPEG, so the file has to be chosen from Files (Photos, Share, Save to Files). Tests (`tests/test_dng_decoder.py`) use synthetic DNGs in the documented ProRAW layout that LibRaw reads bit-for-bit identically; no real iPhone file was available in the build environment, so expect to report any iPhone-specific quirks.

### Retouching, not filtering (phone version)

Each look is applied through masks, the way a retoucher works:
* **Subject / background separation:** a second neural network (DeepLab-v3, 21 object classes: person, cat, dog, car...) outlines the subject; the edge is snapped to the photo's real edges. The subject is lifted and sharpened (clarity plus broad dodge-and-burn style contouring) while the background is held back, desaturated and softened.
* **Skin:** within the person mask, blotchy mid-frequency skin is smoothed (frequency separation) while pores and edges stay; looks documented as "unretouched" (Lindbergh, Cartier-Bresson) leave skin alone.
* **Eyes:** brightened using the detected face geometry.
* **Noise:** a self-calibrating luminance and colour noise reduction, strength measured from the photo itself at the size it is rendered, important for lifted RAW shadows.
* **RAW develop:** extra contrast, colour and capture sharpening for RAW, an automatic white point so highlights are clean, plus the exposure/highlight/shadow solver.

### Machine learning in the phone version

* **Seeing the photo.** Every photo goes through Google's EfficientNet-Lite0 (an ImageNet network trained on 1.2 M labelled photos, Apache-2.0, from MediaPipe). It runs on the phone in a Web Worker using a small JavaScript inference engine (`browser/vision_engine.js`) with the weights exported by `scripts/export_vision_model.py` as 8-bit. Its answer ("espresso 90%", "Egyptian cat 77%", "obelisk 17%") is mapped to genres (`scripts/vision_groups.py`) to choose which looks to recommend; measurements (light, colour cast, faces, sky, lines) are shown in *What I found in this photo*. The JS engine was checked against the reference TFLite model (same top answer; probabilities within 0.011 because of the 8-bit weights).
* **Learning your taste.** The network's 1280-number description of each photo is stored (random-projected to 256 numbers) with the look you picked. For a new photo, a nearest-neighbour model finds the photos you handled before and recommends what you chose on them, plus your overall favourites ("Picked for you"). Taps count 0.4, saves count 1. It is saved to your account when the page has a database, otherwise in the browser.
* **Not learned:** the look recipes themselves. Training a network to edit like professionals needs thousands of photos with expert edits (e.g. Adobe FiveK), which were not reachable from the build environment. Your own picks are the training data for taste; if you have a set of your own edited photos, the next step is to train on those.

## On your phone with the full app (RAW, no Xcode, no App Store)

Darkroom is a web app, so the phone only needs a browser. Open it in Safari/Chrome and choose *Add to Home Screen* to install it like an app. The editing itself runs on whatever machine runs Darkroom, so you need one of:

* **Your computer at home/office** — `darkroom serve --lan` prints a private link and QR code; scan it with the phone on the same Wi-Fi.
* **A small hosted server** (so it works from anywhere, including a phone with no computer) — a `Dockerfile` is included; deploy it to Fly.io / Render / a VPS, set `DARKROOM_TOKEN` to a long secret, and open `https://your-host/?token=…` once on the phone. Expect to need at least ~4 GB RAM for full-size RAW files.

The layout is built for touch: filmstrip, tap-a-look grid, finger-drag before/after slider, pinned **Apply** button, camera button, upload progress, and **Save / Share** to Photos. iPhone **HEIC** and ProRAW **DNG** work (iOS may convert photos to JPEG/HEIC when picked from the library; pick from *Files* to keep the DNG). The *Share → Darkroom* target works on Android only; iOS doesn't support web share targets.

## How the photographer looks were made

I searched for how each photographer worked and encoded what the sources actually support, labelling the rest as interpretation in each style's `Basis` note ([docs/STYLES.md](docs/STYLES.md)). Honest summary: the web has plenty on *what their pictures look like* (Adams' Zone System and dodging/burning, Fan Ho's low-sun shadow, Moriyama's pushed grain and contrast, Leiter/Herzog/Eggleston on Kodachrome and dye-transfer colour, Webb's saturated layered light, Lindbergh's minimal retouching, Sugimoto's smooth long exposures, Stoller's geometry) and very little on exact editing numbers. So these are faithful-in-spirit approximations — not copies of anyone's workflow — and they adapt to each photo like every other style.

## Development

```bash
pip install -e '.[dev]'
pytest      # colour maths, RAW decode (synthetic DNGs), geometry, every style, web flow, watch folder
```

`tests/synth.py` builds real Bayer-mosaic DNG files (with shot/read noise) from ordinary pictures, so the genuine LibRaw path is exercised without camera files.

## Honest limits

* The styles are hand-authored from established professional practice (genre conventions, film-stock characteristics, standard retouching workflows), not machine-learned from a dataset. They adapt to each photo, but taste is subjective — use *strength* and the fine-tune sliders.
* Photographer styles are approximations from sparse public information (see above); Maier, Hido, Frank and similar entries lean mostly on interpretation of their published work.
* RAW decoding was verified with synthetic DNGs; real camera files weren't reachable from the build environment. LibRaw handles the real formats, but expect to tune on your own cameras.
* Face detection uses OpenCV's bundled Haar cascade (frontal faces only); sky detection is colour/gradient based. If nothing is detected, those local steps are skipped.
* Auto-upright needs visible straight lines; with too few lines or low confidence it does nothing.
* A 24 MP RAW takes about 40 s and ~3 GB RAM on 4 cores; previews take 1–2 s.
