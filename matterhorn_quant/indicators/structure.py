"""Market-structure analytics: support/resistance, volume profile, trend,
breakouts/reversals, and liquidity.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .technical import atr, ema


def support_resistance(df: pd.DataFrame, window: int = 10, lookback: int = 250,
                       tolerance: float = 0.01) -> pd.DataFrame:
    """Detect swing-pivot levels and the nearest support/resistance per bar.

    A pivot high (low) is a local max (min) over +/- `window` bars; levels
    within `tolerance` of each other are clustered. Pivot confirmation lags
    by `window` bars so values remain causal.
    """
    high, low, close = df["high"], df["low"], df["close"]
    piv_hi = (high == high.rolling(2 * window + 1, center=True).max()).shift(window).fillna(False)
    piv_lo = (low == low.rolling(2 * window + 1, center=True).min()).shift(window).fillna(False)

    support = np.full(len(df), np.nan)
    resistance = np.full(len(df), np.nan)
    levels: list[float] = []
    highs, lows = high.values, low.values
    for i, (is_hi, is_lo) in enumerate(zip(piv_hi.values, piv_lo.values)):
        # a flag at i confirms a pivot that occurred `window` bars earlier —
        # record the pivot bar's price, not the confirmation bar's
        if is_hi:
            levels.append(highs[i - window])
        if is_lo:
            levels.append(lows[i - window])
        levels = levels[-60:]  # keep recent structure only
        c = close.iloc[i]
        below = [lv for lv in levels if lv < c * (1 - tolerance / 4)]
        above = [lv for lv in levels if lv > c * (1 + tolerance / 4)]
        if below:
            support[i] = max(below)
        if above:
            resistance[i] = min(above)

    return pd.DataFrame({"support": support, "resistance": resistance}, index=df.index)


def volume_profile(df: pd.DataFrame, lookback: int = 120, bins: int = 24) -> pd.Series:
    """Point of control: price level with the highest traded volume in lookback."""
    poc = np.full(len(df), np.nan)
    closes, volumes = df["close"].values, df["volume"].values
    for i in range(lookback, len(df)):
        window_p = closes[i - lookback:i + 1]
        window_v = volumes[i - lookback:i + 1]
        hist, edges = np.histogram(window_p, bins=bins, weights=window_v)
        k = int(hist.argmax())
        poc[i] = (edges[k] + edges[k + 1]) / 2
    return pd.Series(poc, index=df.index, name="poc")


def trend_strength(df: pd.DataFrame, fast: int = 20, slow: int = 100) -> pd.Series:
    """Trend score in [-1, 1]: EMA separation normalized by ATR."""
    spread = ema(df["close"], fast) - ema(df["close"], slow)
    normalized = spread / (atr(df, 14) * 5)
    return normalized.clip(-1, 1).rename("trend")


def breakout(df: pd.DataFrame, window: int = 55) -> pd.Series:
    """+1 on an upside range breakout, -1 downside, 0 otherwise (Donchian-style)."""
    prior_high = df["high"].rolling(window).max().shift()
    prior_low = df["low"].rolling(window).min().shift()
    up = (df["close"] > prior_high).astype(int)
    down = (df["close"] < prior_low).astype(int)
    return (up - down).rename("breakout")


def market_structure(df: pd.DataFrame, window: int = 10) -> pd.Series:
    """Classify structure: +1 higher-highs/higher-lows, -1 lower-highs/lower-lows.

    Also serves as a reversal detector: a structure flip (e.g. +1 -> -1)
    marks a potential trend reversal.
    """
    hh = df["high"].rolling(window).max()
    ll = df["low"].rolling(window).min()
    higher = ((hh > hh.shift(window)) & (ll > ll.shift(window))).astype(int)
    lower = ((hh < hh.shift(window)) & (ll < ll.shift(window))).astype(int)
    return (higher - lower).rename("structure")


def liquidity_profile(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Liquidity/cost proxies from daily bars.

    - dollar_volume: rolling average traded value (capacity constraint input)
    - amihud: |return| per dollar traded (price impact; higher = less liquid)
    - range_pct: average daily range (spread/impact proxy)
    """
    dollar_vol = (df["close"] * df["volume"]).rolling(window).mean()
    ret = df["close"].pct_change().abs()
    amihud = (ret / (df["close"] * df["volume"])).rolling(window).mean() * 1e9
    range_pct = ((df["high"] - df["low"]) / df["close"]).rolling(window).mean()
    return pd.DataFrame(
        {"dollar_volume": dollar_vol, "amihud": amihud, "range_pct": range_pct}
    )
