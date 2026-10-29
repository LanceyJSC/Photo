"""Geometry: horizon levelling, vertical/horizontal perspective correction ("upright"),
manual rotation and crop."""
from __future__ import annotations

import math

import cv2
import numpy as np

from . import color
from .filters import resize_long


def _segments(gray: np.ndarray, min_len_frac: float = 0.05) -> np.ndarray:
    """Line segments (x1, y1, x2, y2) via LSD, falling back to probabilistic Hough."""
    h, w = gray.shape
    g8 = np.clip(gray * 255, 0, 255).astype(np.uint8)
    g8 = cv2.GaussianBlur(g8, (0, 0), 1.0)
    segs = None
    try:
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
        out = lsd.detect(g8)[0]
        if out is not None:
            segs = out.reshape(-1, 4)
    except Exception:
        segs = None
    if segs is None:
        edges = cv2.Canny(g8, 60, 160)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 360, 80, minLineLength=int(min_len_frac * max(h, w)), maxLineGap=6)
        segs = lines.reshape(-1, 4).astype(np.float32) if lines is not None else np.zeros((0, 4), np.float32)
    length = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    return segs[length >= min_len_frac * max(h, w)]


def _weighted_median(vals: np.ndarray, weights: np.ndarray) -> float:
    o = np.argsort(vals)
    v, w = vals[o], weights[o]
    c = np.cumsum(w)
    return float(v[np.searchsorted(c, c[-1] / 2)])


def _robust_line_fit(x: np.ndarray, y: np.ndarray, w: np.ndarray, iters: int = 4):
    """Weighted least squares y = s*x + r with iterative reweighting (Huber-like)."""
    ww = w.copy()
    s = r = 0.0
    for _ in range(iters):
        sw = ww.sum()
        mx, my = (ww * x).sum() / sw, (ww * y).sum() / sw
        var = (ww * (x - mx) ** 2).sum()
        s = (ww * (x - mx) * (y - my)).sum() / var if var > 1e-12 else 0.0
        r = my - s * mx
        res = np.abs(y - (s * x + r))
        scale = max(np.median(res) * 1.4826, 1e-4)
        ww = w / (1 + (res / (2 * scale)) ** 2)
    res = np.abs(y - (s * x + r))
    return s, r, float(np.median(res))


def estimate_upright(rgb: np.ndarray, vertical: bool = True, horizontal: bool = False,
                     max_rot: float = 7.0, max_key: float = 0.30, min_len_frac: float = 0.05):
    """Return a dict {rot_deg, vkey, hkey, confidence, n_v, n_h}.

    Vertical lines follow ``x = x0 + m*y`` and are made parallel by
    ``x' = x / (1 + k*y)`` (k = slope of m against x0), then rotated by the
    residual.  All coordinates are in pixels relative to the image centre.
    """
    small = resize_long(rgb, 1400)
    h, w = small.shape[:2]
    Y = color.luminance(small)
    gray = np.sqrt(np.clip(Y, 0, 1))
    segs = _segments(gray, min_len_frac)
    res = {"rot": 0.0, "vkey": 0.0, "hkey": 0.0, "confidence": 0.0, "n_v": 0, "n_h": 0, "scale": 1.0}
    if len(segs) < 6:
        return res
    cx, cy = w / 2, h / 2
    x1, y1, x2, y2 = segs.T
    dx, dy = x2 - x1, y2 - y1
    flip = dy < 0
    dx, dy = np.where(flip, -dx, dx), np.where(flip, -dy, dy)
    length = np.hypot(dx, dy)
    mx, my = (x1 + x2) / 2 - cx, (y1 + y2) / 2 - cy

    # near-vertical family: m = dx/dy
    with np.errstate(divide="ignore", invalid="ignore"):
        m = dx / dy
    vsel = (np.abs(np.arctan(m)) < math.radians(14)) & (dy > 0)
    out = {}
    if vertical and vsel.sum() >= 6:
        mv, xv, wv = m[vsel], mx[vsel], length[vsel] ** 1.5
        s, r, spread = _robust_line_fit(xv, mv, wv)
        # keystone: m = s*x + r.  Only trust it if explained variance is real.
        res["n_v"] = int(vsel.sum())
        out["v"] = (s, r, spread)
    # near-horizontal family: n = dy/dx
    with np.errstate(divide="ignore", invalid="ignore"):
        n = dy / np.where(np.abs(dx) < 1e-6, 1e-6, dx)
    hsel = (np.abs(np.arctan(n)) < math.radians(14)) & (np.abs(dx) > 0)
    if hsel.sum() >= 4:
        res["n_h"] = int(hsel.sum())
        if horizontal and hsel.sum() >= 6:
            s, r, spread = _robust_line_fit(my[hsel], n[hsel], length[hsel] ** 1.5)
            out["h"] = (s, r, spread)
        out["h_rot"] = _weighted_median(n[hsel], length[hsel] ** 2)

    # rotation: prefer the vertical family; blend with horizontals when they agree
    rot_candidates = []
    conf = 0.0
    if "v" in out:
        s, r, spread = out["v"]
        res["vkey"] = float(np.clip(s * h, -max_key, max_key) / h)
        rot_v = r
        rot_candidates.append(("v", math.degrees(math.atan(rot_v)), spread))
        conf = max(conf, float(np.clip(1 - spread / 0.02, 0, 1)) * float(np.clip(res["n_v"] / 25, 0.2, 1)))
    if "h_rot" in out:
        rot_candidates.append(("h", -math.degrees(math.atan(out["h_rot"])), 0.01))
    if "v" in out and "h_rot" in out:
        rv = rot_candidates[0][1]
        rh = rot_candidates[1][1]
        # if verticals and horizontals disagree strongly this is perspective, not tilt;
        # trust verticals (architecture) but reduce confidence if they point in opposite directions
        if abs(rv - rh) > 2.5:
            conf *= 0.7
    if rot_candidates:
        res["rot"] = float(rot_candidates[0][1])
    if "h" in out:
        res["hkey"] = float(out["h"][0])
    res["confidence"] = conf
    res["scale"] = 1400 / max(rgb.shape[:2]) if max(rgb.shape[:2]) > 1400 else 1.0
    return res


def _build_homography(w: int, h: int, rot_deg: float, vkey: float, hkey: float) -> np.ndarray:
    """Centre-referenced homography: vertical keystone, horizontal keystone, rotation."""
    T = np.array([[1, 0, -w / 2], [0, 1, -h / 2], [0, 0, 1]], np.float64)
    Ti = np.linalg.inv(T)
    Hk = np.array([[1, 0, 0], [0, 1, 0], [hkey, vkey, 1]], np.float64)
    # x' = x/(1+vkey*y+hkey*x)  (homogeneous divide)
    th = math.radians(rot_deg)
    c, s = math.cos(th), math.sin(th)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)
    return Ti @ R @ Hk @ T


def _inscribed_crop(H: np.ndarray, w: int, h: int, margin: float = 0.0):
    """Largest centred, original-aspect rectangle that stays inside the warped frame."""
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float64)
    pts = cv2.perspectiveTransform(corners[None], H)[0].astype(np.float32)
    hull = cv2.convexHull(pts)
    cx, cy = w / 2, h / 2

    def inside(s: float) -> bool:
        r = np.array([[cx - s * w / 2, cy - s * h / 2], [cx + s * w / 2, cy - s * h / 2],
                      [cx + s * w / 2, cy + s * h / 2], [cx - s * w / 2, cy + s * h / 2]], np.float32)
        return all(cv2.pointPolygonTest(hull, (float(px), float(py)), False) >= 0 for px, py in r)

    lo, hi = 0.3, 1.0
    if inside(hi):
        return (0, 0, w, h)
    for _ in range(18):
        mid = (lo + hi) / 2
        if inside(mid):
            lo = mid
        else:
            hi = mid
    s = lo * (1 - margin)
    x0, y0 = int(math.ceil(cx - s * w / 2)), int(math.ceil(cy - s * h / 2))
    return (x0, y0, int(s * w) - 1, int(s * h) - 1)


def warp(pro: np.ndarray, rot_deg: float, vkey_px: float, hkey_px: float):
    """Apply rotation + keystone (keys given in 1/px at the *image's* resolution)."""
    h, w = pro.shape[:2]
    H = _build_homography(w, h, rot_deg, vkey_px, hkey_px)
    out = cv2.warpPerspective(pro, H, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    x, y, cw, ch = _inscribed_crop(H, w, h)
    return out[y:y + ch, x:x + cw]


def apply_geometry(pro: np.ndarray, g: dict, an=None) -> tuple[np.ndarray, dict]:
    """Run geometry stage; returns (image, info)."""
    info = {}
    up = float(g.get("auto_upright", 0.0))
    hz = float(g.get("auto_horizon", 0.0))
    rot = float(g.get("rotate", 0.0))
    vkey = hkey = 0.0
    if up > 0 or hz > 0:
        est = estimate_upright(pro, vertical=up > 0, horizontal=up > 0)
        info["upright"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in est.items()}
        conf = est["confidence"]
        if up > 0 and conf > 0.25:
            rot += up * float(np.clip(est["rot"], -7, 7)) * min(1.0, conf * 1.4)
            sc = est["scale"]
            vkey = up * est["vkey"] * sc * min(1.0, conf * 1.4)
            hkey = up * est["hkey"] * sc * min(1.0, conf * 1.4) * 0.7
    if hz > 0 and up <= 0:
        small = resize_long(pro, 1400)
        segs = _segments(np.sqrt(np.clip(color.luminance(small), 0, 1)), min_len_frac=0.08)
        if len(segs):
            dx, dy = segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1]
            ang = np.degrees(np.arctan2(dy, dx))
            ang = np.where(ang > 90, ang - 180, np.where(ang < -90, ang + 180, ang))
            length = np.hypot(dx, dy)
            sel = np.abs(ang) < 6
            # need real evidence: long near-horizontal edges that agree with each other
            if length[sel].sum() >= 0.35 * max(small.shape[:2]):
                med = _weighted_median(ang[sel], length[sel] ** 2)
                spread = float(np.average(np.abs(ang[sel] - med), weights=length[sel]))
                if spread < 1.2:
                    info["horizon_deg"] = round(med, 3)
                    rot += hz * float(np.clip(-med, -5, 5))
    if abs(rot) > 0.02 or abs(vkey) > 1e-7 or abs(hkey) > 1e-7:
        pro = warp(pro, rot, vkey, hkey)
        info["applied"] = {"rot": round(rot, 3), "vkey": vkey, "hkey": hkey}
    crop = g.get("crop")
    if crop:
        l, t, r, b = [float(v) for v in crop]
        h, w = pro.shape[:2]
        pro = pro[int(t * h):max(int(t * h) + 8, int(b * h)), int(l * w):max(int(l * w) + 8, int(r * w))]
    return pro, info
