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
