import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from achilles import skills
from achilles.config import Config, WorldViewConfig, load_dotenv


class TestRouter(unittest.TestCase):
    def test_intent_resolution(self):
        self.assertEqual(skills.resolve_intent("how's the market today"), "market")
        self.assertEqual(skills.resolve_intent("מה קורה בבורסה"), "market")
        self.assertEqual(skills.resolve_intent("volume up please"), "audio")
        self.assertEqual(skills.resolve_intent("log 40 pushups from my workout"), "fitness")
        self.assertIsNone(skills.resolve_intent("tell me a story"))

    def test_dispatch_and_fallback(self):
        router = skills.Router(fallback=lambda c: f"fallback:{c}")
        router.register("market", lambda c: "market!")
        self.assertEqual(router.dispatch("stock check"), "market!")
        self.assertEqual(router.dispatch("tell me a story"), "fallback:tell me a story")

    def test_registered_intent_missing_handler_falls_back(self):
        router = skills.Router(fallback=lambda c: "fb")
        self.assertEqual(router.dispatch("volume up"), "fb")


class TestConfig(unittest.TestCase):
    def test_dotenv_loader_does_not_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            envfile = Path(tmp) / ".env"
            envfile.write_text(
                "# comment\nACHILLES_TEST_A=hello\nACHILLES_TEST_B='quoted'\nBADLINE\n",
                encoding="utf-8")
            with mock.patch.dict(os.environ, {"ACHILLES_TEST_A": "preset"}, clear=False):
                os.environ.pop("ACHILLES_TEST_B", None)
                loaded = load_dotenv(envfile)
                self.assertNotIn("ACHILLES_TEST_A", loaded)  # not overridden
                self.assertEqual(os.environ["ACHILLES_TEST_A"], "preset")
                self.assertEqual(os.environ["ACHILLES_TEST_B"], "quoted")
                os.environ.pop("ACHILLES_TEST_B", None)

    def test_bbox_parsing(self):
        wv = WorldViewConfig(bbox="29.3,33.8,33.4,36.0")
        self.assertEqual(wv.bbox_tuple(), (29.3, 33.8, 33.4, 36.0))
        self.assertIsNone(WorldViewConfig(bbox="global").bbox_tuple())
        with self.assertRaises(ValueError):
            WorldViewConfig(bbox="1,2,3").bbox_tuple()

    def test_from_env_defaults(self):
        cfg = Config.from_env(dotenv=None)
        self.assertEqual(cfg.worldview.host, os.environ.get("ACHILLES_WV_HOST", "0.0.0.0"))
        self.assertEqual(cfg.anthropic_model,
                         os.environ.get("ACHILLES_CLAUDE_MODEL", "claude-opus-4-8"))


if __name__ == "__main__":
    unittest.main()
