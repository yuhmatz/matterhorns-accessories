"""Sentiment analysis over financial text (news, earnings calls, filings,
analyst reports, social media).

The reference implementation scores text with the Loughran–McDonald-style
finance lexicon approach (general-purpose sentiment lexicons misread
finance: "liability", "gross", "depreciation" are not negative emotions).
In production this is one scorer in a pipeline; transformer models (FinBERT)
or an LLM scorer implement the same `score()` interface, and per-source
ingestion adapters normalize news feeds, transcripts, EDGAR filings and
social streams into `Document`s.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

POSITIVE = {
    "beat", "beats", "exceeded", "strong", "growth", "record", "upgraded",
    "upgrade", "raised", "outperform", "profitable", "surged", "expansion",
    "robust", "momentum", "buyback", "dividend", "innovative", "gain",
    "gains", "improved", "improving", "accelerating", "bullish", "rally",
}
NEGATIVE = {
    "miss", "missed", "weak", "decline", "declined", "downgrade",
    "downgraded", "cut", "lawsuit", "investigation", "fraud", "warning",
    "bankruptcy", "default", "layoffs", "restructuring", "impairment",
    "loss", "losses", "plunge", "plunged", "bearish", "recession",
    "shortfall", "guidance-cut", "writedown", "probe", "recall",
}
NEGATORS = {"not", "no", "never", "without", "hardly"}
INTENSIFIERS = {"very": 1.5, "significantly": 1.6, "sharply": 1.6,
                "slightly": 0.6, "modestly": 0.7}


@dataclass
class SentimentScore:
    symbol: str
    score: float        # [-1, 1]
    confidence: float   # [0, 1] — driven by signal density and volume
    n_documents: int
    summary: str


class SentimentAnalyzer:
    """Aggregates per-document lexicon scores into a symbol-level score."""

    def score_text(self, text: str) -> tuple[float, int]:
        """Return (score in [-1,1], number of sentiment-bearing tokens)."""
        tokens = re.findall(r"[a-z'-]+", text.lower())
        total, hits = 0.0, 0
        for i, tok in enumerate(tokens):
            val = 1.0 if tok in POSITIVE else -1.0 if tok in NEGATIVE else 0.0
            if val == 0.0:
                continue
            window = tokens[max(0, i - 3): i]
            if any(w in NEGATORS for w in window):
                val = -val
            for w in window:
                val *= INTENSIFIERS.get(w, 1.0)
            total += val
            hits += 1
        if hits == 0:
            return 0.0, 0
        return math.tanh(total / max(hits, 1) * 1.2), hits

    def score_documents(self, symbol: str, documents: list[str]) -> SentimentScore:
        if not documents:
            return SentimentScore(symbol, 0.0, 0.0, 0, "no documents")
        scores, weights = [], []
        for doc in documents:
            s, hits = self.score_text(doc)
            if hits:
                scores.append(s)
                weights.append(min(hits, 10))
        if not scores:
            return SentimentScore(symbol, 0.0, 0.0, len(documents), "no sentiment-bearing text")
        score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        # confidence grows with document count and agreement between documents
        spread = max(scores) - min(scores) if len(scores) > 1 else 0.0
        confidence = min(1.0, len(scores) / 8) * max(0.2, 1 - spread / 2)
        label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
        return SentimentScore(
            symbol, score, confidence, len(documents),
            f"{label} ({score:+.2f}) across {len(scores)} scored documents",
        )
