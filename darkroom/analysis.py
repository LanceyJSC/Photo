"""Scene analysis: what a human editor takes in before touching a slider.

All measurements run on a small proxy (plus a full-resolution crop for noise).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import color
from .filters import resize_long, gaussian

_CASCADE = None


@dataclass
class Analysis:
    # luminance distribution, linear Y
    y_pct: dict = field(default_factory=dict)
    # Oklab lightness distribution
    l_pct: dict = field(default_factory=dict)
    dr_stops: float = 8.0               # p99.5 / p0.5 in stops
    clip_hi: float = 0.0                # fraction of pixels at sensor white
    near_black: float = 0.0             # fraction of pixels below ~ -7 EV
    mean_chroma: float = 0.0
    chroma_p90: float = 0.0
    is_mono: bool = False
    cast_ab: tuple = (0.0, 0.0)         # Oklab a,b of neutral-ish pixels
    cast_confidence: float = 0.0
    wb_suggest: tuple = (0.0, 0.0)      # (mired shift, tint) that would neutralise the cast
    noise_sigma: float = 0.0            # Oklab-L units at full resolution
    sky_frac: float = 0.0
    sky_mask: np.ndarray | None = None  # proxy-sized float mask
    faces: list = field(default_factory=list)    # [(x, y, w, h)] fractions of the frame
    skin_frac: float = 0.0
    edge_density: float = 0.0
    dominant_hues: list = field(default_factory=list)
    backlit: bool = False
    night: bool = False
    is_raw: bool = True
    width: int = 0
    height: int = 0

    @property
    def median_l(self) -> float:
        return self.l_pct.get(50, 0.5)

    def summary(self) -> dict:
        return {
            "dynamic_range_stops": round(self.dr_stops, 1),
            "median_lightness": round(self.median_l, 3),
            "clipped_highlights_pct": round(100 * self.clip_hi, 2),
            "noise_sigma": round(self.noise_sigma, 4),
            "color_cast": {"mired": round(self.wb_suggest[0], 1), "tint": round(self.wb_suggest[1], 1),
                           "confidence": round(self.cast_confidence, 2)},
            "mean_chroma": round(self.mean_chroma, 3),
            "sky_pct": round(100 * self.sky_frac, 1),
            "faces": len(self.faces),
            "skin_pct": round(100 * self.skin_frac, 1),
            "monochrome": self.is_mono,
            "backlit": self.backlit,
            "night": self.night,
        }


# --- white balance calibration --------------------------------------------
_WB_JAC = None


def _wb_jacobian() -> np.ndarray:
    """d(a,b)/d(mired, tint) for a mid-grey, measured numerically so the white
    balance solver is exact for our own temperature/tint model."""
    global _WB_JAC
    if _WB_JAC is None:
        grey = np.full((1, 1, 3), 0.25, np.float32)

        def ab(m, t):
            lab = color.to_oklab(color.mat(grey, color.white_shift_matrix(m, t)))
            return np.array([lab[0, 0, 1], lab[0, 0, 2]])
        base = ab(0, 0)
        j = np.stack([(ab(15, 0) - base) / 15, (ab(0, 15) - base) / 15], axis=1)
        _WB_JAC = j
    return _WB_JAC


def solve_wb(cast_ab) -> tuple[float, float]:
    """(mired, tint) that moves a neutral currently at ``cast_ab`` back to a=b=0."""
    j = _wb_jacobian()
    sol = np.linalg.solve(j, -np.asarray(cast_ab, dtype=np.float64))
    return float(sol[0]), float(sol[1])


# --- noise ----------------------------------------------------------------
def estimate_noise(L: np.ndarray, block: int = 24) -> float:
    """Noise sigma of the L channel, measured on the flattest blocks (Immerkaer
    operator, robust to texture by only trusting the quietest quartile)."""
    h, w = L.shape
    if h < 64 or w < 64:
        return 0.0
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float32)
    r = cv2.filter2D(L, -1, k, borderType=cv2.BORDER_REFLECT)
    r = np.abs(r[1:-1, 1:-1])
    hh, ww = (r.shape[0] // block) * block, (r.shape[1] // block) * block
    if hh == 0 or ww == 0:
        return 0.0
    tiles = r[:hh, :ww].reshape(hh // block, block, ww // block, block).mean(axis=(1, 3)).ravel()
    flat = np.percentile(tiles, 20)
    # Immerkaer: sigma = sqrt(pi/2) * mean|I*N| / 6
    return float(math.sqrt(math.pi / 2) * flat / 6.0)


# --- sky ------------------------------------------------------------------
def _sky_mask(lab: np.ndarray) -> tuple[np.ndarray, float]:
    h, w = lab.shape[:2]
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    chroma = np.hypot(a, b)
    hue = np.degrees(np.arctan2(b, a)) % 360
    gy = cv2.Sobel(gaussian(L, 1.5), cv2.CV_32F, 0, 1)
    gx = cv2.Sobel(gaussian(L, 1.5), cv2.CV_32F, 1, 0)
    grad = np.hypot(gx, gy)
    smooth = grad < 0.045
    blue = (hue > 205) & (hue < 285) & (chroma > 0.025) & (L > 0.45)
    overcast = (L > 0.72) & (chroma < 0.04)
    cand = (smooth & (blue | overcast)).astype(np.uint8)
    # restrict to the upper two thirds and connected-to-top components
    cand[int(h * 0.7):] = 0
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(cand, connectivity=4)
    keep = np.zeros_like(cand)
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        if y <= h * 0.04 and area > 0.01 * h * w:
            keep[labels == i] = 1
    frac = float(keep.mean())
    if frac < 0.04:
        return np.zeros((h, w), np.float32), 0.0
    m = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), max(2, w / 150))
    return np.clip(m * 1.15, 0, 1), frac


# --- faces ----------------------------------------------------------------
def _cascade():
    global _CASCADE
    if _CASCADE is None:
        path = Path(__file__).parent / "data" / "haarcascade_frontalface_alt2.xml"
        c = cv2.CascadeClassifier(str(path)) if path.exists() else None
        _CASCADE = c if c is not None and not c.empty() else False
    return _CASCADE


def _faces(L: np.ndarray) -> list:
    c = _cascade()
    if not c:
        return []
    h, w = L.shape
    g = np.clip(L * 255, 0, 255).astype(np.uint8)
    g = cv2.equalizeHist(g)
    found = c.detectMultiScale(g, scaleFactor=1.1, minNeighbors=5, minSize=(max(28, w // 22),) * 2)
    return [(x / w, y / h, fw / w, fh / h) for x, y, fw, fh in found]


def _skin_fraction(lab: np.ndarray) -> float:
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    hue = np.degrees(np.arctan2(b, a)) % 360
    chroma = np.hypot(a, b)
    skin = (hue > 20) & (hue < 65) & (chroma > 0.03) & (chroma < 0.16) & (L > 0.35) & (L < 0.92)
    return float(skin.mean())


# --- main -----------------------------------------------------------------
def analyze(rgb: np.ndarray, is_raw: bool = True, proxy: int = 640) -> Analysis:
    H, W = rgb.shape[:2]
    an = Analysis(is_raw=is_raw, width=W, height=H)
    small = resize_long(rgb, proxy)
    Y = color.luminance(small)
    lab = color.to_oklab(small)
    L = lab[..., 0]

    qs = (0.5, 2, 10, 25, 50, 75, 90, 98, 99.5)
    yv = np.percentile(Y, qs)
    lv = np.percentile(L, qs)
    an.y_pct = {q: float(v) for q, v in zip(qs, yv)}
    an.l_pct = {q: float(v) for q, v in zip(qs, lv)}
    an.dr_stops = float(np.log2(max(an.y_pct[99.5], 1e-4) / max(an.y_pct[0.5], 1e-5)))
    an.clip_hi = float((small.max(axis=2) >= 0.995).mean())
    an.near_black = float((Y < 0.0078).mean())

    chroma = np.hypot(lab[..., 1], lab[..., 2])
    an.mean_chroma = float(chroma.mean())
    an.chroma_p90 = float(np.percentile(chroma, 90))
    an.is_mono = an.chroma_p90 < 0.012

    # colour cast from neutral-ish mid-tone pixels
    sel = (chroma < 0.035) & (L > 0.35) & (L < 0.92)
    frac = float(sel.mean())
    if sel.sum() > 200:
        ab = (float(np.median(lab[..., 1][sel])), float(np.median(lab[..., 2][sel])))
        spread = float(np.hypot(np.std(lab[..., 1][sel]), np.std(lab[..., 2][sel])))
        an.cast_ab = ab
        mag = float(np.hypot(*ab))
        # a large offset is far more likely to be the scene's own colour than a cast
        an.cast_confidence = float(np.clip(frac * 5, 0, 1) * np.clip(1 - spread / 0.05, 0, 1) *
                                   np.clip(1 - (mag - 0.008) / 0.02, 0.05, 1))
        an.wb_suggest = solve_wb(ab)

    # noise measured at full resolution on a central crop
    ch, cw = min(H, 1024), min(W, 1024)
    y0, x0 = (H - ch) // 2, (W - cw) // 2
    crop = rgb[y0:y0 + ch, x0:x0 + cw]
    an.noise_sigma = estimate_noise(color.to_oklab(crop)[..., 0])

    an.sky_mask, an.sky_frac = _sky_mask(lab)
    an.faces = _faces(L)
    an.skin_frac = _skin_fraction(lab)

    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(L, cv2.CV_32F, 0, 1)
    an.edge_density = float((np.hypot(gx, gy) > 0.15).mean())

    hue = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    strong = chroma > 0.05
    if strong.sum() > 100:
        hist, _ = np.histogram(hue[strong], bins=12, range=(0, 360))
        an.dominant_hues = [int(i * 30 + 15) for i in np.argsort(hist)[::-1][:3] if hist[i] > 0.1 * hist.max()]

    # backlit: dark centre/bottom with bright top or very high contrast pair of modes
    top, bot = L[: L.shape[0] // 3], L[2 * L.shape[0] // 3:]
    an.backlit = bool(an.dr_stops > 10 and an.clip_hi > 0.03 and np.median(bot) < 0.45 and np.median(top) > np.median(bot) + 0.2)
    an.night = bool(an.y_pct[50] < 0.012 and an.y_pct[99.5] > 8 * an.y_pct[50])
    return an
