"""Convert OpenCV's Haar frontal-face cascade to compact JSON for the browser build."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export() -> dict:
    t = ET.parse(ROOT / "darkroom" / "data" / "haarcascade_frontalface_alt2.xml").getroot().find("cascade")
    w, h = int(t.findtext("width")), int(t.findtext("height"))
    feats = []
    for f in t.find("features"):
        rects = []
        for r in f.find("rects"):
            x, y, rw, rh, wt = r.text.strip().rstrip(".").split()
            rects.append([int(x), int(y), int(rw), int(rh), float(wt.rstrip("."))])
        feats.append(rects)
    stages = []
    for st in t.find("stages"):
        weak = []
        for wc in st.find("weakClassifiers"):
            nodes = [float(v) for v in wc.findtext("internalNodes").split()]
            leaves = [float(v) for v in wc.findtext("leafValues").split()]
            weak.append([[int(nodes[i]), int(nodes[i + 1]), int(nodes[i + 2]), nodes[i + 3]] for i in range(0, len(nodes), 4)] + [leaves])
        stages.append([float(st.findtext("stageThreshold")), weak])
    return {"w": w, "h": h, "feats": feats, "stages": stages}


if __name__ == "__main__":
    json.dump(export(), sys.stdout, separators=(",", ":"))
