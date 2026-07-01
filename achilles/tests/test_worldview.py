import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from achilles.config import WorldViewConfig
from achilles.worldview import server as wv


class TestWorldViewServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = WorldViewConfig(host="127.0.0.1", port=0,
                                     bbox="29.3,33.8,33.4,36.0",
                                     openweathermap_key="")
        handler = wv.make_handler(cls.config, wv._Cache())
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5)

    def test_index_served(self):
        with self._get("/") as resp:
            body = resp.read().decode()
        self.assertIn("WORLDVIEW", body)
        # The frontend must not hardcode localhost anywhere (phone-access fix)
        self.assertNotIn("localhost", body)
        self.assertNotIn("127.0.0.1", body)

    def test_config_endpoint(self):
        with self._get("/api/config") as resp:
            cfg = json.loads(resp.read())
        self.assertEqual(cfg["bbox"], [29.3, 33.8, 33.4, 36.0])
        self.assertEqual(cfg["center"], [31.5, 34.9])
        self.assertFalse(cfg["cloudsEnabled"])

    def test_config_never_leaks_keys(self):
        config = WorldViewConfig(openweathermap_key="SUPER-SECRET")
        handler = wv.make_handler(config, wv._Cache())
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/config", timeout=5) as r:
                body = r.read().decode()
            self.assertNotIn("SUPER-SECRET", body)
            self.assertIn('"cloudsEnabled": true', body)
        finally:
            server.shutdown()

    def test_clouds_404_when_disabled(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/tiles/clouds/5/19/13.png")
        self.assertEqual(ctx.exception.code, 404)

    def test_unknown_path_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/nope")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
