import unittest

from achilles.config import WakeConfig
from achilles.wake.decision import WakeDecisionMachine, WakeEvent


def cfg(**kw):
    base = dict(wake_word="achilles", min_confidence=0.85, rms_gate=0.01,
                cooldown_s=3.0, noise_backoff_after=3, noise_backoff_s=10.0)
    base.update(kw)
    return WakeConfig(**base)


def ev(t, text="achilles", conf=0.95, rms=0.1, final=True):
    return WakeEvent(is_final=final, text=text, confidence=conf, rms=rms, timestamp=t)


class TestWakeDecision(unittest.TestCase):
    def test_clean_trigger(self):
        m = WakeDecisionMachine(cfg())
        d = m.observe(ev(t=100.0))
        self.assertTrue(d.triggered)

    def test_partials_never_trigger(self):
        m = WakeDecisionMachine(cfg())
        d = m.observe(ev(t=100.0, final=False))
        self.assertFalse(d.triggered)
        self.assertEqual(d.reason, "partial-ignored")

    def test_rms_gate(self):
        m = WakeDecisionMachine(cfg())
        d = m.observe(ev(t=100.0, rms=0.001))
        self.assertEqual(d.reason, "rms-gate")

    def test_wrong_word(self):
        m = WakeDecisionMachine(cfg())
        d = m.observe(ev(t=100.0, text="hercules"))
        self.assertEqual(d.reason, "no-wake-word")

    def test_wake_word_must_be_a_word_not_substring(self):
        m = WakeDecisionMachine(cfg())
        d = m.observe(ev(t=100.0, text="achillesheel"))
        self.assertFalse(d.triggered)

    def test_cooldown_suppresses_double_fire(self):
        m = WakeDecisionMachine(cfg())
        self.assertTrue(m.observe(ev(t=100.0)).triggered)
        d = m.observe(ev(t=101.0))
        self.assertEqual(d.reason, "cooldown")
        self.assertTrue(m.observe(ev(t=104.5)).triggered)

    def test_low_confidence_rejected(self):
        m = WakeDecisionMachine(cfg())
        d = m.observe(ev(t=100.0, conf=0.5))
        self.assertEqual(d.reason, "low-confidence")

    def test_noise_backoff_storm(self):
        """A media bed spamming near-matches arms the backoff and goes quiet."""
        m = WakeDecisionMachine(cfg(noise_backoff_after=3, noise_backoff_s=10.0))
        self.assertEqual(m.observe(ev(t=1.0, conf=0.4)).reason, "low-confidence")
        self.assertEqual(m.observe(ev(t=2.0, conf=0.4)).reason, "low-confidence")
        self.assertEqual(m.observe(ev(t=3.0, conf=0.4)).reason, "low-confidence-backoff-armed")
        # Even a perfect match is ignored during backoff...
        self.assertEqual(m.observe(ev(t=5.0, conf=0.99)).reason, "noise-backoff")
        # ...and works again after it expires.
        self.assertTrue(m.observe(ev(t=13.5, conf=0.99)).triggered)

    def test_good_trigger_resets_reject_streak(self):
        m = WakeDecisionMachine(cfg(noise_backoff_after=3))
        m.observe(ev(t=1.0, conf=0.4))
        m.observe(ev(t=2.0, conf=0.4))
        self.assertTrue(m.observe(ev(t=3.0, conf=0.99)).triggered)
        # streak was reset; two more rejects don't arm backoff
        self.assertEqual(m.observe(ev(t=7.0, conf=0.4)).reason, "low-confidence")
        self.assertEqual(m.observe(ev(t=8.0, conf=0.4)).reason, "low-confidence")


if __name__ == "__main__":
    unittest.main()
