"""Feature engineering for ML signal models.

Every feature at row t uses information up to and including t; the label is
the *forward* return, used only at training time. Features are designed to
be stationary (returns, ratios, normalized distances) rather than raw prices.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators.structure import liquidity_profile, market_structure, trend_strength
from ..indicators.technical import atr, bollinger_bands, macd, rsi

FEATURE_COLUMNS = [
    "ret_1d", "ret_5d", "ret_21d", "ret_63d",
    "vol_21d", "vol_ratio",
    "rsi", "pct_b", "bandwidth", "macd_hist_norm",
    "trend", "structure", "atr_pct",
    "volume_z", "range_pct",
    "dow_sin", "dow_cos",
]

LABEL_HORIZON = 5  # predict 5-day forward direction


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    ret = close.pct_change()
    vol21 = ret.rolling(21).std()

    bb = bollinger_bands(close)
    a = atr(df)
    feats = pd.DataFrame(index=df.index)
    feats["ret_1d"] = ret
    feats["ret_5d"] = close.pct_change(5)
    feats["ret_21d"] = close.pct_change(21)
    feats["ret_63d"] = close.pct_change(63)
    feats["vol_21d"] = vol21 * np.sqrt(252)
    feats["vol_ratio"] = vol21 / ret.rolling(100).std()
    feats["rsi"] = rsi(close) / 100
    feats["pct_b"] = bb["pct_b"]
    feats["bandwidth"] = bb["bandwidth"]
    feats["macd_hist_norm"] = macd(close)["hist"] / close
    feats["trend"] = trend_strength(df)
    feats["structure"] = market_structure(df)
    feats["atr_pct"] = a / close
    vol_mean = df["volume"].rolling(63).mean()
    vol_std = df["volume"].rolling(63).std()
    feats["volume_z"] = ((df["volume"] - vol_mean) / vol_std).clip(-4, 4)
    feats["range_pct"] = liquidity_profile(df)["range_pct"]
    dow = pd.Series(df.index.dayofweek, index=df.index, dtype=float)
    feats["dow_sin"] = np.sin(2 * np.pi * dow / 5)
    feats["dow_cos"] = np.cos(2 * np.pi * dow / 5)

    # forward label — training only; NEVER readable at prediction time t
    fwd = close.shift(-LABEL_HORIZON) / close - 1
    feats["label_up"] = (fwd > 0).astype(float).where(fwd.notna())
    return feats
