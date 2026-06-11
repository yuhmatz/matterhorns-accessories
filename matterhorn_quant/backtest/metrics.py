"""Performance metrics: Sharpe, Sortino, max drawdown, CAGR, win rate,
profit factor, risk/reward, exposure, turnover.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sharpe_ratio(returns: pd.Series, rf_annual: float = 0.0) -> float:
    r = returns.dropna() - rf_annual / TRADING_DAYS
    if r.std() == 0 or len(r) < 20:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def sortino_ratio(returns: pd.Series, rf_annual: float = 0.0) -> float:
    r = returns.dropna() - rf_annual / TRADING_DAYS
    downside = r[r < 0]
    if len(downside) < 5 or downside.std() == 0:
        return 0.0
    return float(r.mean() / downside.std() * np.sqrt(TRADING_DAYS))


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1).min())


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = len(equity) / TRADING_DAYS
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def trade_stats(trade_pnls: list[float]) -> dict[str, float]:
    if not trade_pnls:
        return {"win_rate": 0.0, "profit_factor": 0.0, "risk_reward": 0.0, "n_trades": 0}
    pnls = np.array(trade_pnls)
    wins, losses = pnls[pnls > 0], pnls[pnls < 0]
    gross_profit, gross_loss = wins.sum(), -losses.sum()
    return {
        "win_rate": float(len(wins) / len(pnls)),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "risk_reward": float(wins.mean() / -losses.mean()) if len(wins) and len(losses) else 0.0,
        "n_trades": len(pnls),
    }


def performance_summary(equity: pd.Series, trade_pnls: list[float] | None = None,
                        rf_annual: float = 0.0) -> dict[str, float]:
    returns = equity.pct_change().dropna()
    out = {
        "cagr": cagr(equity),
        "annual_vol": float(returns.std() * np.sqrt(TRADING_DAYS)),
        "sharpe": sharpe_ratio(returns, rf_annual),
        "sortino": sortino_ratio(returns, rf_annual),
        "max_drawdown": max_drawdown(equity),
        "calmar": cagr(equity) / abs(max_drawdown(equity)) if max_drawdown(equity) else 0.0,
        "best_day": float(returns.max()) if len(returns) else 0.0,
        "worst_day": float(returns.min()) if len(returns) else 0.0,
    }
    out.update(trade_stats(trade_pnls or []))
    return out


def format_summary(summary: dict[str, float]) -> str:
    lines = [
        f"CAGR              {summary['cagr']:+8.2%}",
        f"Annual vol        {summary['annual_vol']:8.2%}",
        f"Sharpe            {summary['sharpe']:8.2f}",
        f"Sortino           {summary['sortino']:8.2f}",
        f"Max drawdown      {summary['max_drawdown']:8.2%}",
        f"Calmar            {summary['calmar']:8.2f}",
        f"Win rate          {summary['win_rate']:8.2%}",
        f"Profit factor     {summary['profit_factor']:8.2f}",
        f"Risk/reward       {summary['risk_reward']:8.2f}",
        f"Trades            {summary['n_trades']:8d}",
    ]
    return "\n".join(lines)
