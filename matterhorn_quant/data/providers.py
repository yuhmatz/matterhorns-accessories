"""Market data providers with redundancy and failover.

Production providers (Polygon, Alpaca, IEX, Refinitiv, Bloomberg) implement
the same `DataProvider` interface; `FailoverProvider` chains them so a
provider outage degrades gracefully instead of halting the system.

`SyntheticProvider` generates statistically realistic multi-regime price
paths so every part of the platform can be developed, tested, and
stress-tested without a live data subscription.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataProvider(ABC):
    """Uniform interface over heterogeneous market-data vendors."""

    name: str = "abstract"

    @abstractmethod
    def history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Daily OHLCV indexed by date. Must raise on failure (for failover)."""

    def healthy(self) -> bool:
        return True


class CSVProvider(DataProvider):
    """Reads OHLCV from ``<root>/<SYMBOL>.csv`` (columns: date + OHLCV)."""

    name = "csv"

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        path = self.root / f"{symbol}.csv"
        df = pd.read_csv(path, parse_dates=["date"], index_col="date")
        df = df.loc[start:end, OHLCV_COLUMNS].astype(float)
        if df.empty:
            raise ValueError(f"no data for {symbol} in {start}..{end}")
        return df


class SyntheticProvider(DataProvider):
    """Regime-switching geometric Brownian motion with fat tails.

    Three regimes (bull / bear / chop) with distinct drift, volatility and
    persistence, plus occasional jump shocks — enough realism to exercise
    regime detection, drawdown protection and circuit breakers.
    """

    name = "synthetic"

    REGIMES = {  # (annual drift, annual vol)
        "bull": (0.18, 0.13),
        "bear": (-0.25, 0.32),
        "chop": (0.02, 0.18),
    }
    TRANSITION = pd.DataFrame(  # daily regime transition matrix
        [[0.990, 0.004, 0.006],
         [0.010, 0.980, 0.010],
         [0.008, 0.004, 0.988]],
        index=["bull", "bear", "chop"], columns=["bull", "bear", "chop"],
    )

    def __init__(self, seed: int = 7):
        self.seed = seed

    def history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        dates = pd.bdate_range(start, end)
        n = len(dates)
        rng = np.random.default_rng(abs(hash((symbol, self.seed))) % 2**32)

        regimes = list(self.REGIMES)
        state = rng.choice(regimes)
        rets = np.empty(n)
        for i in range(n):
            mu, sigma = self.REGIMES[state]
            daily_mu, daily_sigma = mu / 252, sigma / np.sqrt(252)
            shock = rng.standard_t(df=4) * daily_sigma * 0.85
            if rng.random() < 0.004:  # jump
                shock += rng.normal(0, 4 * daily_sigma)
            rets[i] = daily_mu + shock
            state = rng.choice(regimes, p=self.TRANSITION.loc[state].values)

        close = 100.0 * np.exp(np.cumsum(rets))
        intraday = np.abs(rng.normal(0, 0.006, n))
        open_ = close * np.exp(rng.normal(0, 0.004, n))
        high = np.maximum(open_, close) * (1 + intraday)
        low = np.minimum(open_, close) * (1 - intraday)
        volume = rng.lognormal(13.5, 0.5, n) * (1 + 5 * np.abs(rets))

        return pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )


class FailoverProvider(DataProvider):
    """Tries each provider in order; first healthy answer wins."""

    name = "failover"

    def __init__(self, providers: list[DataProvider]):
        if not providers:
            raise ValueError("at least one provider required")
        self.providers = providers

    def history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        errors = []
        for p in self.providers:
            try:
                df = p.history(symbol, start, end)
                self._validate(df, symbol)
                return df
            except Exception as exc:  # noqa: BLE001 — failover by design
                log.warning("provider %s failed for %s: %s", p.name, symbol, exc)
                errors.append(f"{p.name}: {exc}")
        raise RuntimeError(f"all providers failed for {symbol}: {errors}")

    @staticmethod
    def _validate(df: pd.DataFrame, symbol: str) -> None:
        """Data-quality gate: reject obviously corrupt vendor data."""
        if df[OHLCV_COLUMNS].isna().any().any():
            raise ValueError(f"{symbol}: NaNs in OHLCV")
        if (df["close"] <= 0).any() or (df["high"] < df["low"]).any():
            raise ValueError(f"{symbol}: impossible prices")
        jumps = df["close"].pct_change().abs()
        if (jumps > 0.5).any():
            log.warning("%s: >50%% single-day move — verify corporate actions", symbol)


def load_universe(provider: DataProvider, symbols: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    """Fetch aligned history for a universe of symbols."""
    return {s: provider.history(s, start, end) for s in symbols}
