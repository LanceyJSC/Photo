"""Command line: ``darkroom edit``, ``darkroom serve``, ``darkroom watch``, ``darkroom styles``."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from . import raw, styles


def _ask_look() -> tuple[str | None, str | None]:
    """Interactive 'what look are you going for?' prompt."""
    print("\nWhat look are you going for?\n")
    n = 0
    index = {}
    cat = None
    for s in styles.STYLES:
        if s.category != cat:
            cat = s.category
            print(f"  {cat}")
        n += 1
        index[str(n)] = s
        print(f"    {n:>2}. {s.name:<44} {s.description[:70]}")
    print("\nPick a number, a style id, or just describe it (e.g. 'moody black and white street, grainy').")
    while True:
        ans = input("> ").strip()
        if not ans:
            continue
        if ans in index:
            return index[ans].id, None
        try:
            styles.get(ans)
            return ans, None
        except KeyError:
            pass
        s, mods, _ = styles.match(ans)
        print(f"  -> {s.name}" + (f"  (+ {', '.join(f'{k} {v:+.1f}' for k, v in mods.items())})" if mods else ""))
        if input("  use this? [Y/n] ").strip().lower() in ("", "y", "yes"):
            return None, ans


def cmd_edit(a):
    from . import edit
    files = []
    for f in a.files:
        p = Path(f)
        if p.is_dir():
            files += sorted(x for x in p.iterdir() if raw.is_supported(x))
        else:
            files.append(p)
    if not files:
        sys.exit("no supported photos given")
    style, text = a.style, a.look
    if not style and not text:
        if sys.stdin.isatty():
            style, text = _ask_look()
        else:
            style = styles.DEFAULT_STYLE
    mods = {}
    for m in ("brightness", "contrast", "warmth", "saturation", "grain", "fade", "clarity", "vignette"):
        v = getattr(a, m)
        if v:
            mods[m] = v
    fmts = tuple(x.strip() for x in a.format.split(","))
    for p in files:
        t = time.time()

        def prog(stage, frac, name=p.name):
            if not a.quiet:
                print(f"\r  {name}: {stage:<28} {int(frac * 100):>3}%", end="", flush=True)

        res = edit.process(p, a.out, style, text, a.strength, mods, fmts, a.max_side, prog)
        print(f"\r  {p.name}: done in {time.time() - t:.1f}s -> {', '.join(Path(v).name for k, v in res.outputs.items() if k != 'sidecar')}      ")
        if a.explain:
            for n in res.notes:
                print("     •", n)


def cmd_styles(a):
    cat = None
    for s in styles.STYLES:
        if s.category != cat:
            cat = s.category
            print(f"\n{cat}")
        print(f"  {s.id:<20} {s.name}\n  {'':<20} {s.description}")


def _lan_ip() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
            sk.connect(("10.255.255.255", 1))
            return sk.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def cmd_serve(a):
    import secrets
    import uvicorn
    from .server import create_app
    host = "0.0.0.0" if a.lan else a.host
    token = None if a.no_token else (a.token or os.environ.get("DARKROOM_TOKEN") or (secrets.token_urlsafe(9) if (a.lan or host not in ("127.0.0.1", "localhost", "::1")) else None))
    url = f"http://{_lan_ip() if host == '0.0.0.0' else host}:{a.port}/" + (f"?token={token}" if token else "")
    print(f"Darkroom running (data in {a.data})\n  open: {url}")
    if a.lan:
        print("  Phone on the same Wi-Fi? Scan this, then 'Add to Home Screen':\n")
        try:
            import segno
            segno.make(url, error="m").terminal(compact=True)
        except Exception:  # noqa: BLE001 - QR is a nicety
            pass
        print("  (the link contains a private token; anyone with it can use the editor)")
    uvicorn.run(create_app(a.data, a.workers, token), host=host, port=a.port, log_level="warning")


def cmd_watch(a):
    from .jobs import Watcher
    style, text = a.style, a.look
    if not style and not text:
        style, text = _ask_look() if sys.stdin.isatty() else (styles.DEFAULT_STYLE, None)
    w = Watcher(a.inbox, a.outbox, style, text, a.strength, tuple(a.format.split(",")))
    print(f"Watching {a.inbox} -> {a.outbox}  (Ctrl-C to stop)")
    w.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        w.stop_event.set()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="darkroom", description="Pro RAW photo editor that grades in the style you ask for.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("edit", help="edit photos")
    e.add_argument("files", nargs="+")
    e.add_argument("-s", "--style", help="style id (see `darkroom styles`)")
    e.add_argument("-l", "--look", help="describe the look in words")
    e.add_argument("--strength", type=float, default=1.0, help="0..1.5 (default 1)")
    e.add_argument("-o", "--out", default="out")
    e.add_argument("-f", "--format", default="jpg", help="jpg,tif,png (comma separated)")
    e.add_argument("--max-side", type=int)
    e.add_argument("--explain", action="store_true", help="print the editing decisions")
    e.add_argument("-q", "--quiet", action="store_true")
    for m in ("brightness", "contrast", "warmth", "saturation", "grain", "fade", "clarity", "vignette"):
        e.add_argument(f"--{m}", type=float, default=0.0, help=f"-1..1 {m} adjustment")
    e.set_defaults(fn=cmd_edit)

    s = sub.add_parser("styles", help="list the style library")
    s.set_defaults(fn=cmd_styles)

    v = sub.add_parser("serve", help="start the web app")
    v.add_argument("--host", default="127.0.0.1")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--data", default="darkroom_data")
    v.add_argument("--workers", type=int, default=1)
    v.add_argument("--lan", action="store_true", help="listen on the local network (for your phone) behind a private link/QR code")
    v.add_argument("--no-token", action="store_true", help="disable the access token (only behind an already-private tunnel)")
    v.add_argument("--token", help="require this access token (auto-generated with --lan)")
    v.set_defaults(fn=cmd_serve)

    w = sub.add_parser("watch", help="edit everything dropped into a folder")
    w.add_argument("inbox")
    w.add_argument("outbox")
    w.add_argument("-s", "--style")
    w.add_argument("-l", "--look")
    w.add_argument("--strength", type=float, default=1.0)
    w.add_argument("-f", "--format", default="jpg")
    w.set_defaults(fn=cmd_watch)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
