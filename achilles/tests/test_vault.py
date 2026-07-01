import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from achilles.config import MemoryConfig
from achilles.memory import vault as vault_mod
from achilles.memory.vault import Vault


class TestVault(unittest.TestCase):
    def test_log_and_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = MemoryConfig(vault_path=f"{tmp}/vault",
                               audio_archive_path=f"{tmp}/hdd")
            v = Vault(cfg)
            when = datetime(2026, 7, 1, 9, 30, 0)
            note = v.log_exchange("remind me about the marantz receiver",
                                  "Receiver noted.", when=when)
            self.assertTrue(note.is_file())
            self.assertIn("2026-07-01", note.name)
            v.log_exchange("what's the market doing", "S&P is up.", when=when)
            text = note.read_text(encoding="utf-8")
            self.assertEqual(text.count("## "), 2)

            hits = vault_mod.search(cfg.vault_path, "marantz")
            self.assertEqual(len(hits), 1)
            self.assertIn("marantz", hits[0][1].lower())
            self.assertEqual(vault_mod.search(cfg.vault_path, "zzznope"), [])

    def test_audio_tier_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            # point the HDD tier at an uncreatable path → falls back to vault tier
            cfg = MemoryConfig(vault_path=f"{tmp}/vault",
                               audio_archive_path="/proc/definitely/not/writable")
            v = Vault(cfg)
            target = v.archive_audio(b"\x00\x01", when=datetime(2026, 7, 1, 9, 0, 0))
            self.assertTrue(target.is_file())
            self.assertIn("_audio_overflow", str(target))

    def test_audio_tier_primary(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = MemoryConfig(vault_path=f"{tmp}/vault",
                               audio_archive_path=f"{tmp}/hdd")
            v = Vault(cfg)
            target = v.archive_audio(b"\x00\x01")
            self.assertTrue(str(target).startswith(f"{tmp}/hdd"))


if __name__ == "__main__":
    unittest.main()
