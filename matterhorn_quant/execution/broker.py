"""Broker abstraction layer and paper-trading broker.

Live adapters (Interactive Brokers, Alpaca, …) implement the same `Broker`
interface, so strategy/risk/decision code is broker-agnostic. `PaperBroker`
fills against bar data with a square-root market-impact slippage model,
participation-capped partial fills, and per-share commissions — the same
fill model the backtester uses, so paper and backtest results agree.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from ..config import ExecutionConfig
from ..core.types import Bar, Fill, Order, OrderSide, OrderStatus, OrderType

log = logging.getLogger(__name__)


class Broker(ABC):
    @abstractmethod
    def submit(self, order: Order, bar: Bar) -> list[Fill]:
        """Submit an order; returns resulting fills (possibly partial/empty)."""

    @abstractmethod
    def positions(self) -> dict[str, float]: ...

    @abstractmethod
    def cash(self) -> float: ...


class PaperBroker(Broker):
    def __init__(self, config: ExecutionConfig, initial_cash: float):
        self.cfg = config
        self._cash = initial_cash
        self._positions: dict[str, float] = {}
        self.fills: list[Fill] = []
        self.rejected: list[Order] = []

    # -- Broker interface ---------------------------------------------------
    def submit(self, order: Order, bar: Bar) -> list[Fill]:
        if order.qty <= 0:
            order.status = OrderStatus.REJECTED
            order.reason = "non-positive quantity"
            self.rejected.append(order)
            return []

        # participation cap -> partial fill on thin volume
        max_qty = max(1.0, self.cfg.max_participation * bar.volume)
        fill_qty = min(order.qty, max_qty)

        price = self._fill_price(order, bar, fill_qty)
        if price is None:  # limit not marketable this bar
            order.status = OrderStatus.CANCELLED
            order.reason = "limit price not reached"
            return []

        commission = max(self.cfg.commission_min,
                         self.cfg.commission_per_share * fill_qty)
        fill = Fill(order_id=order.id, symbol=order.symbol, side=order.side,
                    qty=fill_qty, price=price, commission=commission, ts=bar.ts)

        signed = fill_qty if order.side == OrderSide.BUY else -fill_qty
        self._cash -= signed * price + commission
        self._positions[order.symbol] = self._positions.get(order.symbol, 0.0) + signed
        if abs(self._positions[order.symbol]) < 1e-9:
            del self._positions[order.symbol]

        order.filled_qty += fill_qty
        order.status = (OrderStatus.FILLED if order.filled_qty >= order.qty - 1e-9
                        else OrderStatus.PARTIALLY_FILLED)
        self.fills.append(fill)
        return [fill]

    def positions(self) -> dict[str, float]:
        return dict(self._positions)

    def cash(self) -> float:
        return self._cash

    def equity(self, prices: dict[str, float]) -> float:
        return self._cash + sum(q * prices[s] for s, q in self._positions.items())

    # -- microstructure model -------------------------------------------------
    def _fill_price(self, order: Order, bar: Bar, qty: float) -> float | None:
        ref = bar.open
        if order.type == OrderType.LIMIT and order.limit_price is not None:
            marketable = (order.limit_price >= bar.low if order.side == OrderSide.BUY
                          else order.limit_price <= bar.high)
            if not marketable:
                return None
            ref = (min(order.limit_price, bar.open) if order.side == OrderSide.BUY
                   else max(order.limit_price, bar.open))
        # square-root impact: cost grows with participation
        participation = qty / max(bar.volume, 1.0)
        impact_bps = self.cfg.slippage_bps * (1 + 10 * np.sqrt(participation))
        direction = 1 if order.side == OrderSide.BUY else -1
        price = float(ref * (1 + direction * impact_bps / 10_000))
        if order.type == OrderType.LIMIT and order.limit_price is not None:
            # a limit fill can never be worse than the limit price
            price = (min(price, order.limit_price) if order.side == OrderSide.BUY
                     else max(price, order.limit_price))
        return price


def bar_from_row(symbol: str, ts: pd.Timestamp, row: pd.Series) -> Bar:
    return Bar(symbol=symbol, ts=ts, open=float(row["open"]), high=float(row["high"]),
               low=float(row["low"]), close=float(row["close"]), volume=float(row["volume"]))
