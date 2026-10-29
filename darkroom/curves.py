"""Tone curves: monotone cubic splines and the filmic base curve."""
from __future__ import annotations

import numpy as np


def monotone_spline(points, n: int = 4096, x_max: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Fritsch-Carlson monotone cubic through ``points`` -> (xs, ys) lookup table.

    Beyond the outermost points the curve continues linearly with the end slope
    (so highlights above 1.0 keep going rather than being flat-clipped).
    """
    pts = sorted((float(x), float(y)) for x, y in points)
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    h = np.diff(xs)
    h[h == 0] = 1e-9
    d = np.diff(ys) / h
    m = np.zeros_like(xs)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(xs) - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(len(d)):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / np.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    grid = np.linspace(min(0.0, xs[0]), max(x_max, xs[-1]), n)
    idx = np.clip(np.searchsorted(xs, grid) - 1, 0, len(xs) - 2)
    t = (grid - xs[idx]) / h[idx]
    t2, t3 = t * t, t * t * t
    out = ((2 * t3 - 3 * t2 + 1) * ys[idx] + (t3 - 2 * t2 + t) * h[idx] * m[idx] +
           (-2 * t3 + 3 * t2) * ys[idx + 1] + (t3 - t2) * h[idx] * m[idx + 1])
    lo, hi = grid < xs[0], grid > xs[-1]
    out[lo] = ys[0] + m[0] * (grid[lo] - xs[0])
    out[hi] = ys[-1] + m[-1] * (grid[hi] - xs[-1])
    return grid.astype(np.float32), out.astype(np.float32)


def apply_lut(x: np.ndarray, grid: np.ndarray, vals: np.ndarray) -> np.ndarray:
    return np.interp(x, grid, vals).astype(np.float32)


def apply_points(x: np.ndarray, points) -> np.ndarray:
    grid, vals = monotone_spline(points)
    return apply_lut(x, grid, vals)


def is_identity(points, tol: float = 1e-4) -> bool:
    return all(abs(x - y) < tol for x, y in points)


def filmic_curve(pivot_in: float, pivot_out: float, contrast: float, toe: float,
                 shoulder: float, white_in: float, black_in: float = 0.0,
                 black_out: float = 0.0):
    """Base tone curve in Oklab-L space (scene L -> display L).

    * ``contrast``  slope at the pivot (1 = neutral)
    * ``toe``       0..1 how softly shadows roll into black
    * ``shoulder``  0..1 how softly highlights roll toward white
    * ``white_in``  scene L that maps to display 1.0 (>1 leaves highlight headroom)

    Built as control points for the monotone spline so the shape is always smooth
    and monotonic.
    """
    m = contrast
    # centre segment (linear in L around the pivot)
    d = 0.12
    pts = [(black_in, black_out)]
    # shadow toe: slope eases from ~0 at the black point up to m at the pivot
    toe_x = pivot_in - d - 0.30 * (0.4 + toe)
    toe_x = max(toe_x, black_in + 0.06)
    toe_y_lin = pivot_out - m * (pivot_in - toe_x)
    if toe_y_lin > black_out:
        toe_y = black_out + (toe_y_lin - black_out) * (1.0 - 0.55 * toe)
    else:
        toe_y = black_out + 0.01
    pts.append((toe_x, toe_y))
    pts.append((pivot_in - d, pivot_out - m * d))
    pts.append((pivot_in, pivot_out))
    pts.append((pivot_in + d, pivot_out + m * d))
    # highlight shoulder
    sh_x = pivot_in + d + (white_in - pivot_in - d) * (0.50 - 0.18 * shoulder)
    sh_lin = pivot_out + m * (sh_x - pivot_in)
    sh_y = pivot_out + m * d + (min(sh_lin, 1.0) - (pivot_out + m * d)) * (1.0 - 0.45 * shoulder)
    sh_y = min(sh_y, 0.985)
    pts.append((sh_x, sh_y))
    pts.append((white_in, 1.0))
    # extend flat past white so over-range values compress to 1 smoothly
    pts.append((white_in + 0.6, 1.0 + 0.002))
    # remove non-monotone points introduced by extreme parameter combos
    cleaned = [pts[0]]
    for x, y in pts[1:]:
        if x > cleaned[-1][0] + 1e-4 and y >= cleaned[-1][1]:
            cleaned.append((x, y))
    return cleaned


def fade_points(lift: float, mid: float = 0.5):
    """Matte / faded blacks: raise the black point without moving highlights."""
    return [(0.0, lift), (mid, mid + lift * 0.35), (1.0, 1.0)]
