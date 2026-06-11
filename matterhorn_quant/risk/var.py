"""Value-at-Risk and expected shortfall estimators.

All functions take a *portfolio* daily-return series (or weights + asset
returns) and return positive loss fractions (0.025 = 2.5% of equity).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def historical_var(returns: pd.Series, confidence: float = 0.99) -> float:
    r = returns.dropna()
    if len(r) < 100:
        return float("nan")
    return float(-np.percentile(r, (1 - confidence) * 100))


def parametric_var(returns: pd.Series, confidence: float = 0.99) -> float:
    """Cornish–Fisher VaR: adjusts the Gaussian quantile for skew/kurtosis."""
    r = returns.dropna()
    if len(r) < 100:
        return float("nan")
    z = stats.norm.ppf(1 - confidence)
    s, k = stats.skew(r), stats.kurtosis(r)
    z_cf = (z + (z**2 - 1) * s / 6
            + (z**3 - 3 * z) * k / 24
            - (2 * z**3 - 5 * z) * s**2 / 36)
    return float(-(r.mean() + z_cf * r.std()))


def monte_carlo_var(weights: np.ndarray, asset_returns: pd.DataFrame,
                    confidence: float = 0.99, n_sims: int = 20_000,
                    seed: int = 0) -> float:
    """Simulate portfolio returns from the historical covariance (Student-t
    innovations for fat tails)."""
    r = asset_returns.dropna()
    if len(r) < 100:
        return float("nan")
    mu, cov = r.mean().values, r.cov().values
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(cov + 1e-12 * np.eye(len(cov)))
    t = rng.standard_t(df=5, size=(n_sims, len(mu))) / np.sqrt(5 / 3)
    sims = mu + t @ L.T
    port = sims @ weights
    return float(-np.percentile(port, (1 - confidence) * 100))


def expected_shortfall(returns: pd.Series, confidence: float = 0.975) -> float:
    r = returns.dropna()
    if len(r) < 100:
        return float("nan")
    cutoff = np.percentile(r, (1 - confidence) * 100)
    tail = r[r <= cutoff]
    return float(-tail.mean()) if len(tail) else float("nan")
