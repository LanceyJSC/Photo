"""Synthetic RAW generation for tests: turn an sRGB picture into a real DNG
(RGGB Bayer mosaic, 12-bit, shot-noise + read-noise) so the genuine LibRaw
decode path is exercised without needing camera files."""
from __future__ import annotations

from pathlib import Path

import numpy as np


def srgb_to_lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def write_dng(path: str | Path, srgb: np.ndarray, ev: float = 0.0, iso_noise: float = 0.0,
              seed: int = 0, bpp: int = 12, wb=(1.0, 1.0, 1.0)) -> Path:
    """``srgb``: HxWx3 float in [0,1].  ``ev`` scales scene light (negative = under-exposed RAW).
    ``iso_noise``: 0 = clean, 1 ~ ISO 6400-ish noise."""
    from pidng.core import RAW2DNG, DNGTags, Tag
    from pidng.defs import CFAPattern, CalibrationIlluminant, DNGVersion, Orientation, PhotometricInterpretation, PreviewColorSpace

    h, w = (srgb.shape[0] // 2) * 2, (srgb.shape[1] // 2) * 2
    lin = srgb_to_lin(np.clip(srgb[:h, :w], 0, 1)) * (2.0 ** ev)
    rng = np.random.default_rng(seed)
    white = (1 << bpp) - 1
    black = 64 if bpp == 12 else 256
    mosaic = np.zeros((h, w), np.float64)
    mosaic[0::2, 0::2] = lin[0::2, 0::2, 0] / wb[0]
    mosaic[0::2, 1::2] = lin[0::2, 1::2, 1] / wb[1]
    mosaic[1::2, 0::2] = lin[1::2, 0::2, 1] / wb[1]
    mosaic[1::2, 1::2] = lin[1::2, 1::2, 2] / wb[2]
    signal = mosaic * (white - black)
    if iso_noise > 0:
        k = 8.0 * iso_noise                       # photons per DN, inverse gain
        shot = rng.poisson(np.maximum(signal, 0) / max(k, 1e-3)) * k if k > 0.05 else signal
        read = rng.normal(0, 2.0 + 6.0 * iso_noise, signal.shape)
        signal = shot + read
    raw = np.clip(signal + black, 0, white).astype(np.uint16)

    t = DNGTags()
    t.set(Tag.ImageWidth, w)
    t.set(Tag.ImageLength, h)
    t.set(Tag.TileWidth, w)
    t.set(Tag.TileLength, h)
    t.set(Tag.Orientation, Orientation.Horizontal)
    t.set(Tag.PhotometricInterpretation, PhotometricInterpretation.Color_Filter_Array)
    t.set(Tag.SamplesPerPixel, 1)
    t.set(Tag.BitsPerSample, bpp)
    t.set(Tag.CFARepeatPatternDim, [2, 2])
    t.set(Tag.CFAPattern, CFAPattern.RGGB)
    t.set(Tag.BlackLevel, black)
    t.set(Tag.WhiteLevel, white)
    ccm = [[32406, 10000], [-15372, 10000], [-4986, 10000],
           [-9689, 10000], [18758, 10000], [415, 10000],
           [557, 10000], [-2040, 10000], [10570, 10000]]
    t.set(Tag.ColorMatrix1, ccm)
    t.set(Tag.CalibrationIlluminant1, CalibrationIlluminant.D65)
    t.set(Tag.AsShotNeutral, [[int(1e4 * wb_i), 10000] for wb_i in (1.0 / wb[0], 1.0 / wb[1], 1.0 / wb[2])] if False
          else [[10000, int(10000 * wb[0])], [10000, int(10000 * wb[1])], [10000, int(10000 * wb[2])]])
    t.set(Tag.Make, "SynthCam")
    t.set(Tag.Model, "S1")
    t.set(Tag.DNGVersion, DNGVersion.V1_4)
    t.set(Tag.DNGBackwardVersion, DNGVersion.V1_2)
    t.set(Tag.PreviewColorSpace, PreviewColorSpace.sRGB)
    path = Path(path)
    r = RAW2DNG()
    r.options(t, path=str(path.parent), compress=False)
    r.convert(raw, filename=path.stem)
    return path
