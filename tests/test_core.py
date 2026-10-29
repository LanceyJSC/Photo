import numpy as np
import pytest

from darkroom import analysis, color, curves, director, edit, geometry, pipeline, raw, recipe, styles


def test_oklab_roundtrip():
    rng = np.random.default_rng(1)
    pro = color.display_to_pro(rng.random((16, 16, 3)).astype(np.float32) * 0.9 + 0.05)   # in-gamut colours
    back = color.from_oklab(color.to_oklab(pro))
    assert np.allclose(pro, back, atol=2e-3)


def test_oklab_is_homogeneous():
    pro = np.full((2, 2, 3), 0.2, np.float32)
    a = color.to_oklab(pro)
    b = color.to_oklab(pro * 8)
    assert np.allclose(b, a * 2, atol=1e-4)      # cube-root scaling => exposure is a simple multiply


def test_wb_shift_warms_and_cools():
    grey = np.full((1, 1, 3), 0.3, np.float32)
    warm = color.mat(grey, color.white_shift_matrix(40, 0))[0, 0]
    cool = color.mat(grey, color.white_shift_matrix(-40, 0))[0, 0]
    assert warm[0] > warm[2] and cool[2] > cool[0]
    mag = color.mat(grey, color.white_shift_matrix(0, 30))[0, 0]
    assert mag[1] < mag[0]                         # positive tint = magenta (less green)


def test_wb_solver_neutralises_cast():
    grey = np.full((1, 1, 3), 0.3, np.float32)
    cast = color.mat(grey, color.white_shift_matrix(35, 8))
    lab = color.to_oklab(cast)[0, 0]
    m, t = analysis.solve_wb((lab[1], lab[2]))
    fixed = color.to_oklab(color.mat(cast, color.white_shift_matrix(m, t)))[0, 0]
    assert abs(fixed[1]) < 0.004 and abs(fixed[2]) < 0.004


def test_curves_monotone():
    for c in (0.8, 1.0, 1.5, 1.9):
        pts = curves.filmic_curve(0.565, 0.6, c, 0.5, 0.5, 1.2)
        g, v = curves.monotone_spline(pts)
        assert np.all(np.diff(v) >= -1e-6)
        assert abs(float(np.interp(1.2, g, v)) - 1.0) < 0.02


def test_dng_decodes_as_raw(dng):
    ph = raw.load(dng)
    assert ph.is_raw and ph.rgb.dtype == np.float32 and ph.rgb.shape[2] == 3
    assert 0.0 <= ph.rgb.min() and ph.rgb.max() <= 1.2
    half = raw.load(dng, half=True)
    assert half.rgb.shape[0] * 2 == ph.rgb.shape[0] or abs(half.rgb.shape[0] * 2 - ph.rgb.shape[0]) <= 2


def test_noise_estimate_tracks_noise(scene_rgb):
    base = color.display_to_pro(scene_rgb)
    rng = np.random.default_rng(2)
    est = []
    for s in (0.0, 0.01, 0.03):
        noisy = base + rng.normal(0, s, base.shape).astype(np.float32)
        est.append(analysis.analyze(np.clip(noisy, 0, 1)).noise_sigma)
    assert est[0] < est[1] < est[2]


def test_denoise_reduces_noise(scene_rgb):
    from darkroom import ops
    base = color.display_to_pro(scene_rgb)
    rng = np.random.default_rng(3)
    noisy = np.clip(base + rng.normal(0, 0.02, base.shape).astype(np.float32), 0, 1)
    lab = color.to_oklab(noisy)
    clean = color.to_oklab(base)
    out = ops.denoise(lab, 0.9, 0.9)
    err_before = np.abs(lab - clean).mean()
    err_after = np.abs(out - clean).mean()
    assert err_after < err_before * 0.8


def test_upright_fixes_tilt():
    import cv2
    h, w = 600, 900
    img = np.full((h, w, 3), 0.8, np.float32)
    for x in range(100, 800, 100):
        img[60:540, x:x + 6] = 0.05
    for y in range(100, 540, 120):
        img[y:y + 5, 100:800] = 0.05
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 3.0, 1.0)
    tilted = cv2.warpAffine(img, M, (w, h), borderValue=(0.8, 0.8, 0.8))
    lin = color.display_to_pro(tilted)
    est = geometry.estimate_upright(lin)
    assert abs(est["rot"] - 3.0) < 0.6
    out, info = geometry.apply_geometry(lin, {"auto_upright": 1.0, "rotate": 0.0, "auto_horizon": 0.0, "crop": None})
    assert abs(geometry.estimate_upright(out)["rot"]) < 0.6


def test_horizon_levelling():
    import cv2
    h, w = 500, 900
    img = np.full((h, w, 3), 0.7, np.float32)
    img[250:] = 0.2
    M = cv2.getRotationMatrix2D((w / 2, h / 2), -2.5, 1.0)
    tilted = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    lin = color.display_to_pro(tilted)
    out, info = geometry.apply_geometry(lin, {"auto_upright": 0.0, "rotate": 0.0, "auto_horizon": 1.0, "crop": None})
    assert abs(info.get("horizon_deg", 0)) > 1.5
    # after levelling the edge should be flatter than before
    def slope(a):
        g = a.mean(axis=2)
        left = np.argmax(g[:, 100] < 0.3)
        right = np.argmax(g[:, a.shape[1] - 100] < 0.3)
        return abs(right - left)
    assert slope(out) < slope(lin)


@pytest.mark.parametrize("style", [s.id for s in styles.STYLES])
def test_every_style_renders_cleanly(style, scene_rgb):
    lin = color.display_to_pro(scene_rgb)
    an = analysis.analyze(lin, is_raw=True)
    st = styles.get(style)
    r, notes = director.plan(lin, an, st, 1.0)
    lab, _ = pipeline.develop(lin, r, an)
    enc = pipeline.to_display(lab)
    assert enc.shape[2] == 3 and np.isfinite(enc).all()
    assert 0 <= enc.min() and enc.max() <= 1.0
    mean = enc.mean()
    assert 0.08 < mean < 0.9, f"{style} mean {mean}"
    if st.is_bw:
        assert np.abs(enc[..., 0] - enc[..., 2]).mean() < 0.08   # toned but essentially mono


def test_strength_interpolates(scene_rgb):
    lin = color.display_to_pro(scene_rgb)
    an = analysis.analyze(lin)
    st = styles.get("street_gritty")
    outs = []
    for s in (0.0, 0.5, 1.0):
        r = recipe.scaled(st.recipe, s)
        lab, _ = pipeline.develop(lin, r, an, fast=True)
        outs.append(pipeline.to_display(lab))
    d1 = np.abs(outs[1] - outs[0]).mean()
    d2 = np.abs(outs[2] - outs[0]).mean()
    assert 0 < d1 < d2


def test_recipe_roundtrip():
    r = recipe.default()
    r["tone"]["curve"] = [[0, 0], [0.5, 0.45], [1, 1]]
    assert recipe.loads(recipe.dumps(r)) == r


def test_style_match():
    s, mods, _ = styles.match("gritty black and white street photography")
    assert s.id.startswith("street") and s.is_bw
    s, mods, _ = styles.match("clean modern architecture, cooler")
    assert s.category == "Architecture" and mods.get("warmth", 0) < 0
    s, mods, _ = styles.match("moody dark portrait")
    assert s.id == "portrait_moody"
    s, _, _ = styles.match("")
    assert s.id == styles.DEFAULT_STYLE


def test_exposure_solver_recovers_underexposure(tmp_path, scene_rgb):
    import synth
    results = {}
    for ev in (-2.0, 0.0):
        p = synth.write_dng(tmp_path / f"s{ev}.dng", scene_rgb, ev=ev, iso_noise=0.1)
        ph = raw.load(p)
        an = analysis.analyze(ph.rgb)
        r, _ = director.plan(ph.rgb, an, styles.get("natural"), 1.0)
        lab, _ = pipeline.develop(ph.rgb, r, an, fast=True)
        results[ev] = (r["exposure"]["ev"], float(np.median(pipeline.to_display(lab)[..., 1])))
    assert results[-2.0][0] > results[0.0][0] + 1.2          # solver pushes the dark RAW up
    # both end at a comparable brightness: that's the point of the solver
    assert abs(results[-2.0][1] - results[0.0][1]) < 0.12


def test_process_writes_outputs_and_sidecar(dng, tmp_path):
    res = edit.process(dng, tmp_path, style="street_classic", formats=("jpg", "tif"))
    assert (tmp_path / "scene_street_classic.jpg").exists()
    assert (tmp_path / "scene_street_classic.tif").exists()
    assert (tmp_path / "scene_street_classic.darkroom.json").exists()
    assert res.notes
    # re-render from the stored sidecar reproduces the same recipe
    import json
    data = json.loads((tmp_path / "scene_street_classic.darkroom.json").read_text())
    res2 = edit.process(dng, tmp_path / "again", recipe=data["recipe"], style="street_classic")
    from PIL import Image
    a = np.asarray(Image.open(res.outputs["jpg"]), np.float32)
    b = np.asarray(Image.open(res2.outputs["jpg"]), np.float32)
    assert np.abs(a - b).mean() < 2.0
    # original untouched
    assert dng.exists()
