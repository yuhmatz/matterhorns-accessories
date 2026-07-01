import unittest

from achilles.skills import market


class TestRsi(unittest.TestCase):
    def test_all_gains_is_100(self):
        closes = [float(i) for i in range(1, 20)]
        self.assertEqual(market.rsi(closes), 100.0)

    def test_all_losses_is_0(self):
        closes = [float(i) for i in range(20, 1, -1)]
        self.assertAlmostEqual(market.rsi(closes), 0.0, places=6)

    def test_known_wilder_series(self):
        # Classic Wilder example series (14-period RSI ≈ 70.46 at the 15th close)
        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        self.assertAlmostEqual(market.rsi(closes), 70.46, delta=0.1)

    def test_needs_enough_data(self):
        with self.assertRaises(ValueError):
            market.rsi([1.0] * 10)


class TestEmaMacd(unittest.TestCase):
    def test_ema_constant_series(self):
        self.assertTrue(all(abs(v - 5.0) < 1e-9 for v in market.ema([5.0] * 40, 12)))

    def test_ema_short_input_empty(self):
        self.assertEqual(market.ema([1.0, 2.0], 12), [])

    def test_macd_constant_series_is_zero(self):
        m, s, h = market.macd([100.0] * 60)
        self.assertAlmostEqual(m, 0.0)
        self.assertAlmostEqual(s, 0.0)
        self.assertAlmostEqual(h, 0.0)

    def test_macd_uptrend_positive(self):
        closes = [100.0 + i * 0.5 for i in range(80)]
        m, s, h = market.macd(closes)
        self.assertGreater(m, 0.0)

    def test_macd_needs_enough_data(self):
        with self.assertRaises(ValueError):
            market.macd([1.0] * 20)


if __name__ == "__main__":
    unittest.main()
