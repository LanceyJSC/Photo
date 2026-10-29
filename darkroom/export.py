"""Writing results: colour-managed JPEG / 16-bit TIFF / PNG with a clean EXIF subset."""
from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np

_ICC_CACHE: dict = {}


def srgb_icc() -> bytes:
    if "srgb" not in _ICC_CACHE:
        from PIL import ImageCms
        _ICC_CACHE["srgb"] = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    return _ICC_CACHE["srgb"]


def _exif(meta: dict):
    from PIL import Image
    ex = Image.Exif()
    mapping = {"Make": 0x010F, "Model": 0x0110, "DateTimeOriginal": None}
    try:
        for k, tag in (("Make", 0x010F), ("Model", 0x0110)):
            if isinstance(meta.get(k), str):
                ex[tag] = meta[k].strip("\x00 ")
        sub = ex.get_ifd(0x8769)
        if meta.get("iso"):
            sub[0x8827] = int(meta["iso"])
        if isinstance(meta.get("ExposureTime"), float):
            sub[0x829A] = meta["ExposureTime"]
        if isinstance(meta.get("FNumber"), float):
            sub[0x829D] = meta["FNumber"]
        if isinstance(meta.get("FocalLength"), float):
            sub[0x920A] = meta["FocalLength"]
        if isinstance(meta.get("DateTimeOriginal"), str):
            sub[0x9003] = meta["DateTimeOriginal"]
        if isinstance(meta.get("LensModel"), str):
            sub[0xA434] = meta["LensModel"]
        ex[0x0131] = "Darkroom"
    except Exception:
        pass
    return ex


def save_jpeg(path: Path, rgb8: np.ndarray, meta: dict | None = None, quality: int = 95) -> Path:
    from PIL import Image
    im = Image.fromarray(rgb8)
    kw = dict(quality=quality, subsampling=0, optimize=True, icc_profile=srgb_icc())
    try:
        im.save(path, "JPEG", exif=_exif(meta or {}), **kw)
    except Exception:
        im.save(path, "JPEG", **kw)
    return path


def save_tiff16(path: Path, rgb16: np.ndarray) -> Path:
    try:
        import tifffile
        tifffile.imwrite(str(path), rgb16, photometric="rgb", iccprofile=srgb_icc(), compression="deflate")
    except Exception:
        cv2.imwrite(str(path), cv2.cvtColor(rgb16, cv2.COLOR_RGB2BGR))
    return path


def save_png16(path: Path, rgb16: np.ndarray) -> Path:
    cv2.imwrite(str(path), cv2.cvtColor(rgb16, cv2.COLOR_RGB2BGR))
    return path


def jpeg_bytes(rgb8: np.ndarray, quality: int = 88) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(rgb8).save(buf, "JPEG", quality=quality, icc_profile=srgb_icc())
    return buf.getvalue()
