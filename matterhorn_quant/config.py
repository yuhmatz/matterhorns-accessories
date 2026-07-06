"""Central configuration.

Secrets (API keys, broker credentials) are NEVER stored in code or in this
file — they are read from environment variables (in production: a secrets
manager such as AWS Secrets Manager / Vault, injected at runtime).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def secret(name: str, default: str = "") -> str:
    """Read a secret from the environment / injected secret store."""
    return os.environ.get(name, default)


@dataclass
class RiskConfig:
    annual_vol_target: float = 0.12          # portfolio volatility target
    max_position_weight: float = 0.10        # per-name cap (fraction of equity)
    max_gross_exposure: float = 1.0          # sum of |weights|
    max_net_exposure: float = 1.0
    max_sector_weight: float = 0.30
    daily_loss_limit: float = 0.02           # halt new entries beyond -2% day
    max_drawdown_soft: float = 0.10          # start de-risking
    max_drawdown_hard: float = 0.20          # kill switch: liquidate, halt
    var_confidence: float = 0.99
    var_limit: float = 0.03                  # 1-day 99% VaR cap (fraction of equity)
    atr_stop_multiple: float = 3.0
    atr_take_profit_multiple: float = 6.0
    kelly_fraction: float = 0.25             # fraction of full Kelly


@dataclass
class ExecutionConfig:
    commission_per_share: float = 0.005
    commission_min: float = 1.0
    slippage_bps: float = 5.0                # baseline market-impact assumption
    max_participation: float = 0.05          # max share of bar volume per order
    twap_slices: int = 4


@dataclass
class DecisionConfig:
    min_confidence: float = 0.35             # filter low-quality trades
    min_abs_score: float = 0.15
    max_positions: int = 20
    strategy_learning_rate: float = 0.05     # adaptive strategy-weight updates
    min_strategy_weight: float = 0.25
    max_strategy_weight: float = 2.0


@dataclass
class BacktestConfig:
    initial_equity: float = 1_000_000.0
    warmup_bars: int = 252


@dataclass
class Settings:
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data_providers: tuple[str, ...] = ("primary", "backup")
    base_currency: str = "USD"


DEFAULT_SETTINGS = Settings()
