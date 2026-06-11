"""Statistical arbitrage: cointegration scanning and pairs trading.

`find_cointegrated_pairs` runs an Engle–Granger test over all pairs in the
universe; `PairsStrategy` trades the z-score of the cointegrating spread.
Pairs trading is market-neutral by construction — the strategy emits
opposite-signed signals on the two legs.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from ..core.types import Signal
from .base import Strategy


def _adf_stat(series: np.ndarray) -> float:
    """Augmented Dickey–Fuller t-statistic (one lag) for unit-root testing."""
    y = np.asarray(series, dtype=float)
    dy = np.diff(y)
    y_lag, dy_lag, dy_t = y[1:-1], dy[:-1], dy[1:]
    X = np.column_stack([np.ones_like(y_lag), y_lag, dy_lag])
    beta, *_ = np.linalg.lstsq(X, dy_t, rcond=None)
    resid = dy_t - X @ beta
    dof = len(dy_t) - X.shape[1]
    sigma2 = resid @ resid / dof
    cov = sigma2 * np.linalg.inv(X.T @ X)
    return beta[1] / np.sqrt(cov[1, 1])


def engle_granger(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    """Return (hedge_ratio, adf_t_stat) for log-price cointegration of a ~ b."""
    la, lb = np.log(a.values), np.log(b.values)
    slope, intercept, *_ = stats.linregress(lb, la)
    spread = la - (slope * lb + intercept)
    return slope, _adf_stat(spread)


def find_cointegrated_pairs(prices: dict[str, pd.Series], adf_threshold: float = -3.3,
                            min_corr: float = 0.5) -> list[tuple[str, str, float]]:
    """Scan all pairs; return (sym_a, sym_b, hedge_ratio) for cointegrated ones.

    -3.3 approximates the 5% Engle–Granger critical value. Correlation
    pre-filter keeps the O(n^2) scan cheap on large universes.
    """
    symbols = sorted(prices)
    rets = pd.DataFrame({s: prices[s].pct_change() for s in symbols}).dropna()
    corr = rets.corr()
    pairs = []
    for i, a in enumerate(symbols):
        for b in symbols[i + 1:]:
            if corr.loc[a, b] < min_corr:
                continue
            hedge, t_stat = engle_granger(prices[a], prices[b])
            if t_stat < adf_threshold:
                pairs.append((a, b, hedge))
    return pairs


class PairsStrategy(Strategy):
    """Trade the z-scored cointegrating spread of one (a, b) pair.

    Emits a signal only for the leg matching `symbol`; the backtest engine
    runs one instance per leg so both sides are taken simultaneously.
    """

    def __init__(self, sym_a: str, sym_b: str, hedge_ratio: float,
                 prices_b: pd.Series, window: int = 60,
                 entry_z: float = 2.0, exit_z: float = 0.5):
        self.sym_a, self.sym_b, self.hedge = sym_a, sym_b, hedge_ratio
        self.prices_b = prices_b
        self.window, self.entry_z, self.exit_z = window, entry_z, exit_z
        self.name = f"pairs[{sym_a}/{sym_b}]"
        self._col = f"z_{sym_a}_{sym_b}"

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        b = self.prices_b.reindex(df.index).ffill()
        spread = np.log(df["close"]) - self.hedge * np.log(b)
        mean = spread.rolling(self.window).mean()
        std = spread.rolling(self.window).std()
        out[self._col] = (spread - mean) / std.replace(0, np.nan)
        return out

    def signal(self, symbol: str, df: pd.DataFrame, i: int) -> Optional[Signal]:
        z = df[self._col].iloc[i]
        if np.isnan(z) or abs(z) < self.entry_z:
            return None
        # spread too high -> short A / long B; leg sign depends on which leg we are
        leg = -1.0 if symbol == self.sym_a else self.hedge / abs(self.hedge)
        strength = float(np.clip(abs(z) / 3, 0, 1)) * np.sign(z) * leg
        confidence = float(np.clip((abs(z) - self.entry_z) / 2 + 0.5, 0.5, 0.9))
        return self._make(
            symbol, strength, confidence,
            f"cointegrated spread {self.sym_a}/{self.sym_b} z={z:+.2f} "
            f"(entry {self.entry_z}); mean-reversion leg",
        )
