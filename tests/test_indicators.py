import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from matterhorn_quant.data.providers import SyntheticProvider
from matterhorn_quant.indicators.structure import breakout, market_structure, trend_strength
from matterhorn_quant.indicators.technical import (
    atr, bollinger_bands, ema, ichimoku, macd, rsi, sma, vwap,
)


def _df(n=600):
    return SyntheticProvider(seed=1).history("TEST", "2020-01-01", "2022-06-01").iloc[:n]


def test_rsi_bounds():
    r = rsi(_df()["close"])
    assert ((r >= 0) & (r <= 100)).all()


def test_sma_ema_track_price():
    close = _df()["close"]
    assert abs(sma(close, 20).iloc[-1] / close.iloc[-20:].mean() - 1) < 1e-9
    assert np.isfinite(ema(close, 20).iloc[-1])


def test_bollinger_contains_mid():
    bb = bollinger_bands(_df()["close"]).dropna()
    assert (bb["upper"] >= bb["mid"]).all() and (bb["mid"] >= bb["lower"]).all()


def test_atr_positive():
    assert (atr(_df()).dropna() > 0).all()


def test_macd_hist_is_diff():
    m = macd(_df()["close"])
    assert np.allclose(m["hist"], m["macd"] - m["signal"])


def test_vwap_within_price_range():
    df = _df()
    v = vwap(df).dropna()
    assert (v > df["low"].min() * 0.9).all() and (v < df["high"].max() * 1.1).all()


def test_ichimoku_columns():
    ich = ichimoku(_df())
    assert {"tenkan", "kijun", "span_a", "span_b"} <= set(ich.columns)


def test_structure_signals_discrete():
    df = _df()
    assert set(breakout(df).dropna().unique()) <= {-1, 0, 1}
    assert set(market_structure(df).dropna().unique()) <= {-1, 0, 1}
    assert trend_strength(df).dropna().between(-1, 1).all()


def test_no_lookahead_in_indicators():
    """Indicator values must not change when future bars are appended."""
    df = _df(500)
    cut = 400
    full = rsi(df["close"]).iloc[:cut]
    truncated = rsi(df["close"].iloc[:cut])
    assert np.allclose(full, truncated, equal_nan=True)
