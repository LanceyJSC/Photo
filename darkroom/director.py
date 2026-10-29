"""The 'editor brain': turns a style + the measured scene into a concrete recipe.

A style says what the finished picture should feel like.  The director looks at
*this* photograph (exposure, dynamic range, noise, colour cast, sky, faces) and
adapts the recipe the way a retoucher would, rather than applying fixed numbers.
"""
from __future__ import annotations

import numpy as np

from . import pipeline, recipe as rcp, styles
from .analysis import Analysis


def _clip(v, lo, hi):
    return float(np.clip(v, lo, hi))


def plan(rgb: np.ndarray, an: Analysis, style: styles.Style, strength: float = 1.0,
         modifiers: dict | None = None, overrides: dict | None = None) -> tuple[dict, list]:
    """Return (recipe, notes).  ``notes`` explains each decision in plain English."""
    notes: list[str] = [f"Look: {style.name} at {int(round(strength * 100))}% strength"]
    r = rcp.scaled(style.recipe, float(np.clip(strength, 0.0, 1.5)))
    adapt = style.adapt
    targets = dict(style.targets or styles.T(0.52))

    # ---- source quality ----------------------------------------------------
    caution = 1.0 if an.is_raw else 0.7
    if not an.is_raw:
        notes.append("Source is an 8-bit file (not RAW): edits are kept gentler to avoid banding/artefacts")
        r["tone"]["shadows"] *= 0.6
        r["presence"]["dehaze"] *= 0.6
        r["presence"]["clarity"] *= 0.85

    # ---- monochrome source / B&W intent -----------------------------------
    if an.is_mono and r["color"]["bw"]["amount"] <= 0:
        r["color"]["vibrance"] = r["color"]["saturation"] = 0
        r["color"]["hsl"] = rcp.default()["color"]["hsl"]
        r["color"]["grade"] = rcp.default()["color"]["grade"]

    # ---- white balance -----------------------------------------------------
    if r["wb"]["auto"] > 0 and an.cast_confidence > 0.15:
        am, at = an.wb_suggest
        notes.append(f"White balance: measured cast of {am:+.0f} mired / {at:+.0f} tint, "
                     f"correcting {int(100 * r['wb']['auto'])}% (confidence {an.cast_confidence:.0%})")

    # ---- noise-aware detail ------------------------------------------------
    sigma = an.noise_sigma
    nr_scale = float(adapt.get("nr", 1.0)) * (1.0 if an.is_raw else 0.5)
    luma = _clip((sigma - 0.0035) / 0.018, 0, 1) * 0.95 * nr_scale
    chroma = _clip((sigma - 0.0015) / 0.010, 0, 1) * 0.95 * nr_scale + (0.25 if an.is_raw else 0.1)
    r["detail"]["nr_luma"] = max(r["detail"]["nr_luma"], luma)
    r["detail"]["nr_chroma"] = max(r["detail"]["nr_chroma"], min(1.0, chroma))
    if luma > 0.15:
        notes.append(f"Noise: measured σ={sigma:.4f} → luminance NR {r['detail']['nr_luma']:.0%}, "
                     f"colour NR {r['detail']['nr_chroma']:.0%}")
    noisy = _clip(sigma / 0.02, 0, 1)
    r["detail"]["sharpen"] = r["detail"]["sharpen"] * (1 - 0.5 * noisy) * (1.0 if an.is_raw else 0.5)
    r["detail"]["sharpen_masking"] = 0.35 + 0.45 * noisy
    r["effects"]["grain"]["amount"] *= (1 - 0.7 * noisy)
    r["presence"]["texture"] *= (1 - 0.6 * noisy)

    # ---- scene-contrast adaptation ----------------------------------------
    sc = pipeline.estimate_scene_contrast(an)
    if sc < -0.2 and r["tone"]["contrast"] >= 1.0:
        boost = 1 + 0.18 * (-sc)
        r["tone"]["contrast"] *= boost
        r["presence"]["dehaze"] += 8 * (-sc)
        notes.append(f"Flat scene ({an.dr_stops:.1f} stops): boosting contrast ×{boost:.2f} and dehaze")
    elif sc > 0.35:
        r["tone"]["contrast"] *= 1 - 0.08 * sc
        r["tone"]["shadows"] += 10 * sc * caution
        r["tone"]["highlights"] -= 10 * sc
        notes.append(f"High-contrast scene ({an.dr_stops:.1f} stops): compressing range")
    if an.backlit:
        r["tone"]["shadows"] += 18 * caution
        r["tone"]["highlights"] -= 10
        r["local"]["subject"]["exposure"] += 0.2
        notes.append("Backlit subject detected: lifting shadows and the subject")

    # ---- colour adaptation -------------------------------------------------
    if an.mean_chroma > 0.11:
        k = 0.6
        r["color"]["vibrance"] *= k
        r["color"]["saturation"] *= k if r["color"]["saturation"] > 0 else 1
        notes.append("Scene already very colourful: reducing saturation moves")
    elif an.mean_chroma < 0.035 and not an.is_mono and r["color"]["bw"]["amount"] < 0.5:
        r["color"]["vibrance"] *= 1.25
    if not r["color"]["bw"]["amount"] and an.skin_frac > 0.08:
        r["color"]["skin_protect"] = max(r["color"]["skin_protect"], 0.8)

    # ---- sky ---------------------------------------------------------------
    if an.sky_frac < 0.05:
        for k in r["local"]["sky"]:
            r["local"]["sky"][k] = 0.0
    else:
        notes.append(f"Sky detected ({an.sky_frac:.0%} of frame): applying sky-specific recovery")
        r["local"]["sky"]["exposure"] *= 1 if an.y_pct[99.5] > 0.6 else 0.4
    if an.sky_frac < 0.05 and r["local"]["gradient_top"]["exposure"]:
        r["local"]["gradient_top"]["exposure"] *= 0.8   # graduated filter still helps landscapes

    # ---- faces / portrait --------------------------------------------------
    if an.faces:
        notes.append(f"{len(an.faces)} face(s) found: protecting skin tones and brightening the subject")
        r["presence"]["clarity"] *= 0.5
        r["presence"]["texture"] = min(r["presence"]["texture"], 0)
        r["color"]["skin_protect"] = 1.0
        if adapt.get("faces") and r["local"]["skin_smooth"] <= 0:
            r["local"]["skin_smooth"] = 0.25
    else:
        r["local"]["skin_smooth"] = 0.0

    # ---- night -------------------------------------------------------------
    if an.night:
        notes.append("Night scene: keeping the darkness, protecting light sources")
        r["tone"]["shadows"] = min(r["tone"]["shadows"], 15)
        r["detail"]["nr_luma"] = min(1.0, r["detail"]["nr_luma"] * 1.3)

    # ---- tonal targets (exposure / highlights / shadows / black point) ----
    solve_log: list[str] = []
    r = pipeline.solve_tone(rgb, r, targets, an, solve_log)
    notes.extend("Tone: " + s for s in solve_log)

    # deep shadow lifts amplify noise; add a little extra NR when we pushed
    if r["exposure"]["ev"] > 0.8 or r["tone"]["shadows"] > 40:
        r["detail"]["nr_luma"] = min(1.0, r["detail"]["nr_luma"] + 0.12)
        r["detail"]["nr_chroma"] = min(1.0, r["detail"]["nr_chroma"] + 0.12)

    # ---- user layers -------------------------------------------------------
    r = rcp.apply_modifiers(r, modifiers)
    if modifiers:
        notes.append("Adjustments: " + ", ".join(f"{k} {v:+.1f}" for k, v in modifiers.items() if v))
    if overrides:
        r = rcp.merge(r, overrides)
    return r, notes
