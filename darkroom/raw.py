"""Image loading: camera RAW via LibRaw, plus JPEG/PNG/TIFF.

Everything is returned as linear ProPhoto RGB float32 so the pipeline is
identical for every source.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import color

RAW_EXTS = {
    ".dng", ".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".raf",
    ".orf", ".rw2", ".rwl", ".pef", ".ptx", ".raw", ".3fr", ".fff", ".iiq", ".erf",
    ".mrw", ".kdc", ".dcr", ".srw", ".x3f", ".mef", ".mos", ".cap",
}
BITMAP_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_EXTS = RAW_EXTS | BITMAP_EXTS


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTS


@dataclass
class Photo:
    rgb: np.ndarray                     # HxWx3 float32 linear ProPhoto, 1.0 = sensor/white clip
    is_raw: bool
    path: str = ""
    meta: dict = field(default_factory=dict)
    exif_bytes: bytes | None = None     # raw EXIF block to carry into the export

    @property
    def size(self) -> tuple[int, int]:
        return self.rgb.shape[1], self.rgb.shape[0]


def _exif_meta(path: Path) -> tuple[dict, bytes | None]:
    """Best-effort EXIF (ISO, exposure, lens...).  Never raises."""
    meta: dict = {}
    blob = None
    try:
        from PIL import Image, ExifTags
        with Image.open(path) as im:
            ex = im.getexif()
            if ex:
                try:
                    blob = ex.tobytes()
                except Exception:
                    blob = None
                sub = {}
                try:
                    sub = dict(ex.get_ifd(0x8769))
                except Exception:
                    pass
                names = {**{ExifTags.TAGS.get(k, k): v for k, v in ex.items()},
                         **{ExifTags.TAGS.get(k, k): v for k, v in sub.items()}}
                for key in ("Make", "Model", "LensModel", "ISOSpeedRatings", "PhotographicSensitivity",
                            "ExposureTime", "FNumber", "FocalLength", "DateTimeOriginal"):
                    if key in names:
                        v = names[key]
                        meta[key] = float(v) if hasattr(v, "numerator") else v
                iso = meta.get("ISOSpeedRatings") or meta.get("PhotographicSensitivity")
                if isinstance(iso, (tuple, list)):
                    iso = iso[0]
                if iso:
                    meta["iso"] = int(iso)
    except Exception:
        pass
    return meta, blob


def _load_raw(path: Path, half: bool) -> np.ndarray:
    import rawpy
    kwargs = dict(
        use_camera_wb=True,
        output_color=rawpy.ColorSpace.ProPhoto,
        gamma=(1, 1),
        no_auto_bright=True,
        output_bps=16,
        highlight_mode=rawpy.HighlightMode.Blend,
        half_size=half,
        fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
        median_filter_passes=0,
        bright=1.0,
    )
    with rawpy.imread(str(path)) as raw:
        algo = None
        for name in ("DHT", "AAHD", "AHD"):
            algo = getattr(rawpy.DemosaicAlgorithm, name, None)
            if algo is not None:
                try:
                    rgb16 = raw.postprocess(demosaic_algorithm=algo, **kwargs)
                    break
                except Exception:
                    algo = None
        if algo is None:
            rgb16 = raw.postprocess(**kwargs)
    return rgb16.astype(np.float32) / 65535.0


def _load_bitmap(path: Path) -> np.ndarray:
    from PIL import Image, ImageCms, ImageOps
    arr = None
    if path.suffix.lower() in (".png", ".tif", ".tiff"):
        raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if raw is not None and raw.dtype == np.uint16:
            if raw.ndim == 2:
                raw = np.stack([raw] * 3, -1)
            arr = cv2.cvtColor(raw[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 65535.0
    if arr is None:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            icc = im.info.get("icc_profile")
            if icc:
                try:
                    src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                    dst = ImageCms.createProfile("sRGB")
                    im = ImageCms.profileToProfile(im.convert("RGB"), src, dst, outputMode="RGB")
                except Exception:
                    pass
            arr = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    return color.display_to_pro(arr)


def load(path: str | Path, half: bool = False) -> Photo:
    """Decode ``path`` into a :class:`Photo`.  ``half`` decodes RAWs at half
    resolution (4x faster; used for previews)."""
    p = Path(path)
    ext = p.suffix.lower()
    meta, blob = _exif_meta(p)
    if ext in RAW_EXTS:
        rgb = _load_raw(p, half)
        photo = Photo(rgb, True, str(p), meta, blob)
    elif ext in BITMAP_EXTS:
        rgb = _load_bitmap(p)
        photo = Photo(rgb, False, str(p), meta, blob)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return photo
