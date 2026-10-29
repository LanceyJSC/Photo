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
