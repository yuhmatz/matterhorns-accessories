"""Multi-agent orchestration.

The platform is organized as cooperating specialist agents around a shared
context, mirroring an institutional desk:

    DataAgent        owns ingestion, validation, failover
    AnalystAgents    one per model family (technical, quant, ML, sentiment)
    RegimeAgent      classifies market state
    DecisionAgent    chairs the vote (DecisionEngine)
    RiskAgent        veto power: sizing, limits, circuit breakers
    ExecutionAgent   owns order routing and fill quality
    OpsAgent         health, alerting, audit

Agents communicate via the typed objects in core.types (Signal,
TradeDecision, Order, Fill) — in production these flow over a message bus
(Kafka/Redis streams) so agents scale and fail independently. The
BacktestEngine is this same pipeline run against historical bars; this
orchestrator runs it as a live/paper trading cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import Settings
from ..monitoring.ops import AlertManager, AuditLog, HealthMonitor, Severity

log = logging.getLogger(__name__)


@dataclass
class CycleReport:
    n_signals: int
    n_decisions: int
    n_orders: int
    equity: float
    regime: str
    halted: bool
    notes: list[str]


class Orchestrator:
    """Coordinates one full decision cycle and the self-improvement loop.

    The self-improvement loop has three feedback paths, all implemented in
    the subsystems and exercised every cycle:
      1. DecisionEngine.record_outcome — strategy weights adapt to realized
         signal quality (per-strategy hit rates).
      2. WalkForwardEnsemble — periodic refits, drift-triggered early refits,
         and OOS-accuracy-gated confidence.
      3. RiskManager — drawdown ladder and regime scalars adjust risk
         appetite to current conditions.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.health = HealthMonitor()
        self.alerts = AlertManager()
        self.audit = AuditLog()

    def run_cycle(self, engine, data) -> CycleReport:
        """One paper/live cycle = a backtest step over the latest bar.

        The BacktestEngine and the live path are the same code; live mode
        feeds the engine an expanding window ending at the current bar.
        """
        self.health.beat("orchestrator")
        result = engine.run(data)
        equity = float(result.equity.iloc[-1])
        regime = str(result.regime_history.iloc[-2]) if len(result.regime_history) > 1 else "n/a"
        halted = any("circuit breaker" in e or "KILL SWITCH" in e
                     for e in result.risk_events[-5:])
        for event in result.risk_events[-5:]:
            self.audit.record("risk_event", event)
            if "KILL SWITCH" in event:
                self.alerts.alert(Severity.CRITICAL, "kill switch fired", event)
            elif "circuit breaker" in event:
                self.alerts.alert(Severity.WARNING, "circuit breaker", event)
        stale = self.health.unhealthy()
        if stale:
            self.alerts.alert(Severity.WARNING, "stale components", ", ".join(stale))
        report = CycleReport(
            n_signals=sum(len(d.contributing) for d in result.sample_decisions),
            n_decisions=len(result.sample_decisions),
            n_orders=result.n_fills,
            equity=equity, regime=regime, halted=halted,
            notes=result.risk_events[-3:],
        )
        self.audit.record("cycle", report)
        return report
