"""Colour science primitives.

Working space is linear ProPhoto RGB (D50), float32.  Creative edits happen in
Oklab, which is homogeneous (scaling linear light by g scales L, a, b by g**(1/3))
and has good hue linearity, so exposure, tone and colour moves stay predictable.
"""
from __future__ import annotations

import cv2
import numpy as np

# --- primaries -------------------------------------------------------------
_SRGB_TO_XYZ = np.array(
    [[0.4124564, 0.3575761, 0.1804375],
     [0.2126729, 0.7151522, 0.0721750],
     [0.0193339, 0.1191920, 0.9503041]], dtype=np.float64)
_PROPHOTO_TO_XYZ = np.array(
    [[0.797675, 0.135192, 0.031353],
     [0.288040, 0.711874, 0.000086],
     [0.000000, 0.000000, 0.825210]], dtype=np.float64)

D50 = np.array([0.96422, 1.0, 0.82521])
D65 = np.array([0.95047, 1.0, 1.08883])

_BRADFORD = np.array(
    [[0.8951, 0.2664, -0.1614],
     [-0.7502, 1.7135, 0.0367],
     [0.0389, -0.0685, 1.0296]])


def adapt_matrix(src_white: np.ndarray, dst_white: np.ndarray) -> np.ndarray:
    """Bradford chromatic adaptation matrix (XYZ -> XYZ)."""
    s = _BRADFORD @ src_white
    d = _BRADFORD @ dst_white
    return np.linalg.inv(_BRADFORD) @ np.diag(d / s) @ _BRADFORD


_D50_TO_D65 = adapt_matrix(D50, D65)
_D65_TO_D50 = adapt_matrix(D65, D50)

_OK_M1 = np.array(
    [[0.8189330101, 0.3618667424, -0.1288597137],
     [0.0329845436, 0.9293118715, 0.0361456387],
     [0.0482003018, 0.2643662691, 0.6338517070]])
_OK_M2 = np.array(
    [[0.2104542553, 0.7936177850, -0.0040720468],
     [1.9779984951, -2.4285922050, 0.4505937099],
     [0.0259040371, 0.7827717662, -0.8086757660]])

# working RGB -> LMS (pre-cube-root), and the inverse
PRO_TO_LMS = _OK_M1 @ _D50_TO_D65 @ _PROPHOTO_TO_XYZ
LMS_TO_PRO = np.linalg.inv(PRO_TO_LMS)
OK_M2 = _OK_M2
OK_M2_INV = np.linalg.inv(_OK_M2)

PRO_TO_SRGB = np.linalg.inv(_SRGB_TO_XYZ) @ _D50_TO_D65 @ _PROPHOTO_TO_XYZ
SRGB_TO_PRO = np.linalg.inv(PRO_TO_SRGB)

# adobe rgb (1998) for wide-gamut output
_ADOBE_TO_XYZ = np.array(
    [[0.5767309, 0.1855540, 0.1881852],
     [0.2973769, 0.6273491, 0.0752741],
     [0.0270343, 0.0706872, 0.9911085]])
PRO_TO_ADOBE = np.linalg.inv(_ADOBE_TO_XYZ) @ _D50_TO_D65 @ _PROPHOTO_TO_XYZ

# luminance weights (Y) of the working space
LUMA = _PROPHOTO_TO_XYZ[1].astype(np.float32)
# Rec.709 weights, used for panchromatic B&W maths on sRGB-referred values
LUMA709 = _SRGB_TO_XYZ[1].astype(np.float32)


def mat(img: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Apply a 3x3 matrix to an HxWx3 float32 image."""
    return cv2.transform(np.ascontiguousarray(img, dtype=np.float32), m.astype(np.float32))


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Relative luminance Y of linear working-space RGB."""
    return rgb @ LUMA


# --- transfer functions ----------------------------------------------------
def srgb_encode(lin: np.ndarray) -> np.ndarray:
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055).astype(np.float32)


def srgb_decode(enc: np.ndarray) -> np.ndarray:
    enc = np.asarray(enc, dtype=np.float32)
    return np.where(enc <= 0.04045, enc / 12.92, np.power((enc + 0.055) / 1.055, 2.4)).astype(np.float32)


def gamma_encode(lin: np.ndarray, g: float) -> np.ndarray:
    return np.power(np.clip(lin, 0.0, 1.0), 1.0 / g).astype(np.float32)


# --- Oklab -----------------------------------------------------------------
def to_oklab(pro: np.ndarray) -> np.ndarray:
    """Linear working RGB -> Oklab (L, a, b), float32.  Negative lights are clamped."""
    lms = mat(pro, PRO_TO_LMS)
    np.maximum(lms, 0.0, out=lms)
    np.cbrt(lms, out=lms)
    return mat(lms, OK_M2)


def from_oklab(lab: np.ndarray) -> np.ndarray:
    """Oklab -> linear working RGB (may leave the sRGB gamut, handled at export)."""
    lms = mat(lab, OK_M2_INV)
    np.multiply(lms, lms * lms, out=lms)  # cube
    return mat(lms, LMS_TO_PRO)


def lab_to_lch(lab: np.ndarray):
    a, b = lab[..., 1], lab[..., 2]
    return lab[..., 0], np.hypot(a, b), np.arctan2(b, a)


def lch_to_ab(c: np.ndarray, h: np.ndarray):
    return c * np.cos(h), c * np.sin(h)


def oklab_hue_of_srgb(r: float, g: float, b: float) -> float:
    """Hue angle (radians) in Oklab of a display sRGB colour, for band tables."""
    lin = srgb_decode(np.array([[[r, g, b]]], dtype=np.float32))
    lab = to_oklab(mat(lin, SRGB_TO_PRO))
    return float(np.arctan2(lab[0, 0, 2], lab[0, 0, 1]))


# --- display conversion ----------------------------------------------------
def gamut_compress(rgb: np.ndarray) -> np.ndarray:
    """Pull out-of-gamut colours (negative channels) toward their own luminance
    instead of hard clipping, which would skew hue.  Operates in place on
    linear display RGB (sRGB or AdobeRGB primaries)."""
    mn = rgb.min(axis=2)
    bad = mn < 0
    if bad.any():
        y = rgb @ LUMA709
        y = np.maximum(y, 1e-6)
        t = y / np.maximum(y - mn, 1e-6)
        t = np.where(bad, t, 1.0)[..., None]
        rgb = y[..., None] + (rgb - y[..., None]) * t
    return rgb


def pro_to_display(pro: np.ndarray, space: str = "srgb") -> np.ndarray:
    """Linear working RGB -> encoded display RGB in [0, 1].

    Out-of-gamut colours are compressed toward their luminance (negatives) and
    over-range pixels are scaled by their brightest channel, which preserves hue
    instead of per-channel clipping."""
    if space == "prophoto":
        out = np.clip(pro, 0, 1)
        return np.power(out, 1 / 1.8).astype(np.float32)
    m = PRO_TO_ADOBE if space == "adobe" else PRO_TO_SRGB
    lin = gamut_compress(mat(pro, m))
    mx = lin.max(axis=2, keepdims=True)
    lin = lin / np.maximum(mx, 1.0)
    if space == "adobe":
        return np.power(np.clip(lin, 0, 1), 1 / 2.19921875).astype(np.float32)
    return srgb_encode(lin)


def display_to_pro(enc: np.ndarray) -> np.ndarray:
    """Encoded sRGB (0..1 float) -> linear working RGB."""
    return mat(srgb_decode(enc), SRGB_TO_PRO)


# --- white point / temperature --------------------------------------------
def cct_to_xy(cct: float) -> tuple[float, float]:
    """CIE daylight locus (4000-25000 K) / Planckian approximation below."""
    t = float(cct)
    if t >= 4000:
        if t <= 7000:
            x = -4.6070e9 / t**3 + 2.9678e6 / t**2 + 0.09911e3 / t + 0.244063
        else:
            x = -2.0064e9 / t**3 + 1.9018e6 / t**2 + 0.24748e3 / t + 0.237040
        y = -3.000 * x * x + 2.870 * x - 0.275
    else:  # Kim et al. Planckian approximation 1667-4000 K
        t = max(t, 1667.0)
        x = -0.2661239e9 / t**3 - 0.2343589e6 / t**2 + 0.8776956e3 / t + 0.179910
        y = -1.1063814 * x**3 - 1.34811020 * x**2 + 2.18555832 * x - 0.20219683
    return x, y


def xy_to_xyz(x: float, y: float) -> np.ndarray:
    return np.array([x / y, 1.0, (1 - x - y) / y])


def white_shift_matrix(mired_shift: float, tint: float) -> np.ndarray:
    """3x3 matrix on linear working RGB emulating a white-balance slider move.

    ``mired_shift`` > 0 warms the image (as if the scene light were bluer than
    assumed), < 0 cools it.  ``tint`` > 0 adds magenta, < 0 adds green.
    """
    base = 1e6 / 5003.0
    src_cct = 1e6 / max(base - mired_shift, 80.0)
    x, y = cct_to_xy(float(np.clip(src_cct, 2000, 20000)))
    src = xy_to_xyz(x, y)
    # tint: move along the iso-CCT normal in CIE 1960 uv
    if tint:
        X, Y, Z = src
        denom = X + 15 * Y + 3 * Z
        u, v = 4 * X / denom, 6 * Y / denom
        v = v + tint * 0.0006
        d2 = 2 * u - 8 * v + 4
        xx, yy = 3 * u / d2, 2 * v / d2
        src = xy_to_xyz(xx, yy)
    # adapt in XYZ-D50 space: colours seen under `src` should look like under D50
    a = adapt_matrix(src, D50)
    return np.linalg.inv(_PROPHOTO_TO_XYZ) @ a @ _PROPHOTO_TO_XYZ


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0 + 1e-12), 0.0, 1.0)
    return t * t * (3 - 2 * t)
