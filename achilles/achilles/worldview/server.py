"""WorldView — the live geospatial dashboard, served locally.

Fixes for the known blockers, encoded here:

- **Phone access**: the server binds ``ACHILLES_WV_HOST`` (default
  ``0.0.0.0``) and the frontend calls only *relative* URLs, so any device on
  the LAN can open ``http://<machine-ip>:8590/``.  No ``localhost`` anywhere.
- **Bounding-box cap**: the bbox comes from config; ``ACHILLES_WV_BBOX=global``
  removes the Israel cap entirely.
- **Exposed keys**: the OpenWeatherMap key never reaches the browser — cloud
  tiles are proxied through ``/tiles/clouds/...`` and the key is attached
  server-side only.

Zero third-party dependencies: stdlib ``http.server`` + ``urllib``.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..config import WorldViewConfig

STATIC_DIR = Path(__file__).parent / "static"
AIRCRAFT_CACHE_TTL_S = 8.0


class _Cache:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.aircraft: tuple[float, bytes] | None = None  # (fetched_at, payload)


def _fetch(url: str, timeout: float = 12.0, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "achilles-worldview/1.0",
                                               **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def make_handler(config: WorldViewConfig, cache: _Cache):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AchillesWorldView/1.0"

        def log_message(self, fmt, *args):  # keep the console quiet
            pass

        def _send(self, status: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            try:
                self._route()
            except BrokenPipeError:
                pass
            except Exception as exc:
                self._send(502, json.dumps({"error": str(exc)}).encode())

        def _route(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                body = (STATIC_DIR / "index.html").read_bytes()
                self._send(200, body, "text/html; charset=utf-8")
            elif path == "/api/config":
                self._send(200, json.dumps({
                    "bbox": config.bbox_tuple(),
                    "center": [float(x) for x in config.center.split(",")],
                    "zoom": config.zoom,
                    "cloudsEnabled": bool(config.openweathermap_key),
                }).encode())
            elif path == "/api/aircraft":
                self._send(200, self._aircraft())
            elif path.startswith("/tiles/clouds/"):
                self._cloud_tile(path)
            else:
                self._send(404, b'{"error": "not found"}')

        def _aircraft(self) -> bytes:
            now = time.monotonic()
            with cache.lock:
                if cache.aircraft and now - cache.aircraft[0] < AIRCRAFT_CACHE_TTL_S:
                    return cache.aircraft[1]
            lat, lon = (float(x) for x in config.center.split(","))
            url = (f"https://api.airplanes.live/v2/point/"
                   f"{lat:.4f}/{lon:.4f}/{config.aircraft_radius_nm}")
            try:
                raw = json.loads(_fetch(url))
                planes = raw.get("ac") or []
            except Exception:
                planes = []
            features = []
            for p in planes:
                if p.get("lat") is None or p.get("lon") is None:
                    continue
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                    "properties": {
                        "callsign": (p.get("flight") or p.get("r") or "?").strip(),
                        "alt": p.get("alt_baro") or 0,
                        "track": p.get("track") or 0,
                        "speed": p.get("gs") or 0,
                        "military": bool(p.get("dbFlags", 0) & 1),
                    },
                })
            body = json.dumps({"type": "FeatureCollection", "features": features}).encode()
            with cache.lock:
                cache.aircraft = (now, body)
            return body

        def _cloud_tile(self, path: str) -> None:
            if not config.openweathermap_key:
                self._send(404, b'{"error": "clouds disabled"}')
                return
            parts = path.strip("/").split("/")  # tiles/clouds/z/x/y.png
            if len(parts) != 5:
                self._send(400, b'{"error": "bad tile path"}')
                return
            z, x, y = parts[2], parts[3], parts[4].removesuffix(".png")
            if not (z.isdigit() and x.isdigit() and y.isdigit()):
                self._send(400, b'{"error": "bad tile path"}')
                return
            url = (f"https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png"
                   f"?appid={config.openweathermap_key}")
            self._send(200, _fetch(url), "image/png")

    return Handler


def serve(config: WorldViewConfig | None = None) -> None:
    config = config or WorldViewConfig.from_env()
    handler = make_handler(config, _Cache())
    server = ThreadingHTTPServer((config.host, config.port), handler)
    shown_host = config.host if config.host != "0.0.0.0" else "<this-machine's-LAN-IP>"
    print(f"[worldview] serving on http://{shown_host}:{config.port}/ "
          f"(bbox={'global' if config.bbox_tuple() is None else config.bbox})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    serve()
