"""Wake-word decision logic — the "v4.73 hardening" as a pure state machine.

The live build over-triggered on background video/music because it acted on
Vosk *partial* results with no gating.  This module encodes the hardened
policy and nothing else (no audio, no Vosk), so it is fully unit-testable:

1. **Final-only** — only final recognizer results are ever considered.
2. **RMS gate** — blocks quieter than the gate are ignored outright.
3. **Confidence floor** — the wake word must be recognized with word-level
   confidence >= ``min_confidence``.
4. **Cooldown** — after a trigger, further triggers are suppressed for
   ``cooldown_s`` so one utterance can't fire twice.
5. **Noise backoff** — repeated *rejected* candidates (media chatter that
   keeps almost-matching) put the engine to sleep for ``noise_backoff_s``.
6. **Speaker gate** (optional, applied by the engine) — the final layer that
   makes this durable: only the owner's voice may pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import WakeConfig


@dataclass
class WakeEvent:
    """One candidate observation handed to the decision machine."""

    is_final: bool
    text: str
    confidence: float
    rms: float
    timestamp: float  # seconds, monotonic


@dataclass
class WakeDecision:
    triggered: bool
    reason: str


@dataclass
class WakeDecisionMachine:
    config: WakeConfig
    _last_trigger_at: float = field(default=float("-inf"), init=False)
    _rejects_in_row: int = field(default=0, init=False)
    _backoff_until: float = field(default=float("-inf"), init=False)

    def observe(self, event: WakeEvent) -> WakeDecision:
        cfg = self.config

        if event.timestamp < self._backoff_until:
            return WakeDecision(False, "noise-backoff")

        if not event.is_final:
            return WakeDecision(False, "partial-ignored")

        if event.rms < cfg.rms_gate:
            return WakeDecision(False, "rms-gate")

        if cfg.wake_word.lower() not in event.text.lower().split():
            return WakeDecision(False, "no-wake-word")

        if event.timestamp - self._last_trigger_at < cfg.cooldown_s:
            return WakeDecision(False, "cooldown")

        if event.confidence < cfg.min_confidence:
            self._rejects_in_row += 1
            if self._rejects_in_row >= cfg.noise_backoff_after:
                self._backoff_until = event.timestamp + cfg.noise_backoff_s
                self._rejects_in_row = 0
                return WakeDecision(False, "low-confidence-backoff-armed")
            return WakeDecision(False, "low-confidence")

        self._rejects_in_row = 0
        self._last_trigger_at = event.timestamp
        return WakeDecision(True, "triggered")
