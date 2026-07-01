"""Wake + command listening engine.

Two interchangeable engines behind one interface:

- ``VoskWakeEngine`` — the real thing: streams microphone PCM into a
  grammar-constrained Vosk recognizer (``["<wake word>", "[unk]"]``), applies
  the :class:`~achilles.wake.decision.WakeDecisionMachine` gates on *final*
  results only, then (optionally) the speaker-verification gate.
- ``TextWakeEngine`` — a keyboard fallback so the whole assistant can be
  developed and tested on machines with no microphone (like this repo's CI).

Vosk ships version-independent wheels, so it installs cleanly on Python 3.14;
it is still an *optional* import so that everything else works without it.
"""
from __future__ import annotations

import json
import time
from typing import Callable, Iterator, Optional

from ..audio import dsp
from ..config import WakeConfig
from .decision import WakeDecisionMachine, WakeEvent
from .speaker import SpeakerVerifier


class TextWakeEngine:
    """Type commands instead of speaking them. ``quit`` exits."""

    def __init__(self, config: WakeConfig) -> None:
        self.config = config

    def listen(self) -> Iterator[str]:
        print("[achilles] text mode — type a command (or 'quit'):")
        while True:
            try:
                line = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not line:
                continue
            if line.lower() in ("quit", "exit"):
                return
            yield line


class VoskWakeEngine:
    """Always-on wake word listening with the hardened v4.73+ policy."""

    def __init__(self, config: WakeConfig, verifier: Optional[SpeakerVerifier] = None,
                 on_state: Callable[[str], None] | None = None) -> None:
        self.config = config
        self.verifier = verifier
        self.decision = WakeDecisionMachine(config)
        self.on_state = on_state or (lambda s: None)

    def _make_recognizer(self):
        from vosk import KaldiRecognizer, Model, SetLogLevel  # deferred import

        SetLogLevel(-1)
        model = Model(self.config.vosk_model_path or None,
                      lang=None if self.config.vosk_model_path else "en-us")
        grammar = json.dumps([self.config.wake_word, "[unk]"])
        rec = KaldiRecognizer(model, self.config.sample_rate, grammar)
        rec.SetWords(True)
        return rec

    def _mic_blocks(self) -> Iterator[bytes]:
        import sounddevice as sd  # deferred import

        blocksize = int(self.config.sample_rate * 0.25)
        with sd.RawInputStream(samplerate=self.config.sample_rate, blocksize=blocksize,
                               dtype="int16", channels=1) as stream:
            while True:
                data, _overflowed = stream.read(blocksize)
                yield bytes(data)

    def _wake_confidence(self, result: dict) -> float:
        """Minimum word-level confidence over occurrences of the wake word."""
        words = result.get("result") or []
        confs = [w.get("conf", 0.0) for w in words
                 if w.get("word", "").lower() == self.config.wake_word.lower()]
        return min(confs) if confs else 0.0

    def listen(self) -> Iterator[str]:
        """Yields command transcripts, one per accepted wake + utterance."""
        rec = self._make_recognizer()
        window: list[float] = []  # rolling audio for speaker verification
        window_max = self.config.sample_rate * 2  # keep last ~2 s
        self.on_state("idle")
        for block in self._mic_blocks():
            samples = dsp.pcm16_to_float(block)
            window.extend(samples)
            if len(window) > window_max:
                del window[: len(window) - window_max]
            level = dsp.rms(samples)
            if level < self.config.rms_gate:
                continue  # never feed silence/noise-floor audio to the decoder
            if not rec.AcceptWaveform(block):
                continue  # partial — final-only policy
            result = json.loads(rec.Result() or "{}")
            event = WakeEvent(
                is_final=True,
                text=result.get("text", ""),
                confidence=self._wake_confidence(result),
                rms=level,
                timestamp=time.monotonic(),
            )
            decision = self.decision.observe(event)
            if not decision.triggered:
                continue
            if (self.verifier is not None and self.config.speaker_verify_enabled
                    and self.verifier.enrolled and not self.verifier.verify(window)):
                self.on_state("rejected-speaker")
                continue
            self.on_state("awake")
            command = self._capture_command()
            self.on_state("idle")
            if command:
                yield command

    def _capture_command(self, timeout_s: float = 8.0) -> str:
        """After wake, transcribe one free-form utterance (no grammar)."""
        from vosk import KaldiRecognizer, Model

        model = Model(self.config.vosk_model_path or None,
                      lang=None if self.config.vosk_model_path else "en-us")
        rec = KaldiRecognizer(model, self.config.sample_rate)
        deadline = time.monotonic() + timeout_s
        for block in self._mic_blocks():
            if time.monotonic() > deadline:
                break
            if rec.AcceptWaveform(block):
                text = json.loads(rec.Result() or "{}").get("text", "")
                if text:
                    return text
        return json.loads(rec.FinalResult() or "{}").get("text", "")


def build_engine(config: WakeConfig, data_dir: str, text_mode: bool):
    if text_mode:
        return TextWakeEngine(config)
    verifier = SpeakerVerifier(f"{data_dir}/speaker_profile.json",
                               threshold=config.speaker_threshold,
                               sample_rate=config.sample_rate)
    return VoskWakeEngine(config, verifier=verifier)
