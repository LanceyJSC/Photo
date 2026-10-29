"""Build the phone-only, no-server version of Darkroom.

Writes browser/darkroom.html (standalone, can be hosted on any static host / GitHub Pages)
and prints the path of the fragment used for the claude.ai artifact."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from export_face_cascade import export as export_face  # noqa: E402
from export_styles_json import export  # noqa: E402
from vision_groups import groups  # noqa: E402

tpl = (ROOT / "browser" / "darkroom.template.html").read_text()
vision = json.loads((ROOT / "browser" / "vision_model.json").read_text())
seg = json.loads((ROOT / "browser" / "seg_model.json").read_text())
lm = json.loads((ROOT / "browser" / "lm_model.json").read_text())
data = ("window.__DATA__=" + json.dumps(export(), separators=(",", ":")) + ";\n"
        "window.__FACE__=" + json.dumps(export_face(), separators=(",", ":")) + ";\n"
        "window.__GROUPS__=" + json.dumps(groups(vision["labels"]), separators=(",", ":")) + ";\n"
        "window.__VISION__=" + json.dumps(vision, separators=(",", ":")) + ";\n"
        "window.__SEG__=" + json.dumps(seg, separators=(",", ":")) + ";\n"
        "window.__LM__=" + json.dumps(lm, separators=(",", ":")) + ";")
fragment = tpl.replace("/*__DATA__*/", data).replace("/*__ENGINE__*/", (ROOT / "browser" / "vision_engine.js").read_text()).replace("/*__DNG__*/", (ROOT / "browser" / "dng_decoder.js").read_text())
out_frag = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "browser" / "darkroom.fragment.html"
out_frag.write_text(fragment)
head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>')
(ROOT / "browser" / "darkroom.html").write_text(head + fragment + "</body></html>")
print(out_frag, len(fragment) // 1024, "KB")
