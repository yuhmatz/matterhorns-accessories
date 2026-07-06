"""Classic technical indicators, vectorized over pandas Series/DataFrames.

All functions take a DataFrame with columns open/high/low/close/volume (or a
close Series where noted) and return Series/DataFrames aligned to the input
index. No lookahead: every value at time t uses data up to and including t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    # zero-loss history is maximally overbought (RSI 100), not neutral
    out = out.mask((loss == 0) & (gain > 0), 100.0)
    return out.fillna(50.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": macd_line - signal_line}
    )


def bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = sma(close, window)
    std = close.rolling(window).std()
    upper, lower = mid + num_std * std, mid - num_std * std
    pct_b = (close - lower) / (upper - lower)
    bandwidth = (upper - lower) / mid
    return pd.DataFrame(
        {"mid": mid, "upper": upper, "lower": lower, "pct_b": pct_b, "bandwidth": bandwidth}
    )


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    prev_close = df["close"].shift()
    tr = pd.concat(
        [df["high"] - df["low"],
         (df["high"] - prev_close).abs(),
         (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False).mean()


def vwap(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Rolling VWAP (anchored VWAP needs intraday data; rolling proxy on daily bars)."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    pv = (typical * df["volume"]).rolling(window).sum()
    return pv / df["volume"].rolling(window).sum()


def ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    high, low = df["high"], df["low"]

    def midpoint(w: int) -> pd.Series:
        return (high.rolling(w).max() + low.rolling(w).min()) / 2

    tenkan, kijun = midpoint(9), midpoint(26)
    # spans are plotted 26 forward; shifting keeps "cloud at time t" causal
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = midpoint(52).shift(26)
    return pd.DataFrame(
        {"tenkan": tenkan, "kijun": kijun, "span_a": span_a, "span_b": span_b}
    )


def fibonacci_levels(df: pd.DataFrame, window: int = 120) -> pd.DataFrame:
    """Retracement levels of the rolling high/low swing."""
    hi = df["high"].rolling(window).max()
    lo = df["low"].rolling(window).min()
    rng = hi - lo
    out = {"swing_high": hi, "swing_low": lo}
    for ratio in (0.236, 0.382, 0.5, 0.618, 0.786):
        out[f"fib_{ratio}"] = hi - ratio * rng
    return pd.DataFrame(out)
