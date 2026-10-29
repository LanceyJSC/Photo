"""Edge-aware filtering building blocks.

Everything is parameterised by *fractions of the image's long side* so a recipe
renders identically on a 1200 px preview and a 45 MP export.
"""
from __future__ import annotations

import cv2
import numpy as np


def long_side(img: np.ndarray) -> int:
    return max(img.shape[0], img.shape[1])


def frac_px(img: np.ndarray, frac: float, minimum: float = 0.5) -> float:
    return max(minimum, frac * long_side(img))


def gaussian(img: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur; for large sigma blur a downscaled copy (much faster, same look)."""
    if sigma <= 0.3:
        return img
    if sigma > 12:
        s = min(8.0, sigma / 6.0)
        h, w = img.shape[:2]
        small = cv2.resize(img, (max(1, int(w / s)), max(1, int(h / s))), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), sigma / s, borderType=cv2.BORDER_REFLECT)
        out = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
        return out.reshape(img.shape) if out.shape != img.shape else out
    return cv2.GaussianBlur(img, (0, 0), sigma, borderType=cv2.BORDER_REFLECT)


def _box(img: np.ndarray, r: int) -> np.ndarray:
    k = 2 * r + 1
    return cv2.boxFilter(img, -1, (k, k), borderType=cv2.BORDER_REFLECT)


def guided_filter(guide: np.ndarray, src: np.ndarray, radius_frac: float, eps: float,
                  max_dim: int = 900) -> np.ndarray:
    """Fast guided filter (He & Sun) with a single-channel guide.

    The linear coefficients are solved at reduced resolution and applied to the
    full-resolution guide, so edges stay crisp while cost is independent of
    image size.  ``src`` may be 2-D or HxWxC.
    """
    h, w = guide.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        sw, sh = max(2, int(w * scale)), max(2, int(h * scale))
        g = cv2.resize(guide, (sw, sh), interpolation=cv2.INTER_AREA)
        p = cv2.resize(src, (sw, sh), interpolation=cv2.INTER_AREA)
    else:
        g, p = guide, src
    r = max(1, int(round(radius_frac * max(g.shape[:2]))))
    mean_g = _box(g, r)
    var_g = _box(g * g, r) - mean_g * mean_g
    chans = [p] if p.ndim == 2 else [p[..., c] for c in range(p.shape[2])]
    A, B = [], []
    for ch in chans:
        mean_p = _box(ch, r)
        cov = _box(g * ch, r) - mean_g * mean_p
        a = cov / (var_g + eps)
        b = mean_p - a * mean_g
        A.append(_box(a, r))
        B.append(_box(b, r))
    if scale < 1.0:
        A = [cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR) for a in A]
        B = [cv2.resize(b, (w, h), interpolation=cv2.INTER_LINEAR) for b in B]
    out = [a * guide + b for a, b in zip(A, B)]
    return out[0] if p.ndim == 2 else np.stack(out, axis=-1)


def edge_aware_base(L: np.ndarray, radius_frac: float, edge_eps: float = 0.01) -> np.ndarray:
    """Large-scale luminance layer that does not bleed across strong edges."""
    return guided_filter(L, L, radius_frac, edge_eps * edge_eps)


def local_contrast_layers(L: np.ndarray, sigma_frac: float, edge_eps: float) -> np.ndarray:
    """Detail layer = L - edge-aware blur at the requested scale."""
    return L - guided_filter(L, L, sigma_frac, edge_eps * edge_eps)


def unsharp_detail(L: np.ndarray, sigma_px: float) -> np.ndarray:
    return L - gaussian(L, sigma_px)


def resize_long(img: np.ndarray, target: int) -> np.ndarray:
    h, w = img.shape[:2]
    s = target / max(h, w)
    if s >= 1:
        return img
    interp = cv2.INTER_AREA
    return cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=interp)


def soft_light_mask(L: np.ndarray, lo: float, hi: float, feather: float = 0.15) -> np.ndarray:
    """Smooth luminosity mask selecting L in [lo, hi]."""
    from .color import smoothstep
    return smoothstep(lo - feather, lo + feather, L) * (1 - smoothstep(hi - feather, hi + feather, L))
