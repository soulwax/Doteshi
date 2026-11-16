"""The web interface's server."""
import io
import json
import threading
import urllib.error
import urllib.request

import pytest
from PIL import Image

from doteshi.web import server

from test_atlas import PACKED, _project


@pytest.fixture
def site(tmp_path):
    manifest = _project(tmp_path, PACKED.format(dots=2, bars=1))
    httpd = server.start(manifest, tmp_path / "out", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", tmp_path
    httpd.shutdown()
    httpd.server_close()


def _get(url, method="GET"):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method)) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_page_and_sprite_list(site):
    base, _ = site
    status, headers, body = _get(base + "/")
    assert status == 200 and headers["Content-Type"].startswith("text/html") and b"doteshi" in body
    status, _, body = _get(base + "/api/sprites")
    data = json.loads(body)
    assert status == 200 and [s["id"] for s in data["sprites"]] == ["bar", "dot", "slab"]
    assert data["error"] is None and "tiny" in data["styles"] and data["version"]


def test_render(site):
    base, _ = site
    status, headers, body = _get(base + "/api/render?id=bar&size=16&seed=2")
    assert status == 200 and headers["Content-Type"] == "image/png" and headers["X-Style"] == "tiny"
    assert Image.open(io.BytesIO(body)).size == (32, 16)
    assert _get(base + "/api/render?id=bar&size=16&seed=2")[2] == body                    # cached, identical
    assert _get(base + "/api/render?id=bar&size=16&seed=2&style=pixel-hd")[1]["X-Style"] == "pixel-hd"
    for query, code, text in (("id=ghost&size=16", 404, "no sprite named 'ghost'"),
                              ("id=bar&size=4000", 400, "between 8 and 512"),
                              ("id=bar&size=16&style=chunky", 400, "no style named 'chunky'")):
        status, _, body = _get(base + "/api/render?" + query)
        assert status == code and text in json.loads(body)["error"]


def test_bake_and_atlas(site):
    base, tmp = site
    assert json.loads(_get(base + "/api/atlas")[2]) == {"exists": False, "name": "atlas"}
    status, _, body = _get(base + "/api/bake", "POST")
    st = json.loads(body)
    assert status == 200 and st["sprites"] == 5 and st["new"] == 5
    atlas = json.loads(_get(base + "/api/atlas")[2])
    assert atlas["exists"] and len(atlas["sprites"]) == 5 and atlas["files"] == ["atlas.png", "atlas.json", "atlas.gen.hpp"]
    status, headers, body = _get(base + "/api/atlas/file/atlas.png")
    assert status == 200 and body == (tmp / "out" / "atlas.png").read_bytes()
    assert json.loads(_get(base + "/api/bake", "POST")[2])["kept"] == 5
    for path in ("/api/atlas/file/atlas.lock.json", "/api/atlas/file/..%2Fmanifest.toml", "/api/nothing"):
        assert _get(base + path)[0] == 404


def test_edited_definitions_are_picked_up(site):
    base, tmp = site
    before = json.loads(_get(base + "/api/sprites")[2])
    file = tmp / "sprites" / "shapes.py"
    file.write_text(file.read_text(encoding="utf-8") + '''
@sprite("ring")
def ring(s, rng):
    s.part(sdf.circle(0.7) - sdf.circle(0.4), mat.metal("#d9a441"))
''', encoding="utf-8")
    after = json.loads(_get(base + "/api/sprites")[2])
    assert "ring" in [s["id"] for s in after["sprites"]] and after["version"] != before["version"]
    assert _get(base + "/api/render?id=ring&size=32")[0] == 200
    file.write_text("def broken(:", encoding="utf-8")
    broken = json.loads(_get(base + "/api/sprites")[2])
    assert broken["sprites"] == [] and "SyntaxError" in broken["error"]
