"""Portfolio construction: constrained mean–variance and risk-parity
optimizers, plus rebalancing with turnover control.

This is the *strategic* allocation path (scheduled optimization/rebalance
jobs, multi-sleeve capital allocation). The tactical daily path in
`backtest/engine.py` sizes positions directly through the risk manager;
wiring the optimizer between decision scores and risk limits is the
intended production upgrade once sleeve-level expected returns exist.
Covariance is shrunk (Ledoit–Wolf-style toward the diagonal) because sample
covariance on short windows is the classic way to blow up an optimizer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _shrunk_cov(returns: pd.DataFrame, shrink: float = 0.3) -> np.ndarray:
    sample = returns.cov().values * 252
    target = np.diag(np.diag(sample))
    return (1 - shrink) * sample + shrink * target


def mean_variance_weights(
    expected: pd.Series,                 # annualized expected returns (from scores)
    returns: pd.DataFrame,               # historical daily returns, same symbols
    max_weight: float = 0.10,
    long_only: bool = False,
    risk_aversion: float = 8.0,
) -> pd.Series:
    """Maximize w'mu - (lambda/2) w'Sigma w  s.t. sum|w|<=1, |w_i|<=max_weight."""
    symbols = list(expected.index)
    mu = expected.values
    sigma = _shrunk_cov(returns[symbols])
    n = len(symbols)

    def objective(w):
        return -(w @ mu - 0.5 * risk_aversion * w @ sigma @ w)

    lo = 0.0 if long_only else -max_weight
    bounds = [(lo, max_weight)] * n
    constraints = [{"type": "ineq", "fun": lambda w: 1.0 - np.abs(w).sum()}]
    res = minimize(objective, x0=np.zeros(n), bounds=bounds,
                   constraints=constraints, method="SLSQP",
                   options={"maxiter": 300})
    w = res.x if res.success else np.clip(mu / (np.abs(mu).sum() + 1e-12), lo, max_weight)
    return pd.Series(w, index=symbols)


def risk_parity_weights(returns: pd.DataFrame, max_weight: float = 0.20) -> pd.Series:
    """Equal-risk-contribution weights (long-only), iterative solution."""
    sigma = _shrunk_cov(returns)
    n = sigma.shape[0]
    w = np.full(n, 1 / n)
    for _ in range(200):
        marginal = sigma @ w
        contrib = w * marginal
        target = contrib.mean()
        w *= (target / (contrib + 1e-12)) ** 0.5
        w = np.clip(w / w.sum(), 0.0, max_weight)
        w /= w.sum()
    return pd.Series(w, index=returns.columns)


def rebalance_orders(
    current_weights: pd.Series,
    target_weights: pd.Series,
    equity: float,
    prices: pd.Series,
    threshold: float = 0.01,
) -> pd.Series:
    """Share deltas to move current -> target, skipping drifts under
    `threshold` (turnover/cost control). Positive = buy shares."""
    symbols = target_weights.index.union(current_weights.index)
    cur = current_weights.reindex(symbols, fill_value=0.0)
    tgt = target_weights.reindex(symbols, fill_value=0.0)
    delta = tgt - cur
    delta[delta.abs() < threshold] = 0.0
    return (delta * equity / prices.reindex(symbols)).fillna(0.0)
