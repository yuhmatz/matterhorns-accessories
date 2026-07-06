# Realistic Performance Expectations

This is the most important document in the repository. Everything below is
net of transaction costs and slippage, and assumes the risk controls in
this codebase (12% vol target, 20% hard-stop drawdown) are actually obeyed.

## TL;DR — the realistic number

**A competently built and operated system of this type can realistically
average 6–10% annual return net of all costs (base case), at roughly
10–12% volatility, with a Sharpe ratio of 0.6–1.0.** A conservative
planning number is **4–6%**; a good outcome — top-quartile execution,
honest research process, several genuinely uncorrelated signal families —
is **10–15% with Sharpe 1.0–1.3**. Claims materially above that range
(without privileged data, capacity constraints, or a decade of
infrastructure) should be treated as backtest overfitting until proven by
live trading.

For context: that base case is comparable to — not better than — simply
holding an index fund in a bull decade. The honest selling point of a
system like this is **the path** (controlled drawdowns, low correlation to
the market, positive expectancy across regimes), not a higher headline
return.

## Why these numbers (assumptions and evidence)

1. **Institutional benchmarks.** Equity market-neutral hedge funds (HFRI
   EMN index) have delivered roughly 3–5% annualized net over the last two
   decades; managed-futures/trend (SG Trend) roughly 4–7% with high
   variance across decades; large multi-strategy quant funds (AQR, Two
   Sigma flagships) net single-digit to low-double-digit returns *with
   hundreds of researchers and superior data/execution*. Renaissance
   Medallion (~39% net) is the famous outlier: capacity-capped at a few
   $B, closed to outsiders, and built on infrastructure and data nobody
   replicates from public sources.
2. **The strategies here are public knowledge.** Momentum, mean reversion,
   cointegration, ML on price-derived features — all heavily arbitraged.
   Published anomaly returns decay 30–60% post-publication (McLean &
   Pontiff 2016). A new implementation captures a fraction of historical
   paper returns.
3. **Costs.** At the demo's turnover (~5–10x annually), 5–10 bps per side
   in commissions+slippage costs roughly 1–2% of NAV per year — which must
   be subtracted from a gross edge that is itself only a few percent.
4. **Risk controls cap the upside by design.** Vol targeting at 12% and a
   10% de-risking ladder deliberately trade away tail upside for path
   quality. You cannot cap drawdowns and keep lottery-ticket returns.
5. **Our own cost-aware backtest** (synthetic multi-regime data, full
   pipeline, all costs): 5.6% CAGR, Sharpe 1.2, max DD −5.6% at 4.6%
   realized vol. Synthetic data flatters nobody and proves only that the
   plumbing is sound — but the *shape* (mid-single-digit net return at
   modest vol) is exactly what this class of system produces.

## Estimated ranges (net of costs, at ~10–12% target vol)

| Metric | Conservative | Base case | Optimistic |
|---|---|---|---|
| Annual return | 2–5% | **6–10%** | 10–15% |
| Monthly return (typical range) | −3% … +3% | −3% … +4% | −4% … +5% |
| Average monthly | 0.2–0.4% | 0.5–0.8% | 0.8–1.2% |
| Max drawdown (expected over 5y) | 12–20% | 10–15% | 8–12% |
| Sharpe ratio | 0.3–0.6 | **0.6–1.0** | 1.0–1.3 |
| Win rate (per trade) | 48–52% | 50–55% | 52–57% |
| Profit factor | 1.05–1.15 | 1.15–1.35 | 1.3–1.6 |

Notes:
* Win rate near 52% with risk/reward ≥ 1.1 is what a real edge looks like.
  Backtests showing 70% win rates on daily equity strategies are broken.
* The 20% hard kill switch bounds catastrophic loss but a 20% peak-to-trough
  episode must be treated as *expected* at least once per decade.
* First-year live performance is typically the weakest (implementation
  friction, residual overfitting): plan for 0–5%.

## Expected behavior by market regime

**Bull markets (e.g. 2013, 2017, 2021):** the system will likely
**underperform buy-and-hold** — exposure caps, shorts, and vol targeting
forfeit upside. Expect to capture 50–70% of index returns: roughly
+8–15% in a +20% index year. This is the price of the bear-market profile
and the most common reason operators abandon discipline. Don't.

**Bear markets (2008, 2022):** this is where the system earns its keep.
Target outcome: **−5% to +5%** while the index drops 20–35% — driven by
regime de-risking (bear scalar 0.6x), the drawdown ladder, momentum
turning short, and the circuit breakers. A realistic failure mode is
−8–12% if the regime shift is fast (2020-style crash: detection lags by
days–weeks).

**Sideways/choppy markets (2015, 2023 H2):** modest positive expectancy —
**0% to +6%** — carried by mean reversion and stat-arb while momentum
churns and bleeds costs. The adaptive strategy weights (demonstrated in
the demo backtest: mean-reversion weight fading when it underperforms)
matter most here.

## Scenario stress (from `backtest/stress.py`, representative book)

A typical posture (0.4 net / 0.8 gross, beta ≈ 1) loses an estimated
10–15% in an instantaneous 1987/2008/2020-style shock before controls
react — consistent with the hard drawdown stop. The vol-drag term shows
why gross exposure, not just net, must be capped: vol explosions hurt
"hedged" books too.

## What would make the numbers better — and what won't

Improves the distribution: genuinely uncorrelated signal families
(cross-asset, event-driven, alternative data with provenance), better
execution (capturing 2–3 bps/trade compounds), longer honest OOS history,
disciplined capacity management. **Does not**: more model complexity on
the same price features, parameter tuning on the backtest, removing risk
controls because they "cost performance" (they do — that's their job).

## Hard disclaimer

These are engineering estimates for planning, not predictions or financial
advice. The realized return of any specific implementation can be negative
in any year, including every year. Past relationships used to derive these
estimates routinely break. Trade only risk capital, start at the smallest
viable size, and let live evidence — not backtests — set the capital
allocation.
