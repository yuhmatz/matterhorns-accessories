"""Strategy interface.

Strategies are stateless signal generators: `prepare()` precomputes indicator
columns once per symbol (vectorized, causal), then `signal()` reads row `i`
and emits a Signal with strength, confidence and human-readable reasoning.
The split keeps backtests O(n) instead of O(n^2) and guarantees the live
path and the backtest path execute identical code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from ..core.types import Signal


class Strategy(ABC):
    name: str = "abstract"

    @abstractmethod
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add this strategy's indicator columns to a copy of `df`."""

    @abstractmethod
    def signal(self, symbol: str, df: pd.DataFrame, i: int) -> Optional[Signal]:
        """Signal for bar `i` using rows [0..i] only. None = no opinion."""

    def _make(self, symbol: str, strength: float, confidence: float, reasoning: str) -> Signal:
        return Signal(
            symbol=symbol,
            strategy=self.name,
            strength=float(max(-1.0, min(1.0, strength))),
            confidence=float(max(0.0, min(1.0, confidence))),
            reasoning=reasoning,
        )
