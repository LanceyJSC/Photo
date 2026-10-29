"""High-level API: photo in, finished edit out."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import analysis, director, export, pipeline, raw, styles
from .filters import long_side

VERSION = "0.1.0"


@dataclass
class Result:
    outputs: dict = field(default_factory=dict)
    recipe: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    analysis: dict = field(default_factory=dict)
    size: tuple = (0, 0)
    seconds: float = 0.0


def resolve_style(style: str | None, text: str | None = None) -> tuple[styles.Style, dict, list]:
    """A style id wins; otherwise free text ("moody b&w street, grainy") is matched."""
    if style:
        return styles.get(style), {}, []
    if text:
        return styles.match(text)
    return styles.get(styles.DEFAULT_STYLE), {}, []


def _load(path, preview_side: int | None):
    half = False
    if preview_side and Path(path).suffix.lower() in raw.RAW_EXTS:
        half = True   # 4x faster decode; plenty for previews
    ph = raw.load(path, half=half)
    full_long = long_side(ph.rgb) * (2 if half else 1)
    if preview_side and long_side(ph.rgb) > preview_side:
        s = preview_side / long_side(ph.rgb)
        ph.rgb = cv2.resize(ph.rgb, (round(ph.rgb.shape[1] * s), round(ph.rgb.shape[0] * s)), interpolation=cv2.INTER_AREA)
    return ph, full_long


def render_recipe(ph: raw.Photo, r: dict, an, full_long: int, progress=None):
    lab, info = pipeline.develop(ph.rgb, r, an, full_long=full_long, progress=progress)
    return pipeline.to_display(lab), info


def plan_for(path, style: str | None = None, text: str | None = None, strength: float = 1.0,
             modifiers: dict | None = None, preview_side: int | None = None):
    st, mods, _ = resolve_style(style, text)
    mods = {**mods, **(modifiers or {})}
    ph, full_long = _load(path, preview_side)
    an = analysis.analyze(ph.rgb, ph.is_raw)
    r, notes = director.plan(ph.rgb, an, st, strength, mods)
    return ph, an, r, notes, full_long, st


def preview(path, style=None, text=None, strength=1.0, modifiers=None, side=1600,
            recipe: dict | None = None, quality: int = 86) -> tuple[bytes, dict]:
    """Fast JPEG preview.  Pass ``recipe`` to re-render a stored edit."""
    ph, an, r, notes, full_long, st = plan_for(path, style, text, strength, modifiers, preview_side=side)
    if recipe:
        r = recipe
    enc, _ = render_recipe(ph, r, an, full_long)
    return export.jpeg_bytes(pipeline.quantize8(enc), quality), {"recipe": r, "notes": notes, "analysis": an.summary()}


def process(path, out_dir, style=None, text=None, strength=1.0, modifiers=None,
            formats=("jpg",), max_side: int | None = None, progress=None, quality: int = 95,
            recipe: dict | None = None, suffix: str | None = None) -> Result:
    """Full-resolution edit.  Original is never touched; a ``.darkroom.json`` sidecar
    stores the recipe so the edit is reproducible."""
    t0 = time.time()
    path, out_dir = Path(path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    say = progress or (lambda s, f: None)
    say("decoding RAW", 0.0)
    st, mods, _ = resolve_style(style, text)
    mods = {**mods, **(modifiers or {})}
    ph = raw.load(path, half=False)
    full_long = long_side(ph.rgb)
    say("analysing", 0.05)
    an = analysis.analyze(ph.rgb, ph.is_raw)
    if recipe is None:
        say("planning edit", 0.08)
        r, notes = director.plan(ph.rgb, an, st, strength, mods)
    else:
        r, notes = recipe, ["Re-rendered from stored recipe"]
    lab, info = pipeline.develop(ph.rgb, r, an, full_long=full_long,
                                 progress=lambda s, f: say(s, 0.1 + 0.8 * f))
    del ph.rgb
    say("output", 0.92)
    enc = pipeline.to_display(lab)
    del lab
    if max_side and long_side(enc) > max_side:
        s = max_side / long_side(enc)
        enc = cv2.resize(enc, (round(enc.shape[1] * s), round(enc.shape[0] * s)), interpolation=cv2.INTER_AREA)
    h, w = enc.shape[:2]
    stem = f"{path.stem}_{suffix or st.id}"
    outs = {}
    for fmt in formats:
        fmt = fmt.lower().lstrip(".")
        if fmt in ("jpg", "jpeg"):
            outs["jpg"] = str(export.save_jpeg(out_dir / f"{stem}.jpg", pipeline.quantize8(enc), ph.meta, quality))
        elif fmt in ("tif", "tiff"):
            outs["tif"] = str(export.save_tiff16(out_dir / f"{stem}.tif", pipeline.quantize16(enc)))
        elif fmt == "png":
            outs["png"] = str(export.save_png16(out_dir / f"{stem}.png", pipeline.quantize16(enc)))
        else:
            raise ValueError(f"unknown output format: {fmt}")
    side = out_dir / f"{stem}.darkroom.json"
    side.write_text(json.dumps({"app": "darkroom", "version": VERSION, "source": str(path), "style": st.id,
                                "strength": strength, "modifiers": mods, "recipe": r, "notes": notes,
                                "analysis": an.summary()}, indent=1))
    outs["sidecar"] = str(side)
    say("done", 1.0)
    return Result(outs, r, notes, an.summary(), (w, h), time.time() - t0)


def option_previews(path, style_ids, side: int = 640, on_ready=None):
    """Render the *same* photo in many looks, decoding and analysing only once.

    ``style_ids`` is a list, or a callable ``(analysis, rgb) -> list`` so the order can
    depend on the scene.  ``on_ready(style_id, jpeg_bytes)`` fires as each look finishes,
    so a UI can show them as they arrive."""
    ph, full_long = _load(path, side)
    an = analysis.analyze(ph.rgb, ph.is_raw)
    ids = style_ids(an, ph.rgb) if callable(style_ids) else style_ids
    for sid in ids:
        try:
            st = styles.get(sid)
            r, _ = director.plan(ph.rgb, an, st, 1.0)
            enc, _ = render_recipe(ph, r, an, full_long)
            if on_ready:
                on_ready(sid, export.jpeg_bytes(pipeline.quantize8(enc), 82))
        except Exception:  # noqa: BLE001 - one bad look must not stop the rest
            import traceback
            traceback.print_exc()
    return an
