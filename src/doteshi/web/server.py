"""The web interface's server: a small local HTTP server over the same functions the command line uses.

    GET  /                       the page
    GET  /api/sprites            registered sprites and style names
    GET  /api/render             one sprite as PNG: ?id=&size=&seed=&style=
    GET  /api/atlas              the last bake: pages and sprite rectangles
    GET  /api/atlas/file/<name>  one of the baked files
    POST /api/bake               bake the manifest; ?repack=1 lays everything out again

Sprite definitions are re-imported whenever a file in the content folder changes, so editing a definition and
looking again in the browser is enough. It listens on this machine only unless told otherwise.
"""
import hashlib
import io
import json
import threading
import time
import tomllib
import traceback
import webbrowser
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .. import api
from ..atlas import bake
from ..resolve.style import STYLES, get

PAGE = Path(__file__).with_name("index.html")
MAX_SIZE = 512
CACHE = 600


class App:
    def __init__(self, manifest, out_dir):
        self.manifest = Path(manifest)
        self.out = Path(out_dir)
        settings = tomllib.loads(self.manifest.read_text(encoding="utf-8")).get("atlas", {})
        self.content = self.manifest.parent / settings.get("content", ".")
        self.name = settings.get("name", "atlas")
        self.busy = threading.Lock()         # one render or bake at a time: the registry is shared
        self.cache = OrderedDict()
        self.stamp = None
        self.error = None

    def refresh(self):
        """Re-import the content folder if any file in it changed."""
        stamp = tuple((str(f), f.stat().st_mtime_ns, f.stat().st_size) for f in sorted(self.content.rglob("*.py")))
        if stamp == self.stamp:
            return
        self.stamp = stamp
        self.cache.clear()
        try:
            api.reload(self.content)
            self.error = None
        except Exception:
            self.error = traceback.format_exc(limit=3)

    def sprites(self):
        with self.busy:
            self.refresh()
            items = [{"id": d.id, "sizes": list(d.sizes), "variants": d.variants, "aspect": d.aspect}
                     for _, d in sorted(api.REGISTRY.items())]
        version = hashlib.sha256(repr(self.stamp).encode()).hexdigest()[:12]      # changes when content does
        return {"sprites": items, "styles": list(STYLES), "error": self.error, "manifest": str(self.manifest),
                "version": version}

    def render(self, id, size, seed, style):
        with self.busy:
            self.refresh()
            if id not in api.REGISTRY:
                raise KeyError(f"no sprite named '{id}'")
            if not 8 <= size <= MAX_SIZE:
                raise ValueError(f"size must be between 8 and {MAX_SIZE}")
            key = (id, size, seed, style)
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            start = time.perf_counter()
            image = api.render(id, size, seed, style)
            data = io.BytesIO()
            image.save(data, format="PNG")
            used = get(style if style else api.REGISTRY[id].style, size).name if (id, size) not in api.OVERRIDES \
                or style else "hand-drawn"
            self.cache[key] = (data.getvalue(), used, time.perf_counter() - start)
            while len(self.cache) > CACHE:
                self.cache.popitem(last=False)
            return self.cache[key]

    def atlas(self):
        file = self.out / f"{self.name}.json"
        if not file.exists():
            return {"exists": False, "name": self.name}
        data = json.loads(file.read_text(encoding="utf-8"))
        files = [p["file"] for p in data["pages"]] + [f"{self.name}.json", f"{self.name}.gen.hpp"]
        return {"exists": True, "name": self.name, "files": files, "stamp": file.stat().st_mtime_ns, **data}

    def file(self, name):
        allowed = self.atlas().get("files", [])
        if name not in allowed:
            raise KeyError(f"no baked file named '{name}'")
        return (self.out / name).read_bytes()

    def bake(self, repack):
        with self.busy:
            self.refresh()
            start = time.perf_counter()
            _, st = bake.bake(self.manifest, self.out, repack=repack)
            return {"sprites": st["sprites"], "pages": st["pages"], "new": st["new"], "kept": st["kept"],
                    "moved": st["moved"], "retired": st["retired"], "fill": st["fill"],
                    "seconds": time.perf_counter() - start}


TYPES = {".png": "image/png", ".json": "application/json", ".hpp": "text/plain; charset=utf-8"}


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, body, kind="application/json", status=200, headers=()):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in headers:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def fail(self, error):
            status = 404 if isinstance(error, KeyError) else 400 if isinstance(error, ValueError) else 500
            text = str(error.args[0]) if isinstance(error, KeyError) and error.args else str(error)
            self.send({"error": text or type(error).__name__}, status=status)

        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path in ("/", "/index.html"):
                    self.send(PAGE.read_bytes(), "text/html; charset=utf-8")
                elif url.path == "/api/sprites":
                    self.send(app.sprites())
                elif url.path == "/api/render":
                    data, used, took = app.render(q.get("id", ""), int(q.get("size", 64)), int(q.get("seed", 0)),
                                                  q.get("style") or None)
                    self.send(data, "image/png", headers=(("X-Style", used), ("X-Seconds", f"{took:.3f}")))
                elif url.path == "/api/atlas":
                    self.send(app.atlas())
                elif url.path.startswith("/api/atlas/file/"):
                    name = url.path.rsplit("/", 1)[1]
                    self.send(app.file(name), TYPES.get(Path(name).suffix, "application/octet-stream"))
                else:
                    self.send({"error": "not found"}, status=404)
            except Exception as error:
                self.fail(error)

        def do_POST(self):
            url = urlparse(self.path)
            try:
                if url.path == "/api/bake":
                    self.send(app.bake("repack=1" in url.query))
                else:
                    self.send({"error": "not found"}, status=404)
            except Exception as error:
                self.fail(error)

    return Handler


def start(manifest, out_dir="out", host="127.0.0.1", port=8765):
    """Create the server without running it. Port 0 picks a free port."""
    return ThreadingHTTPServer((host, port), handler(App(manifest, out_dir)))


def serve(manifest, out_dir="out", host="127.0.0.1", port=8765, open_browser=False):
    app = App(manifest, out_dir)
    httpd = ThreadingHTTPServer((host, port), handler(app))
    url = f"http://{host}:{port}/"
    print(f"doteshi is serving {app.manifest} at {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    finally:
        httpd.server_close()
