"""The browser's DNG decoder is JavaScript, so these tests drive it through Node (skipped when Node is absent).
Fixtures are real DNG files written by tests/dngsynth.py and independently cross-checked with LibRaw."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import dngsynth as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

N = np.array([0.5, 1.0, 0.6])
C = np.array([[0.9, 0.1, 0.0], [0.05, 0.85, 0.1], [0.0, 0.15, 0.85]])


def scene(h=96, w=128):
    y, x = np.mgrid[0:h, 0:w]
    lin = np.stack([0.1 + 0.6 * x / w, 0.1 + 0.6 * y / h, 0.5 - 0.3 * x / w], axis=-1) * 0.8
    lin[20:40, 30:60] = [0.7, 0.2, 0.1]
    cam = (lin.reshape(-1, 3) @ np.linalg.inv(C).T) * N
    return lin, np.clip(np.round(cam * 4095), 0, 4095).astype(np.uint16).reshape(h, w, 3)


def decode(path, max_side=4000):
    script = f"""
const fs=require('fs');const DNG=new Function(fs.readFileSync({json.dumps(str(ROOT / 'browser' / 'dng_decoder.js'))},'utf8')+';return DNG;')();
const b=fs.readFileSync({json.dumps(str(path))});const r=DNG.decode(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),{max_side});
process.stdout.write(JSON.stringify({{w:r.w,h:r.h,meta:r.meta,rgb:Array.from(r.rgb)}}));"""
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    return d, np.array(d["rgb"], np.float32).reshape(d["h"], d["w"], 3)


@pytest.mark.parametrize("compress", [True, False])
def test_proraw_style_linear_dng_is_decoded_exactly(tmp_path, compress):
    lin, raw = scene()
    p = D.write_dng(tmp_path / "a.dng", raw, linear=True, bits=12, tile=(64, 64), neutral=tuple(N), fm=D.SRGB_TO_XYZ50 @ C, white=4095, compress=compress)
    d, out = decode(p)
    assert d["meta"]["kind"].startswith("ProRAW") and d["meta"]["compressed"] == compress
    assert out.shape == lin.shape and np.abs(out - lin).max() < 0.012      # 12-bit quantisation only


def test_orientation_crop_and_downscale(tmp_path):
    lin, raw = scene()
    p = D.write_dng(tmp_path / "o.dng", raw, linear=True, bits=12, tile=(64, 64), orientation=6, neutral=tuple(N), fm=D.SRGB_TO_XYZ50 @ C, white=4095, crop=(8, 6, 100, 80))
    _, out = decode(p)
    assert np.abs(out - np.rot90(lin[6:86, 8:108], -1)).max() < 0.012
    _, small = decode(p, 40)
    assert max(small.shape[:2]) <= 40 and abs(small.mean() - out.mean()) < 0.01


def test_bayer_dng_is_binned_to_half_size(tmp_path):
    lin, raw = scene()
    h, w = raw.shape[:2]
    m = np.zeros((h, w), np.uint16)
    m[0::2, 0::2] = raw[0::2, 0::2, 0]; m[0::2, 1::2] = raw[0::2, 1::2, 1]; m[1::2, 0::2] = raw[1::2, 0::2, 1]; m[1::2, 1::2] = raw[1::2, 1::2, 2]
    p = D.write_dng(tmp_path / "b.dng", m, linear=False, bits=12, tile=(64, 64), neutral=tuple(N), fm=D.SRGB_TO_XYZ50 @ C, white=4095)
    d, out = decode(p)
    assert d["meta"]["kind"] == "Bayer DNG" and out.shape[:2] == (h // 2, w // 2)
    assert np.abs(out - lin.reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))).mean() < 0.02


def test_independent_decoder_agrees_the_fixture_is_valid(tmp_path):
    rawpy = pytest.importorskip("rawpy")
    _, raw = scene()
    p = D.write_dng(tmp_path / "c.dng", raw, linear=True, bits=12, tile=(64, 64), neutral=tuple(N), fm=D.SRGB_TO_XYZ50 @ C, white=4095)
    assert np.array_equal(rawpy.imread(str(p)).raw_image[..., :3], raw)
