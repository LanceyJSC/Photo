"""Individual develop / grade operations.

Conventions
-----------
* Scene-referred stages take and return linear working RGB ("pro").
* Creative stages take and return an Oklab image ``lab`` (HxWx3, L,a,b).
* Pixel-scale parameters are expressed at *full resolution* and rescaled with
  ``ctx.scale`` so previews and exports match.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from . import color
from .color import smoothstep
from .curves import apply_lut, apply_points, filmic_curve, monotone_spline
from .filters import gaussian, guided_filter, long_side, resize_long

PIVOT_IN = 0.565  # Oklab L of 18 % grey


@dataclass
class Ctx:
    full_long: int
    seed: int = 7
    an: object = None
    cache: dict = field(default_factory=dict)

    def scale(self, img: np.ndarray) -> float:
        return long_side(img) / max(1, self.full_long)


# =========================================================================
# scene-referred
# =========================================================================
def white_balance(pro: np.ndarray, wb: dict, an) -> np.ndarray:
    m, t = float(wb["mired"]), float(wb["tint"])
    if wb.get("auto", 0) > 0 and an is not None:
        am, at = an.wb_suggest
        k = float(wb["auto"]) * float(an.cast_confidence)
        mx = float(wb.get("auto_max_mired", 60))
        m += float(np.clip(am * k, -mx, mx))
        t += float(np.clip(at * k, -25, 25))
    if abs(m) < 0.05 and abs(t) < 0.05:
        return pro
    return color.mat(pro, color.white_shift_matrix(m, t))


def defringe(lab: np.ndarray, amount: float) -> np.ndarray:
    """Suppress purple/green chromatic-aberration fringes along high-contrast edges."""
    if amount <= 0:
        return lab
    L = lab[..., 0]
    a, b = lab[..., 1], lab[..., 2]
    hue = np.arctan2(b, a)
    chroma = np.hypot(a, b)
    # purple/magenta (~300-345 deg) and green-cyan fringes (~150-200 deg)
    deg = np.degrees(hue) % 360
    fringe_hue = ((deg > 285) & (deg < 350)) | ((deg > 140) & (deg < 200))
    grad = cv2.Sobel(L, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(L, cv2.CV_32F, 0, 1) ** 2
    edge = cv2.dilate(np.sqrt(grad), np.ones((5, 5), np.uint8))
    near_edge = smoothstep(0.08, 0.3, edge)
    bright_near = smoothstep(0.6, 0.95, cv2.dilate(L, np.ones((7, 7), np.uint8)))
    w = near_edge * bright_near * fringe_hue * smoothstep(0.02, 0.07, chroma) * amount
    w = gaussian(w.astype(np.float32), 1.0)
    lab = lab.copy()
    lab[..., 1] *= 1 - w
    lab[..., 2] *= 1 - w
    return lab


# ---------------------------------------------------------------- denoise
def _tile_sigma(c: np.ndarray, tile: int = 16) -> float:
    h, w = c.shape
    hh, ww = (h // tile) * tile, (w // tile) * tile
    if hh < tile or ww < tile:
        return float(np.abs(c).mean() / 0.798)
    t = np.abs(c[:hh, :ww]).reshape(hh // tile, tile, ww // tile, tile).mean(axis=(1, 3)).ravel()
    return float(np.percentile(t, 25) / 0.798)


def _pyr_coring(ch: np.ndarray, amount: float, level_gain, levels: int = 5) -> np.ndarray:
    """Wiener-style shrinkage of Laplacian-pyramid bands.  Thresholds are measured
    per band from the image's own flattest tiles, so no ISO tables are needed."""
    gp = [ch]
    for _ in range(levels):
        if min(gp[-1].shape) < 16:
            break
        gp.append(cv2.pyrDown(gp[-1]))
    lp = []
    for i in range(len(gp) - 1):
        up = cv2.pyrUp(gp[i + 1], dstsize=(gp[i].shape[1], gp[i].shape[0]))
        lp.append(gp[i] - up)
    out = gp[-1]
    for i in range(len(lp) - 1, -1, -1):
        band = lp[i]
        sigma = _tile_sigma(band)
        gain = level_gain[min(i, len(level_gain) - 1)]
        t = amount * gain * sigma * 2.0
        if t > 1e-7:
            band = band * (band * band) / (band * band + t * t)
        out = cv2.pyrUp(out, dstsize=(band.shape[1], band.shape[0])) + band
    return out


def denoise(lab: np.ndarray, luma: float, chroma: float) -> np.ndarray:
    if luma <= 0 and chroma <= 0:
        return lab
    lab = lab.copy()
    L = lab[..., 0]
    if luma > 0:
        lab[..., 0] = _pyr_coring(L, luma, [1.0, 0.9, 0.65, 0.4, 0.25])
    if chroma > 0:
        guide = lab[..., 0]
        for c in (1, 2):
            ch = _pyr_coring(lab[..., c], chroma, [2.2, 2.0, 1.6, 1.2, 0.9], levels=6)
            sm = guided_filter(guide, ch, 0.006, (0.03 * (0.4 + chroma)) ** 2)
            lab[..., c] = ch * (1 - 0.7 * chroma) + sm * (0.7 * chroma)
    return lab


# =========================================================================
# tone
# =========================================================================
def exposure(lab: np.ndarray, ev: float) -> np.ndarray:
    if abs(ev) < 1e-4:
        return lab
    return lab * np.float32(2.0 ** (ev / 3.0))


def filmic(lab: np.ndarray, t: dict, ev: float) -> np.ndarray:
    L = lab[..., 0]
    white = max(1.0, 2.0 ** (max(ev, 0.0) / 3.0)) * 1.0
    pts = filmic_curve(PIVOT_IN, float(t["pivot"]), float(t["contrast"]), float(t["toe"]),
                       float(t["shoulder"]), white)
    Lo = apply_points(L, pts)
    ratio = np.clip(Lo / np.maximum(L, 1e-3), 0.25, 3.0)
    follow = float(t["chroma_follow"])
    k = np.power(ratio, follow)
    out = np.empty_like(lab)
    out[..., 0] = Lo
    out[..., 1] = lab[..., 1] * k
    out[..., 2] = lab[..., 2] * k
    return out


def local_tone(lab: np.ndarray, t: dict) -> np.ndarray:
    hl, sh = float(t["highlights"]) / 100, float(t["shadows"]) / 100
    wh, bl = float(t["whites"]) / 100, float(t["blacks"]) / 100
    if not (hl or sh or wh or bl):
        return lab
    L = lab[..., 0]
    out = L.copy()
    if hl or sh:
        base = guided_filter(L, L, 0.035, 0.05 ** 2)
        if hl:
            out += hl * 0.40 * smoothstep(0.42, 0.98, base)
        if sh:
            out += sh * 0.32 * (1 - smoothstep(0.04, 0.68, base))
    if wh:
        out += wh * 0.14 * smoothstep(0.65, 1.0, L)
    if bl:
        out += bl * 0.12 * (1 - smoothstep(0.0, 0.40, L))
    lab = lab.copy()
    chroma_k = np.clip(out / np.maximum(L, 1e-3), 0.3, 2.5)
    chroma_k = np.power(chroma_k, 0.5)
    lab[..., 1] *= chroma_k
    lab[..., 2] *= chroma_k
    lab[..., 0] = np.maximum(out, 0)
    return lab


def curve_and_fade(lab: np.ndarray, t: dict) -> np.ndarray:
    L = lab[..., 0]
    changed = False
    if t.get("curve"):
        L = apply_points(L, [tuple(p) for p in t["curve"]])
        changed = True
    bp = float(t.get("black_point", 0))
    if bp:
        L = np.clip((L - bp) / (1 - bp), 0, None)
        changed = True
    f = float(t.get("fade", 0))
    if f:
        # lift blacks, tapering out by the mid-tones so highlights stay crisp
        L = L + f * (1 - smoothstep(0.0, 0.75, L)) * 1.0
        changed = True
    if not changed:
        return lab
    lab = lab.copy()
    lab[..., 0] = L
    return lab


def desaturate_extremes(lab: np.ndarray, t: dict) -> np.ndarray:
    hd, sd = float(t["highlight_desat"]), float(t["shadow_desat"])
    if not (hd or sd):
        return lab
    L = lab[..., 0]
    k = 1 - hd * smoothstep(0.72, 1.0, L) - sd * (1 - smoothstep(0.0, 0.3, L))
    k = np.clip(k, 0, 1)
    lab = lab.copy()
    lab[..., 1] *= k
    lab[..., 2] *= k
    return lab


# =========================================================================
# presence / local contrast
# =========================================================================
def presence(lab: np.ndarray, p: dict, ctx: Ctx) -> np.ndarray:
    cl, tx = float(p["clarity"]) / 100, float(p["texture"]) / 100
    dh, mc = float(p["dehaze"]) / 100, float(p["micro_contrast"]) / 100
    if not (cl or tx or dh or mc):
        return lab
    lab = lab.copy()
    L = lab[..., 0]
    sc = ctx.scale(L)
    if dh > 0:
        lab = _dehaze(lab, dh)
        L = lab[..., 0]
    if cl:
        base = guided_filter(L, L, 0.012, 0.07 ** 2)
        mid = 1.0 - np.clip(np.abs(L - 0.5) * 1.5, 0, 1) ** 1.6
        L = L + cl * 1.2 * (L - base) * (0.35 + 0.65 * mid)
    if tx:
        sigma = max(0.7, 1.6 * sc * ctx.full_long / 6000.0 * 1.0)
        detail = L - gaussian(L, sigma)
        L = L + tx * 1.0 * detail
    if mc:
        sigma = max(0.6, 0.9 * sc * ctx.full_long / 6000.0)
        detail = L - gaussian(L, sigma)
        edge = smoothstep(0.004, 0.03, np.abs(detail))
        L = L + mc * 1.4 * detail * edge
    lab[..., 0] = L
    return lab


def _dehaze(lab: np.ndarray, amount: float) -> np.ndarray:
    """Dark-channel-prior haze removal with a guided-filter transmission map."""
    rgb = np.clip(color.mat(color.from_oklab(lab), color.PRO_TO_SRGB), 0, 1)
    small = resize_long(rgb, 640)
    dark = cv2.erode(small.min(axis=2), np.ones((9, 9), np.uint8))
    n = max(1, dark.size // 1000)
    idx = np.argpartition(dark.ravel(), -n)[-n:]
    A = np.median(small.reshape(-1, 3)[idx], axis=0)
    A = np.clip(A, 0.5, 1.0)
    norm = small / A
    t = 1 - 0.9 * amount * cv2.erode(norm.min(axis=2), np.ones((9, 9), np.uint8))
    t = cv2.resize(t, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    t = guided_filter(rgb.mean(axis=2), t, 0.02, 1e-3)
    t = np.clip(t, 0.28, 1.0)[..., None]
    out = (rgb - A) / t + A
    out = np.clip(out, 0, None)
    pro = color.mat(out, color.SRGB_TO_PRO)
    res = color.to_oklab(pro)
    # keep original lightness structure partially so skies don't go muddy
    res[..., 0] = res[..., 0] * 0.85 + lab[..., 0] * 0.15
    return res


# =========================================================================
# colour
# =========================================================================
_BAND_HUE_DEG = {  # Oklab hue angle of the band centres
    "red": 29.0, "orange": 55.0, "yellow": 105.0, "green": 142.0,
    "aqua": 195.0, "blue": 264.0, "purple": 305.0, "magenta": 345.0,
}
_BANDS = list(_BAND_HUE_DEG)


def _band_weights(hue_deg: np.ndarray):
    """Triangular partition-of-unity weights between adjacent band centres."""
    centres = np.array([_BAND_HUE_DEG[b] for b in _BANDS], np.float32)
    ext = np.concatenate([centres, [centres[0] + 360]])
    h = np.mod(hue_deg - centres[0], 360) + centres[0]
    idx = np.clip(np.searchsorted(ext, h, side="right") - 1, 0, len(centres) - 1)
    lo, hi = ext[idx], ext[idx + 1]
    w1 = (h - lo) / (hi - lo)
    w1 = w1 * w1 * (3 - 2 * w1)
    return idx, (idx + 1) % len(centres), w1.astype(np.float32)


def skin_weight(h_deg: np.ndarray, chroma: np.ndarray, L: np.ndarray) -> np.ndarray:
    hw = 1 - smoothstep(18, 35, np.abs(h_deg - 48))
    return (hw * smoothstep(0.02, 0.05, chroma) * (1 - smoothstep(0.17, 0.24, chroma)) *
            smoothstep(0.30, 0.5, L)).astype(np.float32)


def color_ops(lab: np.ndarray, c: dict) -> np.ndarray:
    vib, sat = float(c["vibrance"]) / 100, float(c["saturation"]) / 100
    hsl = c["hsl"]
    hsl_active = any(abs(hsl[b][k]) > 1e-6 for b in _BANDS for k in ("h", "s", "l"))
    if not (vib or sat or hsl_active):
        return lab
    lab = lab.copy()
    a, b = lab[..., 1], lab[..., 2]
    L = lab[..., 0]
    C = np.hypot(a, b)
    hdeg = np.degrees(np.arctan2(b, a)) % 360
    k = np.ones_like(C)
    dh = None
    if hsl_active:
        i0, i1, w = _band_weights(hdeg)
        arr = lambda key: np.array([hsl[bn][key] for bn in _BANDS], np.float32)  # noqa: E731
        H, S, Lm = arr("h"), arr("s"), arr("l")
        dh = np.radians((H[i0] * (1 - w) + H[i1] * w) * 30.0)
        k = k * (1 + (S[i0] * (1 - w) + S[i1] * w))
        dl = (Lm[i0] * (1 - w) + Lm[i1] * w) * 0.22 * smoothstep(0.0, 0.07, C)
        L = L + dl
    if vib:
        cmax = 0.30
        weight = np.clip(1 - C / cmax, 0, 1) ** 1.4
        prot = 1 - float(c.get("skin_protect", 0.6)) * skin_weight(hdeg, C, lab[..., 0]) * 0.7
        k = k * (1 + vib * 1.3 * weight * prot) if vib > 0 else k * (1 + vib * (0.3 + 0.7 * (1 - weight)))
    if sat:
        k = k * (1 + sat)
    k = np.clip(k, 0, 4)
    if dh is not None:
        ang = np.arctan2(b, a) + dh
        C2 = C * k
        lab[..., 1], lab[..., 2] = C2 * np.cos(ang), C2 * np.sin(ang)
    else:
        lab[..., 1] = a * k
        lab[..., 2] = b * k
    lab[..., 0] = L
    return lab


def grade(lab: np.ndarray, g: dict) -> np.ndarray:
    """Three-way colour grade (shadows / mids / highlights + global) in Oklab."""
    zones = ("shadows", "mids", "highlights", "global")
    if not any(abs(g[z][k]) > 1e-6 for z in zones for k in ("s", "l")):
        return lab
    lab = lab.copy()
    L = lab[..., 0]
    bal = float(g.get("balance", 0)) * 0.25
    blend = float(np.clip(g.get("blend", 0.5), 0.05, 1.0))
    width = 0.12 + 0.35 * blend
    Lb = L - bal
    sh = 1 - smoothstep(0.30 - width * 0.5, 0.30 + width, Lb)
    hi = smoothstep(0.60 - width, 0.60 + width * 0.5, Lb)
    mid = np.clip(1 - sh - hi, 0, 1)
    da = np.zeros_like(L)
    db = np.zeros_like(L)
    dl = np.zeros_like(L)
    for name, w in (("shadows", sh), ("mids", mid), ("highlights", hi), ("global", 1.0)):
        z = g[name]
        s = float(z["s"])
        if s:
            ang = np.radians(float(z["h"]))
            amt = s * 0.09
            da += w * amt * np.cos(ang)
            db += w * amt * np.sin(ang)
        if z["l"]:
            dl += w * float(z["l"]) * 0.2
    lab[..., 1] += da
    lab[..., 2] += db
    lab[..., 0] = L + dl
    return lab


def black_and_white(lab: np.ndarray, bw: dict) -> np.ndarray:
    amt = float(bw["amount"])
    if amt <= 0:
        return lab
    lab = lab.copy()
    a, b = lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    mix = bw["mix"]
    if any(abs(mix[k]) > 1e-6 for k in _BANDS):
        hdeg = np.degrees(np.arctan2(b, a)) % 360
        i0, i1, w = _band_weights(hdeg)
        M = np.array([mix[bn] for bn in _BANDS], np.float32)
        dl = (M[i0] * (1 - w) + M[i1] * w) * 0.27 * smoothstep(0.0, 0.10, C)
        lab[..., 0] = lab[..., 0] + dl * amt
    k = 1 - amt
    lab[..., 1] = a * k
    lab[..., 2] = b * k
    tone = bw["tone"]
    if tone["s"] or tone.get("s2", 0):
        L = lab[..., 0]
        split = float(tone.get("split", 0.0))
        w_hi = smoothstep(0.35, 0.9, L) if (split or tone.get("s2", 0)) else 0.0
        w_sh = 1 - w_hi if not np.isscalar(w_hi) else 1.0
        for hue, s, w in ((tone["h"], tone["s"], w_sh), (tone.get("h2", tone["h"]), tone.get("s2", 0.0), w_hi)):
            if s:
                ang = np.radians(float(hue))
                lab[..., 1] += amt * float(s) * 0.05 * np.cos(ang) * w
                lab[..., 2] += amt * float(s) * 0.05 * np.sin(ang) * w
    return lab


# =========================================================================
# local adjustments
# =========================================================================
def _refined_mask(mask_small: np.ndarray, L: np.ndarray, ctx: Ctx, key: str) -> np.ndarray:
    if key in ctx.cache and ctx.cache[key].shape == L.shape:
        return ctx.cache[key]
    m = cv2.resize(mask_small, (L.shape[1], L.shape[0]), interpolation=cv2.INTER_LINEAR)
    m = guided_filter(L, m, 0.006, 0.01 ** 2)
    m = np.clip(m, 0, 1).astype(np.float32)
    ctx.cache[key] = m
    return m


def _gain_lab(lab: np.ndarray, ev: float, mask) -> None:
    g = (2.0 ** (ev / 3.0)) - 1.0
    k = (1.0 + g * mask).astype(np.float32)
    lab *= k[..., None]


def local_adjust(lab: np.ndarray, loc: dict, ctx: Ctx) -> np.ndarray:
    an = ctx.an
    sky, gt, gb, subj = loc["sky"], loc["gradient_top"], loc["gradient_bottom"], loc["subject"]
    ss = float(loc.get("skin_smooth", 0))
    active = (any(abs(float(v)) > 1e-6 for v in sky.values()) or gt["exposure"] or gb["exposure"] or
              subj["exposure"] or ss)
    if not active:
        return lab
    lab = lab.copy()
    h, w = lab.shape[:2]
    L = lab[..., 0]
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]

    if any(abs(float(v)) > 1e-6 for v in sky.values()) and an is not None and an.sky_frac > 0:
        m = _refined_mask(an.sky_mask, L, ctx, "sky")
        if sky["exposure"]:
            _gain_lab(lab, float(sky["exposure"]), m)
        a, b = lab[..., 1], lab[..., 2]
        if sky["saturation"]:
            k = 1 + float(sky["saturation"]) * m
            lab[..., 1], lab[..., 2] = a * k, b * k
        if sky["blue_lum"]:
            C = np.hypot(a, b)
            hdeg = np.degrees(np.arctan2(b, a)) % 360
            blue = (1 - smoothstep(25, 55, np.abs(hdeg - 250))) * smoothstep(0.01, 0.06, C)
            lab[..., 0] = lab[..., 0] + float(sky["blue_lum"]) * 0.2 * blue * m
        if sky["warmth"]:
            lab[..., 2] += float(sky["warmth"]) * 0.03 * m
            lab[..., 1] += float(sky["warmth"]) * 0.008 * m

    if gt["exposure"]:
        ext = float(gt["extent"])
        m = (1 - smoothstep(0.0, ext, ys)) * np.ones((1, w), np.float32)
        if an is not None and an.sky_frac > 0.04:   # graduate through sky only if we have one
            m = m * (0.5 + 0.5 * _refined_mask(an.sky_mask, L, ctx, "sky"))
        _gain_lab(lab, float(gt["exposure"]), m)
    if gb["exposure"]:
        m = smoothstep(1 - float(gb["extent"]), 1.0, ys) * np.ones((1, w), np.float32)
        _gain_lab(lab, float(gb["exposure"]), m)

    if subj["exposure"]:
        m = np.zeros((h, w), np.float32)
        faces = an.faces if an is not None else []
        if faces:
            for fx, fy, fw, fh in faces:
                cx, cy = (fx + fw / 2) * w, (fy + fh / 2) * h
                r = max(fw * w, fh * h) * 1.6
                yy, xx = np.ogrid[:h, :w]
                d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
                m = np.maximum(m, np.exp(-d2 * 1.6).astype(np.float32))
        else:
            yy, xx = np.ogrid[:h, :w]
            d2 = ((xx - w / 2) / (w * float(subj["radius"]) * 1.4)) ** 2 + ((yy - h * 0.48) / (h * float(subj["radius"]) * 1.4)) ** 2
            m = np.exp(-d2 * 1.2).astype(np.float32)
        _gain_lab(lab, float(subj["exposure"]), m)

    if ss > 0 and an is not None and an.faces:
        lab = _smooth_skin(lab, an.faces, ss, ctx)
    return lab


def _smooth_skin(lab: np.ndarray, faces, amount: float, ctx: Ctx) -> np.ndarray:
    h, w = lab.shape[:2]
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    hdeg = np.degrees(np.arctan2(b, a)) % 360
    skin = skin_weight(hdeg, C, L)
    region = np.zeros((h, w), np.float32)
    for fx, fy, fw, fh in faces:
        cx, cy = (fx + fw / 2) * w, (fy + fh / 2) * h
        rx, ry = fw * w * 1.15, fh * h * 1.35
        yy, xx = np.ogrid[:h, :w]
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        region = np.maximum(region, (1 - smoothstep(0.6, 1.3, d)).astype(np.float32))
    m = gaussian(skin * region, max(1.0, w / 600.0))
    # frequency separation: keep pores/edges coarse detail, soften blotchy mid-frequency
    sc = max(1.0, ctx.full_long / 6000.0)
    low = guided_filter(L, L, 0.004, 0.025 ** 2)
    L2 = L + (low - L) * m * (0.55 * amount)
    for c in (1, 2):
        ch = lab[..., c]
        ch_s = guided_filter(L, ch, 0.01, 0.03 ** 2)
        lab[..., c] = ch + (ch_s - ch) * m * 0.8 * amount
    lab[..., 0] = L2
    return lab


# =========================================================================
# effects
# =========================================================================
def effects(lab: np.ndarray, e: dict, ctx: Ctx) -> np.ndarray:
    hal, glow = e["halation"], e["glow"]
    if hal["amount"] > 0 or glow["amount"] > 0:
        lab = lab.copy()
        L = lab[..., 0]
        sc = long_side(L)
        if glow["amount"] > 0:
            src = np.clip(L - 0.45, 0, None)
            bl = gaussian(src, float(glow["radius"]) * sc)
            lab[..., 0] = L + float(glow["amount"]) * 0.55 * bl
            L = lab[..., 0]
        if hal["amount"] > 0:
            thr = float(hal["threshold"])
            src = smoothstep(thr - 0.08, thr + 0.06, L) * (0.4 + 0.6 * L)
            bl = gaussian(src.astype(np.float32), float(hal["radius"]) * sc)
            bl2 = gaussian(src.astype(np.float32), float(hal["radius"]) * sc * 3.2)
            glow_m = bl * 0.65 + bl2 * 0.5
            ang = np.radians(float(hal["hue"]))
            amt = float(hal["amount"])
            lab[..., 0] = L + amt * 0.22 * glow_m
            lab[..., 1] += amt * 0.20 * glow_m * np.cos(ang)
            lab[..., 2] += amt * 0.20 * glow_m * np.sin(ang)

    v = e["vignette"]
    if abs(v["amount"]) > 1e-3:
        lab = vignette(lab, v)

    gr = e["grain"]
    if gr["amount"] > 0:
        lab = grain(lab, gr, ctx)
    return lab


def vignette(lab: np.ndarray, v: dict) -> np.ndarray:
    h, w = lab.shape[:2]
    amount = float(v["amount"])
    rnd = float(v.get("roundness", 0.0))
    yy = (np.linspace(-1, 1, h, dtype=np.float32) * (1.0 if rnd >= 0 else 1.0))[:, None]
    xx = (np.linspace(-1, 1, w, dtype=np.float32) * (w / h if rnd > 0 else 1.0))[None, :]
    if rnd > 0:
        xx = xx / (w / h) * (1 - rnd) + xx * rnd
        yy = yy
    d = np.sqrt(xx * xx + yy * yy) / np.sqrt(2.0 if rnd <= 0 else (1 + (1 - rnd + rnd * w / h) ** 2))
    mid = float(v["midpoint"])
    feather = float(np.clip(v["feather"], 0.05, 1.0))
    m = smoothstep(mid - 0.5 * feather * mid - 0.02, mid + feather * (1 - mid) + 0.1, d)
    m = m * m * 0.5 + m * 0.5
    lab = lab.copy()
    if amount > 0:
        k = 1 - 0.75 * amount * m
        lab *= k[..., None] ** np.float32(0.8)
        lab[..., 0] = lab[..., 0] * np.float32(1.0)
    else:
        lab[..., 0] = lab[..., 0] + (-amount) * 0.7 * m * (1 - lab[..., 0])
    return lab


def grain(lab: np.ndarray, g: dict, ctx: Ctx) -> np.ndarray:
    h, w = lab.shape[:2]
    rng = np.random.default_rng(ctx.seed)
    amount = float(g["amount"])
    size = max(0.6, float(g["size"]) * (long_side(lab) / 4000.0) * 1.15)
    gh, gw = max(8, int(h / size)), max(8, int(w / size))
    n = rng.standard_normal((gh, gw)).astype(np.float32)
    rough = float(g["roughness"])
    n = cv2.GaussianBlur(n, (0, 0), 0.6 + 0.8 * (1 - rough))
    n /= max(float(n.std()), 1e-6)
    if (gh, gw) != (h, w):
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC if size < 1.5 else cv2.INTER_LINEAR)
    L = lab[..., 0]
    prof = 0.28 + 0.72 * np.clip(4 * L * (1 - L), 0, 1) ** 0.8
    lab = lab.copy()
    lab[..., 0] = L + amount * 0.055 * n * prof
    cg = float(g.get("chroma", 0.0))
    if cg > 0:
        n2 = cv2.resize(rng.standard_normal((gh, gw)).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        lab[..., 1] += amount * cg * 0.012 * n2
        lab[..., 2] += amount * cg * 0.012 * np.roll(n2, 17, axis=0)
    return lab


# =========================================================================
# output sharpening
# =========================================================================
def sharpen(lab: np.ndarray, d: dict, ctx: Ctx) -> np.ndarray:
    amt = float(d["sharpen"])
    if amt <= 0:
        return lab
    L = lab[..., 0]
    sc = ctx.scale(L)
    radius = float(np.clip(float(d["sharpen_radius"]) * sc ** 0.5, 0.5, 4.0))
    blur = gaussian(L, radius)
    detail = L - blur
    mask_amt = float(d["sharpen_masking"])
    if mask_amt > 0:
        mag = gaussian(np.abs(detail), 1.5)
        edge = smoothstep(0.003, 0.03 + 0.03 * mask_amt, mag)
        edge = (1 - mask_amt) + mask_amt * edge
    else:
        edge = 1.0
    lim = 0.07
    add = np.clip(detail * edge, -lim, lim) * (amt * 1.6)
    lab = lab.copy()
    lab[..., 0] = L + add
    return lab
