"""Stress testing: Monte Carlo resampling of realized strategy returns and
deterministic historical-crisis scenario analysis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import max_drawdown

# Scenario shocks: instantaneous market move and a vol multiplier applied to
# the strategy's beta-adjusted exposure (approximate, but the right order of
# magnitude for board-level "what if" reporting).
SCENARIOS = {
    "black_monday_1987": {"market_shock": -0.22, "vol_mult": 4.0},
    "gfc_sep_oct_2008": {"market_shock": -0.30, "vol_mult": 3.0},
    "flash_crash_2010": {"market_shock": -0.09, "vol_mult": 2.5},
    "covid_feb_mar_2020": {"market_shock": -0.34, "vol_mult": 3.5},
    "rate_shock_2022": {"market_shock": -0.15, "vol_mult": 1.8},
    "melt_up": {"market_shock": +0.15, "vol_mult": 1.5},
}


def monte_carlo_paths(returns: pd.Series, n_paths: int = 2000,
                      horizon: int = 252, block: int = 10,
                      seed: int = 0) -> pd.DataFrame:
    """Block-bootstrap the realized daily return stream (blocks preserve
    short-range autocorrelation/vol clustering) and report the distribution
    of annual outcomes and drawdowns."""
    r = returns.dropna().values
    rng = np.random.default_rng(seed)
    n_blocks = horizon // block + 1
    finals, drawdowns = np.empty(n_paths), np.empty(n_paths)
    for p in range(n_paths):
        starts = rng.integers(0, len(r) - block, size=n_blocks)
        path = np.concatenate([r[s:s + block] for s in starts])[:horizon]
        equity = pd.Series(np.cumprod(1 + path))
        finals[p] = equity.iloc[-1] - 1
        drawdowns[p] = max_drawdown(equity)
    return pd.DataFrame({
        "stat": ["p05", "p25", "median", "p75", "p95"],
        "annual_return": np.percentile(finals, [5, 25, 50, 75, 95]),
        "max_drawdown": np.percentile(drawdowns, [5, 25, 50, 75, 95]),
    }).set_index("stat")


def scenario_analysis(net_exposure: float, gross_exposure: float,
                      daily_vol: float, beta: float = 1.0) -> pd.DataFrame:
    """First-order portfolio impact under each crisis scenario.

    impact ≈ beta * net_exposure * market_shock
             - gross_exposure * vol_drag(vol_mult)
    The vol-drag term penalizes gross books in vol explosions (spread
    blowouts, forced deleveraging) even when net exposure is small.
    """
    rows = []
    for name, sc in SCENARIOS.items():
        directional = beta * net_exposure * sc["market_shock"]
        vol_drag = -gross_exposure * daily_vol * np.sqrt(5) * (sc["vol_mult"] - 1)
        rows.append({"scenario": name,
                     "directional_pnl": directional,
                     "vol_drag": vol_drag,
                     "estimated_impact": directional + vol_drag})
    return pd.DataFrame(rows).set_index("scenario")
