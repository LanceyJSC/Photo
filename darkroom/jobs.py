"""Background job manager and watch-folder.

Photos are edited on a worker thread (NumPy/OpenCV release the GIL) so the UI
and the user stay free.  Job state is persisted to disk, so a restart resumes
unfinished work.
"""
from __future__ import annotations

import json
import re
import shutil
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import color, edit, export, pipeline, raw, recommend, styles

PREVIEW_SIDE = 1800
THUMB_SIDE = 900


@dataclass
class Job:
    id: str
    name: str
    src: str
    status: str = "awaiting_style"      # awaiting_style | queued | running | done | error
    stage: str = ""
    progress: float = 0.0
    style: str | None = None
    text: str | None = None
    strength: float = 1.0
    modifiers: dict = field(default_factory=dict)
    formats: list = field(default_factory=lambda: ["jpg"])
    max_side: int | None = None
    notes: list = field(default_factory=list)
    analysis: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    error: str = ""
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    version: int = 0                     # bumps whenever previews change (cache-busting)
    size: list = field(default_factory=list)
    has_preview: bool = False
    has_thumb: bool = False
    kind: str = ""                      # portrait | landscape | architecture | night | street
    recommended: list = field(default_factory=list)
    options_ready: list = field(default_factory=list)
    options_done: bool = False


def _safe_name(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .") or "photo"
    return name[:120]


class JobManager:
    def __init__(self, root: str | Path, workers: int = 1):
        self.root = Path(root)
        for d in ("uploads", "outputs", "previews"):
            (self.root / d).mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="darkroom")
        self.opt_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="darkroom-looks")   # look previews never block real edits
        self._state = self.root / "jobs.json"
        self._load()

    # ------------------------------------------------------------ persistence
    def _load(self):
        if not self._state.exists():
            return
        try:
            data = json.loads(self._state.read_text())
        except Exception:
            return
        for d in data:
            try:
                job = Job(**d)
            except TypeError:
                continue
            if job.status in ("queued", "running"):
                job.status = "queued"
                self.jobs[job.id] = job
                self.pool.submit(self._run, job.id)
            else:
                self.jobs[job.id] = job

    def _save(self):
        with self.lock:
            tmp = self._state.with_suffix(".tmp")
            tmp.write_text(json.dumps([asdict(j) for j in self.jobs.values()], indent=1))
            tmp.replace(self._state)

    # ------------------------------------------------------------ public API
    def add(self, filename: str, data_path: str | Path | None = None, content: bytes | None = None) -> Job:
        name = _safe_name(filename)
        if not raw.is_supported(name):
            raise ValueError(f"Unsupported file type: {Path(name).suffix or name}")
        jid = uuid.uuid4().hex[:12]
        dest_dir = self.root / "uploads" / jid
        dest_dir.mkdir(parents=True)
        dest = dest_dir / name
        if content is not None:
            dest.write_bytes(content)
        elif data_path is not None:
            shutil.copy2(data_path, dest)
        job = Job(id=jid, name=name, src=str(dest))
        with self.lock:
            self.jobs[jid] = job
            self._save()
        self.pool.submit(self._make_thumb, jid)
        self.opt_pool.submit(self._make_options, jid)
        return job

    def get(self, jid: str) -> Job:
        with self.lock:
            return self.jobs[jid]

    def list(self) -> list[Job]:
        with self.lock:
            return sorted(self.jobs.values(), key=lambda j: j.created, reverse=True)

    def submit(self, jid: str, style: str | None = None, text: str | None = None, strength: float = 1.0,
               modifiers: dict | None = None, formats: list | None = None, max_side: int | None = None) -> Job:
        job = self.get(jid)
        if job.status == "running":
            raise RuntimeError("job is already running")
        if not style and not text:
            style = styles.DEFAULT_STYLE
        if style:
            styles.get(style)            # validate early
        with self.lock:
            job.style, job.text = style, text
            job.strength = float(max(0.0, min(1.5, strength)))
            job.modifiers = {k: float(v) for k, v in (modifiers or {}).items()}
            job.formats = [f for f in (formats or ["jpg"]) if f in ("jpg", "tif", "png")] or ["jpg"]
            job.max_side = int(max_side) if max_side else None
            job.status, job.progress, job.stage, job.error = "queued", 0.0, "queued", ""
            job.updated = time.time()
            self._save()
        self.pool.submit(self._run, jid)
        return job

    def delete(self, jid: str):
        with self.lock:
            job = self.jobs.pop(jid, None)
            self._save()
        if job:
            shutil.rmtree(self.root / "uploads" / jid, ignore_errors=True)
            shutil.rmtree(self.root / "outputs" / jid, ignore_errors=True)
            shutil.rmtree(self.root / "previews" / jid, ignore_errors=True)

    def preview_path(self, jid: str, kind: str) -> Path:
        return self.root / "previews" / jid / f"{kind}.jpg"

    # ------------------------------------------------------------ workers
    def _update(self, job: Job, **kw):
        with self.lock:
            for k, v in kw.items():
                setattr(job, k, v)
            job.updated = time.time()

    def _make_thumb(self, jid: str):
        job = self.jobs.get(jid)
        if job is None:
            return
        try:
            ph, _ = edit._load(job.src, THUMB_SIDE)
            enc = pipeline.quantize8(color.pro_to_display(ph.rgb))
            d = self.root / "previews" / jid
            d.mkdir(parents=True, exist_ok=True)
            (d / "before.jpg").write_bytes(export.jpeg_bytes(enc, 85))
            self._update(job, has_thumb=True, size=[ph.rgb.shape[1], ph.rgb.shape[0]], version=job.version + 1)
        except Exception as e:  # noqa: BLE001 - surfaced to the UI instead
            self._update(job, status="error", error=f"Could not read this file: {e}")
        self._save()

    def option_path(self, jid: str, style_id: str) -> Path:
        return self.root / "previews" / jid / "opt" / f"{style_id}.jpg"

    def _make_options(self, jid: str):
        """Render the photo in the best-fitting looks first, then the whole library."""
        job = self.jobs.get(jid)
        if job is None:
            return
        d = self.root / "previews" / jid / "opt"
        d.mkdir(parents=True, exist_ok=True)

        def order(an, rgb):
            kind, rec = recommend.recommend(an, rgb)
            self._update(job, kind=kind, recommended=rec)
            self._save()
            return rec + [s.id for s in styles.STYLES if s.id not in rec]

        def ready(sid, jpg):
            (d / f"{sid}.jpg").write_bytes(jpg)
            with self.lock:
                if sid not in job.options_ready:
                    job.options_ready.append(sid)

        try:
            edit.option_previews(job.src, order, 640, ready)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            if job.status == "awaiting_style":
                self._update(job, status="error", error=f"Could not prepare looks: {e}")
        self._update(job, options_done=True)
        self._save()

    def _run(self, jid: str):
        job = self.jobs.get(jid)
        if job is None:
            return
        try:
            self._update(job, status="running", stage="analysing", progress=0.02)
            self._save()
            pdir = self.root / "previews" / jid
            pdir.mkdir(parents=True, exist_ok=True)

            # 1) fast preview so the user sees the look in seconds
            jpg, info = edit.preview(job.src, job.style, job.text, job.strength, job.modifiers, side=PREVIEW_SIDE)
            (pdir / "after.jpg").write_bytes(jpg)
            self._update(job, has_preview=True, notes=info["notes"], analysis=info["analysis"],
                         version=job.version + 1, stage="rendering full resolution", progress=0.15)

            # 2) full resolution export in the background
            out_dir = self.root / "outputs" / jid
            if out_dir.exists():
                shutil.rmtree(out_dir)

            def cb(stage, frac):
                self._update(job, stage=stage, progress=0.15 + 0.85 * frac)

            res = edit.process(job.src, out_dir, job.style, job.text, job.strength, job.modifiers,
                               formats=tuple(job.formats), max_side=job.max_side, progress=cb)
            self._update(job, status="done", stage="done", progress=1.0, outputs=res.outputs,
                         notes=res.notes, size=list(res.size), analysis=res.analysis)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._update(job, status="error", error=str(e), stage="failed")
        self._save()


class Watcher(threading.Thread):
    """Poll an inbox folder; edit every new photo with a fixed look into an outbox."""

    def __init__(self, inbox: Path, outbox: Path, style: str | None, text: str | None, strength: float = 1.0,
                 formats=("jpg",), interval: float = 2.0, log=print):
        super().__init__(daemon=True)
        self.inbox, self.outbox = Path(inbox), Path(outbox)
        self.style, self.text, self.strength, self.formats = style, text, strength, tuple(formats)
        self.interval, self.log = interval, log
        self._seen: dict[str, tuple[int, float]] = {}
        self._done: set[str] = set()
        self.stop_event = threading.Event()
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)

    def run(self):
        while not self.stop_event.is_set():
            self.scan()
            self.stop_event.wait(self.interval)

    def scan(self):
        for p in sorted(self.inbox.iterdir()):
            if not p.is_file() or not raw.is_supported(p) or str(p) in self._done:
                continue
            st = p.stat()
            key = (st.st_size, st.st_mtime)
            if self._seen.get(str(p)) != key:      # still being copied; wait for a stable size
                self._seen[str(p)] = key
                continue
            self._done.add(str(p))
            try:
                self.log(f"[watch] editing {p.name}")
                res = edit.process(p, self.outbox, self.style, self.text, self.strength, formats=self.formats)
                self.log(f"[watch] done {p.name} -> {Path(next(iter(res.outputs.values()))).name} ({res.seconds:.1f}s)")
            except Exception as e:  # noqa: BLE001
                self.log(f"[watch] FAILED {p.name}: {e}")
