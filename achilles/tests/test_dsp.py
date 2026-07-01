import cmath
import math
import unittest

from achilles.audio import dsp


def naive_dft(x):
    n = len(x)
    return [sum(x[t] * cmath.exp(-2j * math.pi * k * t / n) for t in range(n))
            for k in range(n)]


class TestFFT(unittest.TestCase):
    def test_matches_naive_dft(self):
        x = [complex(math.sin(0.3 * i) + 0.1 * i, 0.0) for i in range(16)]
        got = dsp.fft(x)
        want = naive_dft(x)
        for g, w in zip(got, want):
            self.assertAlmostEqual(g.real, w.real, places=8)
            self.assertAlmostEqual(g.imag, w.imag, places=8)

    def test_rejects_non_power_of_two(self):
        with self.assertRaises(ValueError):
            dsp.fft([0j] * 12)

    def test_pure_tone_peak_bin(self):
        n, sr, freq = 256, 16000, 1000.0
        x = [complex(math.sin(2 * math.pi * freq * i / sr), 0) for i in range(n)]
        mags = [abs(c) for c in dsp.fft(x)[: n // 2]]
        peak = mags.index(max(mags))
        self.assertEqual(peak, round(freq * n / sr))


class TestPcmAndRms(unittest.TestCase):
    def test_pcm16_roundtrip(self):
        import struct

        values = [0, 1000, -1000, 32767, -32768]
        data = struct.pack("<5h", *values)
        floats = dsp.pcm16_to_float(data)
        self.assertEqual(len(floats), 5)
        self.assertAlmostEqual(floats[0], 0.0)
        self.assertAlmostEqual(floats[3], 32767 / 32768.0)
        self.assertAlmostEqual(floats[4], -1.0)

    def test_rms(self):
        self.assertEqual(dsp.rms([]), 0.0)
        self.assertAlmostEqual(dsp.rms([0.5, -0.5, 0.5, -0.5]), 0.5)


class TestMfcc(unittest.TestCase):
    def test_shapes_and_determinism(self):
        sr = 16000
        sig = [math.sin(2 * math.pi * 220 * i / sr) for i in range(sr // 2)]
        frames = dsp.mfcc(sig, sample_rate=sr)
        self.assertGreater(len(frames), 10)
        self.assertTrue(all(len(f) == 13 for f in frames))
        self.assertEqual(frames, dsp.mfcc(sig, sample_rate=sr))

    def test_too_short_returns_empty(self):
        self.assertEqual(dsp.mfcc([0.0] * 100, sample_rate=16000), [])


class TestCosine(unittest.TestCase):
    def test_identical_and_orthogonal(self):
        self.assertAlmostEqual(dsp.cosine_similarity([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(dsp.cosine_similarity([1, 0], [0, 1]), 0.0)
        self.assertEqual(dsp.cosine_similarity([0, 0], [1, 1]), 0.0)


if __name__ == "__main__":
    unittest.main()
