import math
import tempfile
import unittest
from pathlib import Path

from achilles.wake.speaker import SpeakerVerifier

SR = 16000


def voice(f0: float, seconds: float = 0.6, harmonics=(1.0, 0.5, 0.25)) -> list[float]:
    """Synthetic 'voice': a fundamental plus harmonics."""
    n = int(SR * seconds)
    return [sum(a * math.sin(2 * math.pi * f0 * (h + 1) * i / SR)
                for h, a in enumerate(harmonics)) / len(harmonics)
            for i in range(n)]


class TestSpeakerVerifier(unittest.TestCase):
    def test_enroll_verify_and_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "profile.json"
            v = SpeakerVerifier(profile, threshold=0.9, sample_rate=SR)
            self.assertFalse(v.enrolled)

            owner = [voice(120), voice(125), voice(118)]
            v.enroll(owner)
            self.assertTrue(v.enrolled)
            self.assertTrue(profile.is_file())

            # Same voice character → accepted
            self.assertTrue(v.verify(voice(122)))
            own_score = v.score(voice(122))

            # Very different spectral character → scored lower
            impostor = voice(600, harmonics=(0.2, 1.0, 0.8, 0.6))
            self.assertLess(v.score(impostor), own_score)

            # Profile persists across instances
            v2 = SpeakerVerifier(profile, threshold=0.9, sample_rate=SR)
            self.assertTrue(v2.enrolled)
            self.assertTrue(v2.verify(voice(121)))

    def test_unenrolled_scores_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = SpeakerVerifier(Path(tmp) / "p.json", sample_rate=SR)
            self.assertEqual(v.score(voice(120)), 0.0)

    def test_enroll_rejects_empty_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = SpeakerVerifier(Path(tmp) / "p.json", sample_rate=SR)
            with self.assertRaises(ValueError):
                v.enroll([[0.0] * 10])


if __name__ == "__main__":
    unittest.main()
