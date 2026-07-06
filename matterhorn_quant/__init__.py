"""Matterhorn Quant — institutional-grade AI-powered trading platform (reference implementation).

Subsystems:
    data        Market data providers with redundancy/failover
    indicators  Technical analysis engine
    strategies  Quantitative trading models (momentum, mean reversion, stat-arb, regime)
    ml          Machine-learning signal models, feature engineering, walk-forward training
    sentiment   News / text sentiment scoring
    risk        Position sizing, VaR, limits, circuit breakers, kill switch
    portfolio   Optimization, rebalancing, allocation
    decision    Central decision engine (weighted voting, confidence, reasoning)
    backtest    Backtesting, walk-forward analysis, stress testing, metrics
    execution   Broker abstraction, order validation, smart routing, paper trading
    monitoring  Logging, health checks, alerting, audit trail
    agents      Multi-agent orchestration loop
"""

__version__ = "0.1.0"
