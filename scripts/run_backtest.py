#!/usr/bin/env python3
"""End-to-end demo: full platform backtest on synthetic multi-regime data.

Pipeline exercised: data (failover provider) -> technical/quant/ML/pairs
signals -> regime detection -> decision engine (adaptive weighted voting)
-> risk manager (vol targeting, VaR, circuit breakers, drawdown ladder)
-> paper execution (slippage, commissions, partial fills) -> metrics,
Monte Carlo stress, scenario analysis.

Run:  python scripts/run_backtest.py [--years 8] [--no-ml]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from matterhorn_quant.backtest.engine import BacktestEngine, walk_forward_analysis
from matterhorn_quant.backtest.metrics import format_summary
from matterhorn_quant.backtest.stress import monte_carlo_paths, scenario_analysis
from matterhorn_quant.config import DEFAULT_SETTINGS
from matterhorn_quant.data.providers import FailoverProvider, SyntheticProvider, load_universe
from matterhorn_quant.monitoring.ops import setup_logging
from matterhorn_quant.strategies.classic import (
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
)
from matterhorn_quant.strategies.statarb import PairsStrategy, find_cointegrated_pairs

UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM", "XOM", "JNJ", "WMT", "CAT", "KO"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=8)
    parser.add_argument("--no-ml", action="store_true")
    parser.add_argument("--walk-forward", action="store_true",
                        help="also run per-fold walk-forward robustness analysis")
    args = parser.parse_args()

    setup_logging()
    settings = DEFAULT_SETTINGS

    end = pd.Timestamp("2026-01-01")
    start = end - pd.DateOffset(years=args.years)
    provider = FailoverProvider([SyntheticProvider(seed=7), SyntheticProvider(seed=11)])
    print(f"Loading {len(UNIVERSE)} symbols, {start.date()} .. {end.date()} ...")
    data = load_universe(provider, UNIVERSE, str(start.date()), str(end.date()))

    # cointegration scan on the warmup window only (no lookahead)
    warmup = settings.backtest.warmup_bars
    warmup_prices = {s: df["close"].iloc[:warmup] for s, df in data.items()}
    pairs = find_cointegrated_pairs(warmup_prices)
    pair_strategies: dict[str, list] = {}
    for a, b, hedge in pairs[:3]:
        strat = PairsStrategy(a, b, hedge, data[a]["close"], data[b]["close"])
        pair_strategies.setdefault(a, []).append(strat)
        pair_strategies.setdefault(b, []).append(strat)
    print(f"Cointegrated pairs (warmup scan): {[(a, b) for a, b, _ in pairs[:3]] or 'none'}")

    engine = BacktestEngine(
        settings,
        strategies=[MomentumStrategy(), MeanReversionStrategy(), BreakoutStrategy()],
        pair_strategies=pair_strategies,
        use_ml=not args.no_ml,
    )

    t0 = time.time()
    result = engine.run(data)
    print(f"\nBacktest finished in {time.time() - t0:.1f}s — {result.n_fills} fills, "
          f"{len(result.trade_pnls)} closed trades")

    print("\n=== Performance =========================================")
    print(format_summary(result.summary))

    print("\n=== Adaptive strategy weights (end of test) =============")
    for name, w in sorted(result.strategy_weights.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<28s} {w:.2f}")

    print("\n=== Regime distribution ==================================")
    print(result.regime_history[result.regime_history != ""].value_counts().to_string())

    print(f"\n=== Risk events ({len(result.risk_events)}) — last 8 ====")
    for event in result.risk_events[-8:]:
        print(f"  {event}")

    if result.sample_decisions:
        d = result.sample_decisions[-1]
        print("\n=== Example decision (full reasoning trail) ==============")
        print(f"  {d.symbol}: score {d.score:+.2f}, confidence {d.confidence:.2f}, "
              f"target weight {d.target_weight:+.2%}")
        print(f"  {d.reasoning[:600]}")

    print("\n=== Monte Carlo (block bootstrap of realized returns) =====")
    print(monte_carlo_paths(result.returns).round(3).to_string())

    print("\n=== Crisis scenario analysis ==============================")
    net = 0.4  # representative average book posture
    gross = 0.8
    daily_vol = float(result.returns.std())
    print(scenario_analysis(net, gross, daily_vol).round(4).to_string())

    if args.walk_forward:
        print("\n=== Walk-forward analysis (independent folds) =============")

        def make_engine():
            return BacktestEngine(
                settings,
                strategies=[MomentumStrategy(), MeanReversionStrategy(), BreakoutStrategy()],
                use_ml=not args.no_ml,
            )

        folds = walk_forward_analysis(make_engine, data, n_folds=3)
        cols = ["fold", "start", "cagr", "sharpe", "max_drawdown", "win_rate", "n_trades"]
        print(pd.DataFrame(folds)[cols].round(3).to_string(index=False))
        sharpes = [f["sharpe"] for f in folds]
        print(f"\nFold Sharpe dispersion: min {min(sharpes):.2f} / max {max(sharpes):.2f} — "
              f"wide dispersion means the edge is regime-dependent, not robust")


if __name__ == "__main__":
    main()
