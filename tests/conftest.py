import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import synth  # noqa: E402


def scene(w=480, h=320, seed=0):
    """Smooth colourful test scene with a bright sky band, a face-ish blob and texture."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.float32)
    img[..., 0] = 0.25 + 0.5 * x / w
    img[..., 1] = 0.30 + 0.4 * y / h
    img[..., 2] = 0.55 - 0.3 * x / w
    img[: h // 4] = np.array([0.35, 0.6, 0.95]) * (1 - 0.2 * y[: h // 4, :, None] / h)
    img += rng.normal(0, 0.01, img.shape).astype(np.float32)
    return np.clip(img, 0, 1)


@pytest.fixture(scope="session")
def dng(tmp_path_factory):
    d = tmp_path_factory.mktemp("raw")
    return synth.write_dng(d / "scene.dng", scene(), ev=-0.5, iso_noise=0.2)


@pytest.fixture
def scene_rgb():
    return scene()
