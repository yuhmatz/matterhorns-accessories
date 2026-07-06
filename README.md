# Matterhorn Quant

An institutional-grade AI-powered trading platform: complete system design
plus a working Python reference implementation of the full pipeline —
data → technical analysis → quant strategies → machine learning →
sentiment → decision engine → risk management → execution → monitoring —
with adaptive self-improvement loops and cost-aware backtesting.

> **This is a research and engineering platform, not financial advice.**
> See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for honest, evidence-based
> performance expectations before forming any opinion based on backtests.

## Documentation

* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — full system design:
  component architecture, multi-agent organization, technology stack,
  databases, cloud/deployment architecture, data flow, MVP→production
  roadmap, scalability, weaknesses, and failure scenarios.
* **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** — realistic performance
  estimates (annual/monthly returns, drawdown, Sharpe, win rate, behavior
  by market regime) with the assumptions behind them.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest tests/ -q          # 21 tests
python scripts/run_backtest.py      # full-pipeline 8-year demo backtest
```

The demo runs the entire platform on synthetic multi-regime market data
(regime-switching drift/vol, fat tails, jumps) for 10 symbols over 8
years: momentum + mean-reversion + breakout + cointegration-pairs + a
walk-forward-trained ML ensemble, combined by an adaptive decision engine,
sized by the risk manager, executed through a paper broker with slippage,
commissions and partial fills — then reports the full metrics suite,
Monte Carlo stress test, and crisis scenario analysis.

Representative output (synthetic data — demonstrates the plumbing, not alpha):

```
CAGR               +3.78%      Sharpe        0.78
Annual vol          4.91%      Sortino       1.27
Max drawdown       -8.10%      Win rate     48.16%
Profit factor       1.16       Trades         8412
```

(These numbers *dropped* after an adversarial code review fixed lookahead
and risk-logic bugs — a live demonstration of why most backtest edges are
bugs. The review's confirmed findings and fixes are in the git history.)

## Package layout

```
matterhorn_quant/
├── core/         shared typed domain objects (Signal, Order, Fill, ...)
├── config.py     all tunables; secrets via environment / secret manager
├── data/         provider abstraction, failover, validation, synthetic data
├── indicators/   RSI, MACD, Bollinger, VWAP, ATR, Ichimoku, Fibonacci,
│                 support/resistance, volume profile, structure, liquidity
├── strategies/   momentum, mean reversion, breakout, pairs/cointegration,
│                 GMM regime detection
├── ml/           feature engineering, walk-forward GBM/RF/logit ensemble,
│                 drift detection, OOS self-evaluation, explainability
├── sentiment/    finance-lexicon sentiment scoring with confidence
├── risk/         vol-target sizing, VaR/ES, exposure limits, dynamic stops,
│                 circuit breakers, drawdown ladder, kill switch
├── portfolio/    mean-variance & risk-parity optimizers, rebalancing
├── decision/     adaptive weighted-voting decision engine with reasoning
├── backtest/     event-driven engine, walk-forward analysis, metrics,
│                 Monte Carlo + crisis scenario stress testing
├── execution/    broker abstraction, order validation, TWAP smart routing,
│                 paper broker (slippage, partial fills, commissions)
├── monitoring/   logging, health heartbeats, alert fan-out, audit trail
└── agents/       multi-agent orchestration and self-improvement loop
```

## Design invariants

1. Backtest, paper, and live trading share one code path.
2. Signals at bar *t* execute at bar *t+1*; models train walk-forward —
   causality is enforced structurally, and tested (`tests/`).
3. Every backtest number includes commissions, slippage and partial fills.
4. The risk manager can veto or flatten anything; the kill switch requires
   human reset.
5. Every decision carries a reasoning trail into an append-only audit log.
