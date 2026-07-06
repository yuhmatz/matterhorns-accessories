"""Classic quantitative strategies: time-series momentum, mean reversion,
volatility breakout. Each emits graded signals with reasoning.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from ..core.types import Signal
from ..indicators.structure import breakout, market_structure, trend_strength
from ..indicators.technical import atr, bollinger_bands, macd, rsi
from .base import Strategy


class MomentumStrategy(Strategy):
    """Time-series momentum: 12-1 month return, confirmed by trend and MACD."""

    name = "momentum"

    def __init__(self, lookback: int = 252, skip: int = 21):
        self.lookback, self.skip = lookback, skip

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        ret = df["close"].pct_change(self.lookback - self.skip).shift(self.skip)
        vol = df["close"].pct_change().rolling(63).std() * np.sqrt(252)
        out["mom_score"] = (ret / vol.replace(0, np.nan)).clip(-3, 3) / 3
        out["mom_trend"] = trend_strength(df)
        out["mom_macd_hist"] = macd(df["close"])["hist"]
        return out

    def signal(self, symbol: str, df: pd.DataFrame, i: int) -> Optional[Signal]:
        row = df.iloc[i]
        score, trend = row["mom_score"], row["mom_trend"]
        if np.isnan(score) or np.isnan(trend):
            return None
        agree = np.sign(score) == np.sign(trend)
        macd_agree = np.sign(row["mom_macd_hist"]) == np.sign(score)
        confidence = 0.3 + 0.4 * agree + 0.2 * macd_agree
        return self._make(
            symbol, score, confidence,
            f"12-1m risk-adj momentum {score:+.2f}; trend {trend:+.2f} "
            f"({'confirms' if agree else 'conflicts'}); MACD "
            f"{'confirms' if macd_agree else 'conflicts'}",
        )


class MeanReversionStrategy(Strategy):
    """Short-horizon reversion: Bollinger %B + RSI extremes, faded only when
    the longer trend is not strongly against the trade."""

    name = "mean_reversion"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        bb = bollinger_bands(df["close"])
        out["mr_pct_b"] = bb["pct_b"]
        out["mr_rsi"] = rsi(df["close"])
        out["mr_trend"] = trend_strength(df)
        return out

    def signal(self, symbol: str, df: pd.DataFrame, i: int) -> Optional[Signal]:
        row = df.iloc[i]
        pct_b, r, trend = row["mr_pct_b"], row["mr_rsi"], row["mr_trend"]
        if np.isnan(pct_b) or np.isnan(trend):
            return None
        if pct_b < 0.05 and r < 32:
            strength = min(1.0, (32 - r) / 20 + (0.05 - pct_b))
            confidence = 0.65 if trend > -0.5 else 0.3  # don't fight a strong downtrend
            return self._make(
                symbol, strength, confidence,
                f"oversold: %B={pct_b:.2f}, RSI={r:.0f}; trend filter {trend:+.2f}",
            )
        if pct_b > 0.95 and r > 68:
            strength = -min(1.0, (r - 68) / 20 + (pct_b - 0.95))
            confidence = 0.65 if trend < 0.5 else 0.3
            return self._make(
                symbol, strength, confidence,
                f"overbought: %B={pct_b:.2f}, RSI={r:.0f}; trend filter {trend:+.2f}",
            )
        return None


class BreakoutStrategy(Strategy):
    """Donchian breakout with market-structure confirmation and ATR context
    (volatility expansion). Doubles as a reversal detector via structure flips."""

    name = "breakout"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["bo_signal"] = breakout(df)
        out["bo_structure"] = market_structure(df)
        a = atr(df)
        out["bo_atr_expansion"] = a / a.rolling(100).mean()
        return out

    def signal(self, symbol: str, df: pd.DataFrame, i: int) -> Optional[Signal]:
        row = df.iloc[i]
        bo = row["bo_signal"]
        if bo == 0 or np.isnan(row["bo_atr_expansion"]):
            return None
        structure_confirms = row["bo_structure"] == bo
        expansion = row["bo_atr_expansion"]
        confidence = 0.4 + 0.3 * structure_confirms + 0.2 * (expansion > 1.1)
        return self._make(
            symbol, 0.8 * bo, confidence,
            f"{'upside' if bo > 0 else 'downside'} 55-bar breakout; structure "
            f"{'confirms' if structure_confirms else 'neutral'}; ATR expansion {expansion:.2f}x",
        )
