"""Order validation and smart order routing.

`validate_order` is the pre-trade compliance gate (fat-finger limits,
notional caps, price sanity). `SmartOrderRouter` slices parent orders into
TWAP child orders capped by participation — on daily bars this is a
simulation of the schedule; in production the same interface routes child
orders across venues with latency monitoring.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from ..config import ExecutionConfig
from ..core.types import Bar, Fill, Order, OrderSide, OrderType
from .broker import Broker

log = logging.getLogger(__name__)


MAX_NOTIONAL_PCT = 0.15


def validate_order(order: Order, bar: Bar, equity: float,
                   max_notional_pct: float = MAX_NOTIONAL_PCT,
                   max_price_deviation: float = 0.10) -> tuple[bool, str]:
    """Pre-trade checks. Returns (ok, reason).

    All price references use the bar's OPEN — the price actually known when
    the order is submitted; the close of the execution bar is future data.
    """
    if order.qty <= 0:
        return False, "quantity must be positive"
    notional = order.qty * bar.open
    if notional > max_notional_pct * equity:
        return False, (f"notional ${notional:,.0f} exceeds "
                       f"{max_notional_pct:.0%} of equity")
    if order.type == OrderType.LIMIT and order.limit_price is not None:
        deviation = abs(order.limit_price / bar.open - 1)
        if deviation > max_price_deviation:
            return False, f"limit price {deviation:.1%} away from market"
    return True, "ok"


@dataclass
class ExecutionReport:
    parent: Order
    fills: list[Fill] = field(default_factory=list)
    rejected_reason: str = ""
    latency_ms: float = 0.0

    @property
    def avg_price(self) -> float:
        total = sum(f.qty for f in self.fills)
        return sum(f.qty * f.price for f in self.fills) / total if total else 0.0


class SmartOrderRouter:
    def __init__(self, broker: Broker, config: ExecutionConfig):
        self.broker = broker
        self.cfg = config
        self.latencies_ms: list[float] = []

    def execute(self, order: Order, bar: Bar, equity: float) -> ExecutionReport:
        report = ExecutionReport(parent=order)
        ok, reason = validate_order(order, bar, equity)
        if not ok:
            report.rejected_reason = reason
            log.warning("order rejected (%s %s x%.0f): %s",
                        order.side.value, order.symbol, order.qty, reason)
            return report

        t0 = time.perf_counter()
        # cap TOTAL participation at the configured share of bar volume —
        # slicing must not multiply the per-order liquidity cap
        exec_qty = min(order.qty, max(1.0, self.cfg.max_participation * bar.volume))
        # TWAP-slice only orders big enough to have market impact; slicing
        # small orders just multiplies minimum commissions
        n_slices = (self.cfg.twap_slices
                    if exec_qty * bar.open > 0.02 * equity else 1)
        slice_qty = exec_qty / n_slices
        for _ in range(n_slices):
            child = Order(symbol=order.symbol, side=order.side, qty=slice_qty,
                          type=order.type, limit_price=order.limit_price)
            report.fills.extend(self.broker.submit(child, bar))
        report.latency_ms = (time.perf_counter() - t0) * 1000
        self.latencies_ms.append(report.latency_ms)
        if len(self.latencies_ms) > 1000:
            self.latencies_ms.pop(0)
        return report
