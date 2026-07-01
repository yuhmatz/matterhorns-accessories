"""Speaker verification — respond only to the owner's voice.

This is both the durable fix for background-noise false triggers and a
security layer.  Implementation: an enrollment profile is the element-wise
mean and standard deviation of MFCC frames over a few owner utterances; a
candidate utterance is accepted when the cosine similarity between its
embedding and the profile embedding clears the threshold.

Deliberately simple (no neural nets): it must run on Python 3.14 with zero
binary dependencies.  It will not defeat a determined impersonator, but it
reliably separates the owner's voice from a TV/music bed, which is the
failure mode that blocks real commands today.  Swap in a stronger model once
the RTX 3090 arrives — the interface (enroll/verify) stays the same.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from ..audio import dsp


def _embed(samples: Sequence[float], sample_rate: int) -> list[float]:
    """Utterance embedding: per-coefficient mean + std over MFCC frames."""
    frames = dsp.mfcc(samples, sample_rate=sample_rate)
    if not frames:
        return []
    n_coeffs = len(frames[0])
    n = len(frames)
    means = [sum(f[c] for f in frames) / n for c in range(n_coeffs)]
    stds = []
    for c in range(n_coeffs):
        var = sum((f[c] - means[c]) ** 2 for f in frames) / n
        stds.append(var ** 0.5)
    return means + stds


class SpeakerVerifier:
    def __init__(self, profile_path: str | Path, threshold: float = 0.80,
                 sample_rate: int = 16000) -> None:
        self.profile_path = Path(profile_path)
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._profile: list[float] | None = None
        if self.profile_path.is_file():
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
            self._profile = data.get("embedding")

    @property
    def enrolled(self) -> bool:
        return bool(self._profile)

    def enroll(self, utterances: Sequence[Sequence[float]]) -> None:
        """Enroll from several owner utterances (float samples in [-1, 1])."""
        embeddings = [e for u in utterances if (e := _embed(u, self.sample_rate))]
        if not embeddings:
            raise ValueError("no usable enrollment audio (utterances too short?)")
        dim = len(embeddings[0])
        profile = [sum(e[i] for e in embeddings) / len(embeddings) for i in range(dim)]
        self._profile = profile
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile_path.write_text(
            json.dumps({"embedding": profile, "sample_rate": self.sample_rate}),
            encoding="utf-8",
        )

    def score(self, samples: Sequence[float]) -> float:
        if not self._profile:
            return 0.0
        emb = _embed(samples, self.sample_rate)
        if not emb or len(emb) != len(self._profile):
            return 0.0
        return dsp.cosine_similarity(emb, self._profile)

    def verify(self, samples: Sequence[float]) -> bool:
        """True if the utterance matches the enrolled owner.

        An engine with verification *enabled but not enrolled* should fail
        open (accept) so the assistant still works before first enrollment —
        that policy lives in the engine, not here.
        """
        return self.score(samples) >= self.threshold
