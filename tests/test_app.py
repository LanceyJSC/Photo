import time

from fastapi.testclient import TestClient

from darkroom.jobs import Watcher
from darkroom.server import create_app


def wait(client, jid, status="done", timeout=60):
    t = time.time()
    while time.time() - t < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in (status, "error"):
            return j
        time.sleep(0.2)
    raise TimeoutError


def test_full_web_flow(dng, tmp_path):
    client = TestClient(create_app(tmp_path / "data"))
    st = client.get("/api/styles").json()
    assert "Street" in st["categories"] and "Architecture" in st["categories"]
    m = client.post("/api/match", json={"text": "moody black and white street"}).json()
    assert m["style"].startswith("street")

    with open(dng, "rb") as f:
        up = client.post("/api/upload", files=[("files", ("scene.dng", f.read()))]).json()
    assert not up["errors"]
    jid = up["jobs"][0]["id"]
    j = wait(client, jid, "awaiting_style")
    assert j["status"] == "awaiting_style"
    t = time.time()
    while not client.get(f"/api/jobs/{jid}").json()["has_thumb"] and time.time() - t < 20:
        time.sleep(0.2)
    assert client.get(f"/api/jobs/{jid}/image/before").status_code == 200

    r = client.post(f"/api/jobs/{jid}/edit", json={"style": m["style"], "modifiers": m["modifiers"], "formats": ["jpg", "tif"]})
    assert r.status_code == 200
    j = wait(client, jid)
    assert j["status"] == "done", j.get("error")
    assert client.get(f"/api/jobs/{jid}/image/after").status_code == 200
    assert client.get(j["downloads"]["jpg"]).headers["content-type"].startswith("image/jpeg")
    assert j["notes"]

    assert client.post(f"/api/jobs/{jid}/edit", json={"style": "nope"}).status_code == 400
    assert client.post("/api/upload", files=[("files", ("evil.exe", b"x"))]).json()["errors"]
    assert client.delete(f"/api/jobs/{jid}").json()["ok"]
    assert client.get("/").status_code == 200


def test_filename_cannot_escape_upload_dir(tmp_path):
    client = TestClient(create_app(tmp_path / "data"))
    r = client.post("/api/upload", files=[("files", ("../../etc/x.jpg", b"not a real jpg"))]).json()
    if r["jobs"]:
        assert ".." not in r["jobs"][0]["name"]
    assert not (tmp_path / "etc").exists()


def test_watch_folder_edits_new_files(dng, tmp_path):
    inbox, outbox = tmp_path / "in", tmp_path / "out"
    w = Watcher(inbox, outbox, "natural", None, log=lambda *_: None)
    import shutil
    shutil.copy(dng, inbox / "a.dng")
    w.scan()          # first sight: size recorded
    assert not list(outbox.glob("*.jpg"))
    w.scan()          # stable: processed
    assert list(outbox.glob("a_natural.jpg"))


def test_lan_token_protects_everything(tmp_path):
    client = TestClient(create_app(tmp_path / "data", token="s3cret"), follow_redirects=False)
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/").status_code == 401
    assert client.post("/api/upload", files=[("files", ("a.jpg", b"x"))]).status_code == 401
    assert client.get("/?token=wrong").status_code == 401
    r = client.get("/?token=s3cret")
    assert r.status_code == 303 and "token" not in r.headers["location"]
    assert "dr_token" in r.headers["set-cookie"]
    client.cookies.set("dr_token", "s3cret")
    assert client.get("/api/jobs").status_code == 200
    assert client.get("/").status_code == 200
    # the installable-app files must stay reachable without credentials
    anon = TestClient(create_app(tmp_path / "d2", token="s3cret"))
    assert anon.get("/manifest.webmanifest").status_code == 200
    assert anon.get("/sw.js").status_code == 200


def test_heic_from_iphone_is_accepted(tmp_path):
    import numpy as np
    from PIL import Image
    import pillow_heif
    pillow_heif.register_heif_opener()
    p = tmp_path / "IMG_0001.HEIC"
    Image.fromarray((np.random.default_rng(0).random((200, 300, 3)) * 255).astype("uint8")).save(p)
    from darkroom import edit
    res = edit.process(p, tmp_path / "o", style="natural")
    assert res.size[0] > 100


def test_share_target_adds_job(tmp_path, dng):
    client = TestClient(create_app(tmp_path / "data"), follow_redirects=False)
    r = client.post("/share", files=[("files", ("scene.dng", dng.read_bytes()))])
    assert r.status_code == 303
    assert len(client.get("/api/jobs").json()) == 1
