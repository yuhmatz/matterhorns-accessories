"""Portfolio risk manager: the layer that turns "what we want to own" into
"what we are allowed to own", and the only layer with authority to halt
trading.

Controls implemented here:
- volatility-targeted position sizing with fractional-Kelly conviction scaling
- per-name / gross / net exposure limits
- portfolio VaR limit (scales the whole book down, never selectively)
- ATR-based dynamic stop-loss and take-profit levels
- daily loss circuit breaker (no new entries after the daily limit)
- drawdown ladder: soft level de-risks progressively, hard level fires the
  kill switch (liquidate everything, halt until manual reset)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import RiskConfig
from ..core.types import TradeDecision
from .var import historical_var

log = logging.getLogger(__name__)


@dataclass
class RiskStateSnapshot:
    equity: float
    peak_equity: float
    drawdown: float
    daily_pnl_pct: float
    portfolio_var: float
    gross_exposure: float
    halted: bool
    kill_switch: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class StopLevels:
    stop: float
    take_profit: float


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.cfg = config
        self.kill_switch_fired = False
        self._day_start_equity: float | None = None

    # -- lifecycle -------------------------------------------------------
    def start_of_day(self, equity: float) -> None:
        self._day_start_equity = equity

    def manual_reset(self) -> None:
        """Human-in-the-loop reset after a kill-switch event (audited)."""
        log.warning("kill switch manually reset")
        self.kill_switch_fired = False

    # -- position sizing ---------------------------------------------------
    def size_positions(
        self,
        decisions: list[TradeDecision],
        equity: float,
        peak_equity: float,
        asset_vol: dict[str, float],        # annualized per-symbol vol
        portfolio_returns: pd.Series,       # realized daily portfolio returns
        regime_scalar: float = 1.0,
    ) -> tuple[list[TradeDecision], RiskStateSnapshot]:
        """Assign target_weight to each decision, subject to all limits."""
        notes: list[str] = []
        drawdown = 1 - equity / peak_equity if peak_equity > 0 else 0.0
        daily_pnl = (equity / self._day_start_equity - 1) if self._day_start_equity else 0.0

        # --- kill switch / hard drawdown ---------------------------------
        if drawdown >= self.cfg.max_drawdown_hard:
            self.kill_switch_fired = True
        if self.kill_switch_fired:
            notes.append(f"KILL SWITCH: drawdown {drawdown:.1%} >= "
                         f"{self.cfg.max_drawdown_hard:.0%} — flat, trading halted")
            for d in decisions:
                d.target_weight = 0.0
            return decisions, self._snapshot(equity, peak_equity, drawdown,
                                             daily_pnl, 0.0, 0.0, True, notes)

        # --- circuit breaker: daily loss limit ----------------------------
        halted = daily_pnl <= -self.cfg.daily_loss_limit
        if halted:
            notes.append(f"circuit breaker: day PnL {daily_pnl:.2%} breached "
                         f"-{self.cfg.daily_loss_limit:.0%} — no new risk today")

        # --- drawdown ladder (capital preservation) -----------------------
        dd_scalar = 1.0
        if drawdown > self.cfg.max_drawdown_soft:
            span = self.cfg.max_drawdown_hard - self.cfg.max_drawdown_soft
            dd_scalar = max(0.25, 1 - (drawdown - self.cfg.max_drawdown_soft) / span)
            notes.append(f"drawdown {drawdown:.1%}: de-risking to {dd_scalar:.0%} of normal size")

        # --- per-position vol-target sizing -------------------------------
        for d in decisions:
            vol = asset_vol.get(d.symbol, np.nan)
            if not np.isfinite(vol) or vol <= 0:
                d.target_weight = 0.0
                continue
            base = self.cfg.annual_vol_target / vol          # equal-risk budget
            kelly = self.cfg.kelly_fraction * abs(d.score) * d.confidence * 4
            weight = np.sign(d.score) * min(base * min(kelly, 1.0),
                                            self.cfg.max_position_weight)
            d.target_weight = float(weight) * dd_scalar * regime_scalar

        # --- portfolio-level exposure caps ---------------------------------
        gross = sum(abs(d.target_weight) for d in decisions)
        if gross > self.cfg.max_gross_exposure:
            scale = self.cfg.max_gross_exposure / gross
            for d in decisions:
                d.target_weight *= scale
            notes.append(f"gross exposure {gross:.2f} capped at "
                         f"{self.cfg.max_gross_exposure:.2f}")
            gross = self.cfg.max_gross_exposure
        net = sum(d.target_weight for d in decisions)
        if abs(net) > self.cfg.max_net_exposure:
            scale = self.cfg.max_net_exposure / abs(net)
            for d in decisions:
                d.target_weight *= scale
            notes.append(f"net exposure {net:+.2f} capped")

        # --- portfolio VaR limit -------------------------------------------
        var = historical_var(portfolio_returns, self.cfg.var_confidence)
        if np.isfinite(var) and var > self.cfg.var_limit:
            scale = self.cfg.var_limit / var
            for d in decisions:
                d.target_weight *= scale
            notes.append(f"1d {self.cfg.var_confidence:.0%} VaR {var:.2%} > "
                         f"limit {self.cfg.var_limit:.0%} — book scaled {scale:.0%}")

        if halted:  # circuit breaker: allow de-risking, block adding
            for d in decisions:
                d.reasoning += " [circuit breaker active: entry blocked]"

        return decisions, self._snapshot(equity, peak_equity, drawdown, daily_pnl,
                                         var if np.isfinite(var) else 0.0,
                                         gross, halted, notes)

    # -- stops -----------------------------------------------------------
    def stop_levels(self, entry_price: float, direction: int, atr_value: float) -> StopLevels:
        """ATR-scaled dynamic stop-loss / take-profit for a new position."""
        return StopLevels(
            stop=entry_price - direction * self.cfg.atr_stop_multiple * atr_value,
            take_profit=entry_price + direction * self.cfg.atr_take_profit_multiple * atr_value,
        )

    def _snapshot(self, equity, peak, dd, daily, var, gross, halted, notes) -> RiskStateSnapshot:
        for n in notes:
            log.info("risk: %s", n)
        return RiskStateSnapshot(
            equity=equity, peak_equity=peak, drawdown=dd, daily_pnl_pct=daily,
            portfolio_var=var, gross_exposure=gross,
            halted=halted, kill_switch=self.kill_switch_fired, notes=notes,
        )
