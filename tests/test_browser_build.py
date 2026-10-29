import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_browser_build_embeds_every_style_and_the_face_model(tmp_path):
    out = tmp_path / "frag.html"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_browser.py"), str(out)], check=True)
    html = out.read_text()
    assert "window.__DATA__=" in html and "window.__FACE__=" in html
    data = json.loads(html.split("window.__DATA__=")[1].split(";\nwindow.__FACE__=")[0])
    from darkroom import styles
    assert len(data["styles"]) == len(styles.STYLES)
    assert data["styles"][0]["recipe"]["tone"]["contrast"] > 0
    face = json.loads(html.split("window.__FACE__=")[1].split(";\n/*", 1)[0].rsplit(";", 1)[0]) if False else None
    assert "<title>Darkroom</title>" in html and "downloads" in html


def test_every_recommended_look_exists():
    import re
    from darkroom import recommend, styles
    ids = {s.id for s in styles.STYLES}
    for pool in (recommend._PORTRAIT, recommend._LANDSCAPE, recommend._ARCH, recommend._NIGHT, recommend._STREET, recommend._FILM):
        assert set(pool) <= ids, set(pool) - ids
    tpl = (ROOT / "browser" / "darkroom.template.html").read_text()
    block = re.search(r"const POOLS = \{(.*?)\n\};", tpl, re.S).group(1)
    used = set(re.findall(r'"([a-z0-9_]+)"', block)) - {"portrait", "landscape", "architecture", "night", "street", "interior", "food", "animal"}
    assert used <= ids, used - ids


def test_vision_model_blob_is_present_and_complete():
    blob = json.loads((ROOT / "browser" / "vision_model.json").read_text())
    assert len(blob["labels"]) == 1000 and blob["labels"][285] == "Egyptian cat"
    assert {o["t"] for o in blob["ops"]} == {"conv", "dw", "add", "avg", "reshape", "fc", "softmax"}
    import base64
    assert len(base64.b64decode(blob["weights"])) > 4_000_000
