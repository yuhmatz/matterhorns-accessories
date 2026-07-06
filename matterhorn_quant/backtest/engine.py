"""Event-driven multi-asset backtest engine.

Causality contract:
- Signals at bar i use data through the close of bar i only.
- Orders generated from those signals execute at the OPEN of bar i+1
  through the same PaperBroker fill model used for paper trading
  (slippage, commissions, participation-capped partial fills).
- ML models are walk-forward refit on strictly past data.
- Adaptive components (strategy weights, ML out-of-sample accuracy) are
  updated only when outcomes have actually realized (5 bars later).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import Settings
from ..core.types import Order, OrderSide, Position, Signal, TradeDecision
from ..decision.engine import DecisionEngine
from ..execution.broker import PaperBroker, bar_from_row
from ..execution.router import MAX_NOTIONAL_PCT, SmartOrderRouter
from ..ml.features import LABEL_HORIZON, build_features
from ..ml.models import MLStrategy, WalkForwardEnsemble
from ..risk.manager import RiskManager, RiskStateSnapshot
from ..strategies.base import Strategy
from ..strategies.regime import RegimeDetector
from .metrics import performance_summary

log = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    equity: pd.Series
    summary: dict[str, float]
    trade_pnls: list[float]
    regime_history: pd.Series
    strategy_weights: dict[str, float]
    risk_events: list[str]
    sample_decisions: list[TradeDecision]
    n_fills: int
    warmup: int = 0

    @property
    def returns(self) -> pd.Series:
        # exclude the flat warmup segment: its zero returns would dilute
        # vol/VaR/Monte-Carlo statistics computed downstream
        return self.equity.iloc[self.warmup:].pct_change().dropna()


@dataclass
class _PendingOutcome:
    due_i: int
    symbol: str
    ref_close: float
    signals: list[Signal] = field(default_factory=list)


class BacktestEngine:
    KILL_SWITCH_COOLDOWN = 21  # bars flat before simulated manual reset

    def __init__(self, settings: Settings, strategies: list[Strategy],
                 pair_strategies: dict[str, list[Strategy]] | None = None,
                 use_ml: bool = True):
        self.settings = settings
        self.strategies = strategies
        self.pair_strategies = pair_strategies or {}
        self.ensemble = WalkForwardEnsemble() if use_ml else None
        if self.ensemble is not None:
            self.strategies = [*strategies, MLStrategy(self.ensemble)]
        names = [s.name for s in self.strategies] + [
            p.name for ps in self.pair_strategies.values() for p in ps]
        self.decision_engine = DecisionEngine(settings.decision, names)
        self.risk = RiskManager(settings.risk)
        self.regime_detector = RegimeDetector()

    # ------------------------------------------------------------------
    def run(self, data: dict[str, pd.DataFrame]) -> BacktestResult:
        symbols = sorted(data)
        index = data[symbols[0]].index
        n = len(index)
        warmup = self.settings.backtest.warmup_bars

        # --- precompute (all vectorized ops are causal) -------------------
        prepared: dict[str, pd.DataFrame] = {}
        features: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            df = data[sym]
            for strat in self.strategies:
                df = strat.prepare(df)
            for pstrat in self.pair_strategies.get(sym, []):
                df = pstrat.prepare(df)
            prepared[sym] = df
            features[sym] = build_features(data[sym])

        closes = pd.DataFrame({s: data[s]["close"] for s in symbols})
        asset_vol = closes.pct_change().rolling(21).std() * np.sqrt(252)
        index_close = (closes / closes.iloc[0]).mean(axis=1)

        # --- state ---------------------------------------------------------
        broker = PaperBroker(self.settings.execution, self.settings.backtest.initial_equity)
        router = SmartOrderRouter(broker, self.settings.execution)
        positions: dict[str, Position] = {}
        stops: dict[str, tuple[float, float, int]] = {}  # symbol -> (stop, take_profit, direction)
        equity_curve = pd.Series(np.nan, index=index)
        equity_curve.iloc[:warmup] = self.settings.backtest.initial_equity
        peak_equity = self.settings.backtest.initial_equity
        pending: list[_PendingOutcome] = []
        trade_pnls: list[float] = []
        risk_events: list[str] = []
        regime_history = pd.Series("", index=index, dtype=object)
        sample_decisions: list[TradeDecision] = []
        kill_flat_days = 0

        for i in range(warmup, n - 1):
            prices_i = closes.iloc[i].to_dict()
            equity = broker.equity(prices_i)
            prev_equity = float(equity_curve.iloc[i - 1])
            peak_equity = max(peak_equity, equity)
            self.risk.start_of_day(prev_equity)

            # 1) resolve realized outcomes -> adaptive learning
            still_pending = []
            for po in pending:
                if po.due_i == i:
                    realized = closes[po.symbol].iloc[i] / po.ref_close - 1
                    for sig in po.signals:
                        self.decision_engine.record_outcome(sig, realized)
                        if self.ensemble is not None and sig.strategy == "ml":
                            self.ensemble.record_outcome(sig.strength > 0, realized > 0)
                else:
                    still_pending.append(po)
            pending = still_pending

            # 2) ML walk-forward refit (past data only)
            if self.ensemble is not None:
                self.ensemble.maybe_refit(features, i)

            # 3) regime classification
            regime = self.regime_detector.classify(index_close, i)
            regime_history.iloc[i] = regime.label

            # 4) per-symbol signals
            signals_by_symbol: dict[str, list[Signal]] = {}
            for sym in symbols:
                sigs = []
                for strat in self.strategies:
                    s = strat.signal(sym, prepared[sym], i)
                    if s is not None and np.isfinite(s.strength):
                        sigs.append(s)
                for pstrat in self.pair_strategies.get(sym, []):
                    s = pstrat.signal(sym, prepared[sym], i)
                    if s is not None and np.isfinite(s.strength):
                        sigs.append(s)
                if sigs:
                    signals_by_symbol[sym] = sigs

            # 5) decision engine: weighted voting + filtering + ranking
            decisions = self.decision_engine.decide(
                signals_by_symbol, RegimeDetector.strategy_tilts(regime))

            # 6) risk sizing + limits + circuit breakers
            # start at the last warmup bar so the flat warmup segment's
            # synthetic zero returns don't dilute the VaR sample
            port_returns = equity_curve.iloc[max(warmup - 1, 0): i].pct_change().dropna()
            decisions, risk_state = self.risk.size_positions(
                decisions, equity, peak_equity,
                asset_vol.iloc[i].to_dict(), port_returns,
                RegimeDetector.exposure_scalar(regime))
            risk_events.extend(f"{index[i].date()}: {note}" for note in risk_state.notes)

            # 7) build target weights (stops + circuit breaker overrides)
            targets = {d.symbol: d.target_weight for d in decisions}
            current_weights = {
                s: positions[s].qty * prices_i[s] / equity for s in positions}
            bar_i = data  # alias for stop checks below
            for sym, pos in list(positions.items()):
                if sym in stops and pos.qty != 0:
                    stop, tp, sdir = stops[sym]
                    if sdir != (1 if pos.qty > 0 else -1):
                        continue  # stale after a flip; refreshed on the flip fill
                    row = bar_i[sym].iloc[i]
                    hit = ((pos.qty > 0 and (row["low"] <= stop or row["high"] >= tp))
                           or (pos.qty < 0 and (row["high"] >= stop or row["low"] <= tp)))
                    if hit:
                        targets[sym] = 0.0
            if risk_state.halted:  # reductions only
                for sym in list(targets):
                    cur = current_weights.get(sym, 0.0)
                    tgt = targets[sym]
                    if abs(tgt) > abs(cur) or np.sign(tgt) != np.sign(cur) and cur != 0:
                        targets[sym] = cur if np.sign(tgt) == np.sign(cur) else 0.0
            for sym in positions:
                targets.setdefault(sym, 0.0)  # held but no decision -> exit

            if decisions and len(sample_decisions) < 50 and i % 50 == 0:
                sample_decisions.append(decisions[0])

            # 8) execute at next bar's open
            next_ts = index[i + 1]
            for sym, target_w in targets.items():
                price = prices_i[sym]
                target_shares = int(target_w * equity / price)
                cur_shares = positions.get(sym, Position(sym)).qty
                delta = target_shares - cur_shares
                closing = target_shares == 0 and cur_shares != 0
                # turnover filter — but risk-mandated exits (stops, kill
                # switch, no-decision flattening) must always go through
                if not closing and abs(delta) * price < max(0.01 * equity, 1000):
                    continue
                # keep each order safely under the pre-trade notional cap;
                # large position flips complete across successive bars
                max_shares = int(0.9 * MAX_NOTIONAL_PCT * equity / price)
                if abs(delta) > max_shares:
                    delta = int(np.sign(delta)) * max_shares
                if delta == 0:
                    continue
                side = OrderSide.BUY if delta > 0 else OrderSide.SELL
                order = Order(symbol=sym, side=side, qty=abs(delta))
                bar = bar_from_row(sym, next_ts, data[sym].iloc[i + 1])
                report = router.execute(order, bar, equity)
                for fill in report.fills:
                    pos = positions.setdefault(sym, Position(sym))
                    realized = pos.apply_fill(fill)
                    if realized != 0.0:
                        trade_pnls.append(realized - fill.commission)
                    if pos.qty == 0:
                        positions.pop(sym, None)
                        stops.pop(sym, None)
                if sym in positions and report.fills:
                    direction = 1 if positions[sym].qty > 0 else -1
                    # set stops on entry, and refresh when a flip through
                    # zero leaves stale opposite-direction levels behind
                    if sym not in stops or stops[sym][2] != direction:
                        atr_val = float(
                            (data[sym]["high"] - data[sym]["low"]).iloc[i - 13:i + 1].mean())
                        lv = self.risk.stop_levels(report.avg_price, direction, atr_val)
                        stops[sym] = (lv.stop, lv.take_profit, direction)

            # 9) queue outcome tracking for adaptive learning
            for sym, sigs in signals_by_symbol.items():
                pending.append(_PendingOutcome(
                    due_i=i + LABEL_HORIZON, symbol=sym,
                    ref_close=float(closes[sym].iloc[i]), signals=sigs))

            # 10) mark book at next close; simulated kill-switch review cycle
            equity_curve.iloc[i + 1] = broker.equity(closes.iloc[i + 1].to_dict())
            if i >= warmup:
                equity_curve.iloc[i] = equity
            if self.risk.kill_switch_fired:
                kill_flat_days += 1
                if kill_flat_days >= self.KILL_SWITCH_COOLDOWN:
                    self.risk.manual_reset()
                    peak_equity = broker.equity(closes.iloc[i + 1].to_dict())
                    risk_events.append(f"{index[i].date()}: kill switch reset after "
                                       f"review period; risk baseline restarted")
                    kill_flat_days = 0

        equity_curve = equity_curve.ffill()
        return BacktestResult(
            equity=equity_curve,
            summary=performance_summary(equity_curve.iloc[warmup:], trade_pnls),
            trade_pnls=trade_pnls,
            regime_history=regime_history,
            strategy_weights=dict(self.decision_engine.weights),
            risk_events=risk_events,
            sample_decisions=sample_decisions,
            n_fills=len(broker.fills),
            warmup=warmup,
        )


def walk_forward_analysis(make_engine, data: dict[str, pd.DataFrame],
                          n_folds: int = 3, min_bars: int = 750) -> list[dict[str, float]]:
    """Run independent backtests on successive time slices (each fold gets a
    fresh engine, so no state leaks across folds) and report per-fold
    out-of-sample summaries. Dispersion across folds is the robustness check."""
    index = next(iter(data.values())).index
    n = len(index)
    fold_len = max(min_bars, n // n_folds)
    results = []
    for k in range(n_folds):
        lo = k * (n - fold_len) // max(n_folds - 1, 1)
        sliced = {s: df.iloc[lo: lo + fold_len] for s, df in data.items()}
        res = make_engine().run(sliced)
        results.append({"fold": k, "start": str(index[lo].date()), **res.summary})
    return results
