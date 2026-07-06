"""Shared domain types used across all subsystems."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd


class Direction(Enum):
    LONG = 1
    FLAT = 0
    SHORT = -1


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Bar:
    """A single OHLCV bar."""

    symbol: str
    ts: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Signal:
    """A directional view emitted by a single strategy/model.

    strength is in [-1, 1] (sign = direction, magnitude = conviction of the
    model itself); confidence is in [0, 1] and reflects how reliable the
    model believes this particular signal is (e.g. regime fit, data quality).
    """

    symbol: str
    strategy: str
    strength: float
    confidence: float
    reasoning: str = ""

    @property
    def direction(self) -> Direction:
        if self.strength > 0:
            return Direction.LONG
        if self.strength < 0:
            return Direction.SHORT
        return Direction.FLAT


@dataclass
class TradeDecision:
    """Output of the decision engine for one symbol on one date."""

    symbol: str
    score: float            # combined signal in [-1, 1]
    confidence: float       # [0, 1]
    target_weight: float    # fraction of equity (signed), set by risk manager
    contributing: list[Signal] = field(default_factory=list)
    reasoning: str = ""


_order_ids = itertools.count(1)


@dataclass
class Order:
    symbol: str
    side: OrderSide
    qty: float
    type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    id: int = field(default_factory=lambda: next(_order_ids))
    status: OrderStatus = OrderStatus.NEW
    filled_qty: float = 0.0
    reason: str = ""


@dataclass
class Fill:
    order_id: int
    symbol: str
    side: OrderSide
    qty: float
    price: float
    commission: float
    ts: pd.Timestamp


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0

    def market_value(self, price: float) -> float:
        return self.qty * price

    def apply_fill(self, fill: Fill) -> float:
        """Update position with a fill. Returns realized PnL (ex-commission)."""
        signed = fill.qty if fill.side == OrderSide.BUY else -fill.qty
        realized = 0.0
        if self.qty * signed >= 0:  # opening or adding
            total_cost = self.avg_price * abs(self.qty) + fill.price * abs(signed)
            self.qty += signed
            self.avg_price = total_cost / abs(self.qty) if self.qty else 0.0
        else:  # reducing or flipping
            closing = min(abs(signed), abs(self.qty))
            pnl_per_share = (fill.price - self.avg_price) * (1 if self.qty > 0 else -1)
            realized = pnl_per_share * closing
            self.qty += signed
            if self.qty == 0:
                self.avg_price = 0.0
            elif abs(signed) > closing:  # flipped through zero
                self.avg_price = fill.price
        return realized
