"""The edit recipe: every adjustment the pipeline understands, with neutral defaults.

A style is a *partial* recipe; strength interpolates between neutral and the style.
Recipes are plain JSON-serialisable dicts so they can be stored as sidecars and
re-rendered later (non-destructive editing).
"""
from __future__ import annotations

import copy
import json
from typing import Any

HSL_BANDS = ["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]


def _hsl_neutral():
    return {b: {"h": 0.0, "s": 0.0, "l": 0.0} for b in HSL_BANDS}


def _grade_neutral():
    z = lambda: {"h": 0.0, "s": 0.0, "l": 0.0}  # noqa: E731
    return {"shadows": z(), "mids": z(), "highlights": z(), "global": z(),
            "balance": 0.0, "blend": 0.5}


DEFAULT: dict[str, Any] = {
    "geometry": {
        "rotate": 0.0,            # degrees, positive = clockwise
        "auto_upright": 0.0,      # 0..1  vertical/horizontal correction strength
        "auto_horizon": 0.0,      # 0..1  level a near-horizontal horizon
        "crop": None,             # [left, top, right, bottom] fractions
    },
    "wb": {
        "mired": 0.0,             # + warmer, - cooler
        "tint": 0.0,              # + magenta, - green
        "auto": 0.0,              # 0..1 how far to neutralise a measured cast
        "auto_max_mired": 60.0,
    },
    "exposure": {"ev": 0.0},
    "tone": {
        "contrast": 1.0,          # slope of the base filmic curve at the pivot
        "pivot": 0.60,            # display lightness of scene middle grey
        "toe": 0.5,
        "shoulder": 0.5,
        "highlights": 0.0,        # -100..100, local (edge-aware)
        "shadows": 0.0,
        "whites": 0.0,
        "blacks": 0.0,
        "curve": None,            # [[x, y], ...] display lightness curve
        "fade": 0.0,              # lifted/matte blacks 0..0.2
        "chroma_follow": 0.55,    # how much colour follows lightness changes
        "highlight_desat": 0.0,   # 0..1 roll chroma off in the brightest tones
        "shadow_desat": 0.0,
        "black_point": 0.0,       # display L below which values clip to black
    },
    "presence": {
        "clarity": 0.0,           # -100..100 mid-scale local contrast
        "texture": 0.0,           # -100..100 fine-scale
        "dehaze": 0.0,            # 0..100
        "micro_contrast": 0.0,    # very fine, edge-masked
    },
    "color": {
        "vibrance": 0.0,          # -100..100
        "saturation": 0.0,        # -100..100
        "hsl": _hsl_neutral(),
        "grade": _grade_neutral(),
        "skin_protect": 0.6,      # 0..1
        "bw": {
            "amount": 0.0,        # 0..1
            "mix": {b: 0.0 for b in HSL_BANDS},     # band brightness in mono, -1..1
            "tone": {"h": 0.0, "s": 0.0, "split": 0.0, "h2": 0.0, "s2": 0.0},
        },
    },
    "detail": {
        "nr_luma": 0.0,           # 0..1 (1 = remove all measured luma noise)
        "nr_chroma": 0.0,
        "sharpen": 0.0,           # 0..1 amount
        "sharpen_radius": 0.8,    # px at full resolution
        "sharpen_masking": 0.5,   # 0..1 protect flat areas
        "defringe": 0.0,
    },
    "effects": {
        "vignette": {"amount": 0.0, "midpoint": 0.55, "feather": 0.6, "roundness": 0.0},
        "grain": {"amount": 0.0, "size": 1.0, "roughness": 0.5, "chroma": 0.0},
        "halation": {"amount": 0.0, "radius": 0.012, "threshold": 0.85, "hue": 20.0},
        "glow": {"amount": 0.0, "radius": 0.02},
    },
    "local": {
        "sky": {"exposure": 0.0, "saturation": 0.0, "blue_lum": 0.0, "warmth": 0.0},
        "gradient_top": {"exposure": 0.0, "extent": 0.45},
        "gradient_bottom": {"exposure": 0.0, "extent": 0.35},
        "subject": {"exposure": 0.0, "radius": 0.35},   # soft spotlight on faces/centre
        "skin_smooth": 0.0,
    },
}

MODIFIER_DOC = {
    "brightness": "-1..1  overall exposure bias (±1.5 EV)",
    "contrast": "-1..1",
    "warmth": "-1..1  cool..warm",
    "saturation": "-1..1",
    "grain": "0..1  extra film grain",
    "fade": "0..1  matte blacks",
    "clarity": "-1..1",
    "vignette": "0..1",
}


def default() -> dict:
    return copy.deepcopy(DEFAULT)


def merge(base: dict, over: dict) -> dict:
    """Deep-merge ``over`` onto ``base`` (new dict)."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _lerp(a, b, s):
    if isinstance(a, bool) or isinstance(b, bool):
        return b if s >= 0.5 else a
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * s
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: _lerp(a.get(k), b[k], s) if k in a else b[k] for k in b} | {k: a[k] for k in a if k not in b}
    if a is None and isinstance(b, list) and b and isinstance(b[0], (list, tuple)):
        return [[x, x + (y - x) * s] for x, y in b]       # curve vs identity
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and a and not isinstance(a[0], (list, tuple)):
        return [_lerp(x, y, s) for x, y in zip(a, b)]
    return b if s >= 0.5 else a


def scaled(style: dict, strength: float) -> dict:
    """Neutral recipe blended toward ``style`` by ``strength`` (0..1, may exceed 1 mildly)."""
    full = merge(DEFAULT, style)
    return _lerp(DEFAULT, full, strength)


def apply_modifiers(r: dict, mods: dict | None) -> dict:
    """Layer user-facing sliders on top of a recipe."""
    if not mods:
        return r
    r = copy.deepcopy(r)
    g = lambda k: float(mods.get(k, 0.0) or 0.0)  # noqa: E731
    r["exposure"]["ev"] += 1.5 * g("brightness")
    r["tone"]["contrast"] *= 1.0 + 0.35 * g("contrast")
    r["wb"]["mired"] += 28.0 * g("warmth")
    r["color"]["saturation"] += 35.0 * g("saturation")
    r["color"]["vibrance"] += 20.0 * g("saturation")
    r["effects"]["grain"]["amount"] = min(1.0, r["effects"]["grain"]["amount"] + 0.6 * max(0.0, g("grain")))
    r["tone"]["fade"] += 0.08 * max(0.0, g("fade"))
    r["presence"]["clarity"] += 30.0 * g("clarity")
    r["effects"]["vignette"]["amount"] = min(1.0, r["effects"]["vignette"]["amount"] + 0.5 * max(0.0, g("vignette")))
    return r


def dumps(r: dict) -> str:
    return json.dumps(r, indent=1, sort_keys=False)


def loads(s: str) -> dict:
    return merge(DEFAULT, json.loads(s))
