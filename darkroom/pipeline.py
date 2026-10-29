"""Render a recipe: the ordered develop / grade pipeline."""
from __future__ import annotations

from typing import Callable

import numpy as np

from . import color, geometry, ops
from .analysis import Analysis, analyze
from .filters import long_side, resize_long

Progress = Callable[[str, float], None]

STAGES = [
    "geometry", "white balance", "noise reduction", "exposure & tone", "presence",
    "colour", "local adjustments", "grade", "effects", "sharpen", "output",
]


def _soft_limit(L: np.ndarray, knee: float = 0.93) -> np.ndarray:
    over = L > knee
    if over.any():
        span = 1.0 - knee
        L = np.where(over, knee + span * np.tanh((L - knee) / span), L)
    return np.maximum(L, 0.0).astype(np.float32)


def develop(pro: np.ndarray, recipe: dict, an: Analysis | None, full_long: int | None = None,
            progress: Progress | None = None, fast: bool = False, seed: int = 7):
    """Linear working RGB -> final Oklab image.

    ``fast`` skips the expensive spatial stages (used by the exposure solver).
    """
    r = recipe
    ctx = ops.Ctx(full_long=full_long or long_side(pro), seed=seed, an=an)
    step = lambda name, f: progress and progress(name, f)  # noqa: E731
    info: dict = {}

    step("geometry", 0.02)
    if not fast:
        pro, ginfo = geometry.apply_geometry(pro, r["geometry"], an)
        info["geometry"] = ginfo

    step("white balance", 0.12)
    pro = ops.white_balance(pro, r["wb"], an)
    lab = color.to_oklab(pro)
    del pro

    if not fast:
        step("noise reduction", 0.2)
        lab = ops.defringe(lab, float(r["detail"]["defringe"]))
        lab = ops.denoise(lab, float(r["detail"]["nr_luma"]), float(r["detail"]["nr_chroma"]))

    step("exposure & tone", 0.35)
    ev = float(r["exposure"]["ev"])
    lab = ops.exposure(lab, ev)
    lab = ops.filmic(lab, r["tone"], ev)
    lab = ops.local_tone(lab, r["tone"])

    if not fast:
        step("presence", 0.5)
        lab = ops.presence(lab, r["presence"], ctx)

    step("colour", 0.6)
    lab = ops.color_ops(lab, r["color"])
    if not fast:
        step("local adjustments", 0.68)
        lab = ops.local_adjust(lab, r["local"], ctx)
    step("grade", 0.74)
    lab = ops.grade(lab, r["color"]["grade"])
    lab = ops.black_and_white(lab, r["color"]["bw"])
    lab = ops.curve_and_fade(lab, r["tone"])
    lab = ops.desaturate_extremes(lab, r["tone"])

    if not fast:
        step("effects", 0.82)
        lab = ops.effects(lab, r["effects"], ctx)
        step("sharpen", 0.9)
        lab = ops.sharpen(lab, r["detail"], ctx)
    return lab, info


def to_display(lab: np.ndarray, space: str = "srgb") -> np.ndarray:
    """Oklab -> encoded display RGB float [0, 1]."""
    lab = lab.copy()
    lab[..., 0] = _soft_limit(lab[..., 0])
    return color.pro_to_display(color.from_oklab(lab), space)


def quantize8(enc: np.ndarray, seed: int = 1) -> np.ndarray:
    """Float -> uint8 with triangular dither (prevents banding in skies/gradients)."""
    rng = np.random.default_rng(seed)
    h, w = enc.shape[:2]
    n = (rng.random((h, w, 1), dtype=np.float32) + rng.random((h, w, 1), dtype=np.float32) - 1.0)
    return np.clip(enc * 255.0 + n, 0, 255).astype(np.uint8)


def quantize16(enc: np.ndarray) -> np.ndarray:
    return np.clip(enc * 65535.0 + 0.5, 0, 65535).astype(np.uint16)


# --------------------------------------------------------------------------
# exposure solver
# --------------------------------------------------------------------------
def _tonal_stats(lab0: np.ndarray, recipe: dict) -> dict:
    """Display-lightness statistics after exposure + tone (no spatial stages)."""
    ev = float(recipe["exposure"]["ev"])
    lab = ops.exposure(lab0, ev)
    lab = ops.filmic(lab, recipe["tone"], ev)
    lab = ops.local_tone(lab, recipe["tone"])
    lab = ops.curve_and_fade(lab, recipe["tone"])
    L = _soft_limit(lab[..., 0])
    p = np.percentile(L, [0.5, 2, 10, 25, 50, 75, 90, 99, 99.5])
    return {
        "p0.5": float(p[0]), "p2": float(p[1]), "p10": float(p[2]), "p25": float(p[3]), "p50": float(p[4]),
        "p75": float(p[5]), "p90": float(p[6]), "p99": float(p[7]), "p99.5": float(p[8]),
        "clip": float((L > 0.985).mean()),
        "key": float(0.25 * p[3] + 0.5 * p[4] + 0.25 * p[5]),
    }


def solve_tone(pro: np.ndarray, recipe: dict, targets: dict, an: Analysis, log: list | None = None) -> dict:
    """Pick exposure / highlight / shadow / black-point so the image lands on the
    style's tonal targets (the 'expose for the highlights, lift the shadows' routine)."""
    r = recipe
    proxy = resize_long(pro, 360)
    proxy = ops.white_balance(proxy, r["wb"], an)
    lab0 = color.to_oklab(proxy)
    note = (lambda s: log.append(s)) if log is not None else (lambda s: None)

    keep = float(targets.get("preserve_key", 0.25))
    if an.night:
        keep = max(keep, 0.7)
    cur = _tonal_stats(lab0, r)
    target_key = float(targets["median"]) * (1 - keep) + cur["key"] * keep
    ev_lo, ev_hi = (-3.0, 3.0) if an.is_raw else (-1.5, 1.5)
    base_ev = float(r["exposure"]["ev"])

    lo, hi = ev_lo, ev_hi
    for _ in range(12):
        mid = (lo + hi) / 2
        r["exposure"]["ev"] = base_ev + mid
        if _tonal_stats(lab0, r)["key"] < target_key:
            lo = mid
        else:
            hi = mid
    r["exposure"]["ev"] = base_ev + (lo + hi) / 2
    st = _tonal_stats(lab0, r)
    note(f"exposure {r['exposure']['ev']:+.2f} EV to reach tonal key {target_key:.2f}")

    # protect highlights: first recover locally, then give back some exposure
    max_clip = float(targets.get("max_clip", 0.004))
    hi_target = float(targets.get("hi", 0.96))
    hl0 = r["tone"]["highlights"]
    floor_hl = hl0 - (70.0 if an.is_raw else 45.0)
    for _ in range(8):
        if st["clip"] <= max_clip and st["p99.5"] <= hi_target + 0.02:
            break
        if r["tone"]["highlights"] > floor_hl:
            r["tone"]["highlights"] -= 12
        elif r["exposure"]["ev"] > base_ev + ev_lo * 0.5 and r["exposure"]["ev"] > base_ev - 0.8:
            r["exposure"]["ev"] -= 0.12
        else:
            break
        st = _tonal_stats(lab0, r)
    if r["tone"]["highlights"] != hl0:
        note(f"highlights {r['tone']['highlights']:+.0f} to hold {100 * st['clip']:.2f}% clipping")

    # open the shadows if the image sinks into black more than the style wants
    lo_t = float(targets.get("lo", 0.06))
    sh0 = r["tone"]["shadows"]
    cap = sh0 + (60.0 if an.is_raw else 35.0)
    if targets.get("lift_shadows", True):
        for _ in range(6):
            if st["p10"] >= lo_t * 2.2 or r["tone"]["shadows"] >= cap:
                break
            r["tone"]["shadows"] += 12
            st = _tonal_stats(lab0, r)
        if r["tone"]["shadows"] != sh0:
            note(f"shadows {r['tone']['shadows']:+.0f} to open detail")

    # set the black point (auto-levels) unless the style is intentionally matte
    floor = float(targets.get("black", 0.02))
    if r["tone"]["fade"] <= 0.001 and targets.get("auto_black", True):
        bp = max(0.0, st["p0.5"] - floor)
        bp = min(bp, 0.12)
        if bp > 0.004:
            r["tone"]["black_point"] = float(r["tone"]["black_point"]) + bp * 0.9
            note(f"black point {r['tone']['black_point']:.3f}")
    return r


def estimate_scene_contrast(an: Analysis) -> float:
    """-1 flat .. +1 very contrasty, from the measured dynamic range."""
    return float(np.clip((an.dr_stops - 8.5) / 4.0, -1, 1))
