"""Local web app: drop photos in, pick a look, edits render in the background."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import styles
from .jobs import JobManager

WEB = Path(__file__).parent / "web"
MAX_UPLOAD = 600 * 1024 * 1024


class EditRequest(BaseModel):
    style: str | None = None
    text: str | None = None
    strength: float = Field(1.0, ge=0.0, le=1.5)
    modifiers: dict[str, float] = {}
    formats: list[str] = ["jpg"]
    max_side: int | None = Field(None, ge=256, le=20000)


class MatchRequest(BaseModel):
    text: str


def job_json(j) -> dict:
    d = {k: getattr(j, k) for k in ("id", "name", "status", "stage", "progress", "style", "text", "strength",
                                   "modifiers", "formats", "notes", "analysis", "error", "version", "size",
                                   "has_preview", "has_thumb", "max_side", "kind", "recommended", "options_ready",
                                   "options_done")}
    d["downloads"] = {k: f"/api/jobs/{j.id}/download/{k}" for k in j.outputs}
    if j.style:
        try:
            d["style_name"] = styles.get(j.style).name
        except KeyError:
            pass
    return d


PUBLIC_PATHS = {"/manifest.webmanifest", "/sw.js"}


def create_app(data_dir: str | Path | None = None, workers: int = 1, token: str | None = None) -> FastAPI:
    """``token``: when set (e.g. when serving on the LAN for a phone) every request must carry it,
    either as ``?token=`` (which sets a cookie and redirects) or via that cookie."""
    data_dir = Path(data_dir or os.environ.get("DARKROOM_DATA", "darkroom_data"))
    mgr = JobManager(data_dir, workers=workers)
    app = FastAPI(title="Darkroom")
    app.state.jobs = mgr

    if token:
        @app.middleware("http")
        async def auth(request: Request, call_next):
            path = request.url.path
            if path in PUBLIC_PATHS or path.startswith("/static/icon") or path.startswith("/static/apple"):
                return await call_next(request)
            if secrets.compare_digest(request.cookies.get("dr_token", ""), token):
                return await call_next(request)
            if secrets.compare_digest(request.query_params.get("token", ""), token):
                resp = RedirectResponse(str(request.url.remove_query_params("token")), status_code=303)
                resp.set_cookie("dr_token", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 90)
                return resp
            return PlainTextResponse("Locked. Open the link (or scan the QR code) printed by `darkroom serve --lan`.", status_code=401)

    @app.get("/api/styles")
    def api_styles():
        cats: dict = {}
        for s in styles.catalog():
            cats.setdefault(s["category"], []).append(s)
        return {"default": styles.DEFAULT_STYLE, "categories": cats, "modifiers": list(styles_modifiers())}

    @app.post("/api/match")
    def api_match(req: MatchRequest):
        s, mods, ranked = styles.match(req.text)
        return {"style": s.id, "name": s.name, "modifiers": mods, "alternatives": ranked}

    @app.post("/api/upload")
    async def api_upload(files: list[UploadFile] = File(...)):
        out, errors = [], []
        for f in files:
            data = await f.read()
            if len(data) > MAX_UPLOAD:
                errors.append({"name": f.filename, "error": "file too large"})
                continue
            try:
                out.append(job_json(mgr.add(f.filename or "photo", content=data)))
            except ValueError as e:
                errors.append({"name": f.filename, "error": str(e)})
        return {"jobs": out, "errors": errors}

    @app.post("/share")
    async def share_target(files: list[UploadFile] = File(default=[])):
        """PWA share target: 'Share → Darkroom' from the phone's photo library."""
        for f in files:
            data = await f.read()
            if data and len(data) <= MAX_UPLOAD:
                try:
                    mgr.add(f.filename or "photo.jpg", content=data)
                except ValueError:
                    pass
        return RedirectResponse("/", status_code=303)

    @app.get("/api/jobs")
    def api_jobs():
        return [job_json(j) for j in mgr.list()]

    def _job(jid: str):
        try:
            return mgr.get(jid)
        except KeyError:
            raise HTTPException(404, "no such job") from None

    @app.get("/api/jobs/{jid}")
    def api_job(jid: str):
        return job_json(_job(jid))

    @app.post("/api/jobs/{jid}/edit")
    def api_edit(jid: str, req: EditRequest):
        _job(jid)
        try:
            return job_json(mgr.submit(jid, req.style, req.text, req.strength, req.modifiers, req.formats, req.max_side))
        except KeyError as e:
            raise HTTPException(400, str(e)) from None
        except RuntimeError as e:
            raise HTTPException(409, str(e)) from None

    @app.delete("/api/jobs/{jid}")
    def api_delete(jid: str):
        _job(jid)
        mgr.delete(jid)
        return {"ok": True}

    @app.get("/api/jobs/{jid}/image/{kind}")
    def api_image(jid: str, kind: str):
        _job(jid)
        if kind not in ("before", "after"):
            raise HTTPException(404)
        p = mgr.preview_path(jid, kind)
        if not p.exists():
            raise HTTPException(404, "not ready")
        return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})

    @app.get("/api/jobs/{jid}/option/{style_id}")
    def api_option(jid: str, style_id: str):
        _job(jid)
        try:
            styles.get(style_id)
        except KeyError:
            raise HTTPException(404) from None
        p = mgr.option_path(jid, style_id)
        if not p.exists():
            raise HTTPException(404, "not ready")
        return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})

    @app.get("/api/jobs/{jid}/download/{kind}")
    def api_download(jid: str, kind: str):
        j = _job(jid)
        path = j.outputs.get(kind)
        if not path or not Path(path).exists():
            raise HTTPException(404, "not ready")
        return FileResponse(path, filename=Path(path).name)

    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/manifest.webmanifest")
    def manifest():
        return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js")
    def sw():
        return FileResponse(WEB / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})

    return app


def styles_modifiers():
    from .recipe import MODIFIER_DOC
    return MODIFIER_DOC.keys()
