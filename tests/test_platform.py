"""Integration tests: decision engine, execution, metrics, and a short
end-to-end backtest."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from matterhorn_quant.backtest.engine import BacktestEngine
from matterhorn_quant.backtest.metrics import performance_summary
from matterhorn_quant.config import DEFAULT_SETTINGS, Settings
from matterhorn_quant.core.types import Bar, Order, OrderSide, Signal
from matterhorn_quant.data.providers import SyntheticProvider, load_universe
from matterhorn_quant.decision.engine import DecisionEngine
from matterhorn_quant.execution.broker import PaperBroker
from matterhorn_quant.execution.router import validate_order
from matterhorn_quant.sentiment.analyzer import SentimentAnalyzer
from matterhorn_quant.strategies.classic import MeanReversionStrategy, MomentumStrategy


def _bar(price=100.0, volume=1e6):
    return Bar("X", pd.Timestamp("2024-01-02"), price, price * 1.01, price * 0.99,
               price, volume)


def test_decision_engine_votes_and_filters():
    eng = DecisionEngine(DEFAULT_SETTINGS.decision, ["a", "b"])
    sigs = {"X": [Signal("X", "a", 0.8, 0.9, "up"), Signal("X", "b", 0.6, 0.7, "up")],
            "Y": [Signal("Y", "a", 0.05, 0.1, "noise")]}
    decisions = eng.decide(sigs)
    assert [d.symbol for d in decisions] == ["X"]  # Y filtered as low quality
    assert decisions[0].score > 0 and "a(" in decisions[0].reasoning


def test_decision_engine_adapts_weights():
    eng = DecisionEngine(DEFAULT_SETTINGS.decision, ["good", "bad"])
    for _ in range(60):
        eng.record_outcome(Signal("X", "good", 0.5, 0.8), +0.01)
        eng.record_outcome(Signal("X", "bad", 0.5, 0.8), -0.01)
    assert eng.weights["good"] > 1.2 > eng.weights["bad"]


def test_paper_broker_slippage_and_partial_fill():
    broker = PaperBroker(DEFAULT_SETTINGS.execution, 1_000_000)
    fills = broker.submit(Order(symbol="X", side=OrderSide.BUY, qty=100), _bar())
    assert len(fills) == 1 and fills[0].price > 100.0  # buy pays slippage
    thin = _bar(volume=500)  # participation cap 5% -> 25 shares max
    fills2 = broker.submit(Order(symbol="X", side=OrderSide.BUY, qty=100), thin)
    assert fills2[0].qty < 100


def test_order_validation_blocks_fat_fingers():
    ok, _ = validate_order(Order(symbol="X", side=OrderSide.BUY, qty=100),
                           _bar(), equity=1_000_000)
    assert ok
    too_big, reason = validate_order(Order(symbol="X", side=OrderSide.BUY, qty=10_000),
                                     _bar(), equity=100_000)
    assert not too_big and "notional" in reason


def test_sentiment_analyzer_direction():
    sa = SentimentAnalyzer()
    pos = sa.score_documents("X", ["Company beat estimates with record growth and "
                                   "raised guidance; analysts upgraded the stock."])
    neg = sa.score_documents("X", ["Earnings miss, guidance cut and an SEC "
                                   "investigation triggered a downgrade."])
    assert pos.score > 0.1 > -0.1 > neg.score
    assert sa.score_documents("X", ["not a strong quarter"]).score < 0


def test_metrics_known_values():
    equity = pd.Series(np.linspace(100, 121, 253))  # steady climb, no drawdown
    s = performance_summary(equity, trade_pnls=[10, -5, 20, -5])
    assert s["max_drawdown"] == 0.0
    assert 0.18 < s["cagr"] < 0.23
    assert s["win_rate"] == 0.5 and s["profit_factor"] == 3.0


def test_end_to_end_backtest_smoke():
    data = load_universe(SyntheticProvider(seed=3), ["AA", "BB", "CC"],
                         "2020-01-01", "2023-06-01")
    settings = Settings()
    engine = BacktestEngine(settings,
                            [MomentumStrategy(), MeanReversionStrategy()],
                            use_ml=False)
    result = engine.run(data)
    final = result.equity.iloc[-1]
    assert np.isfinite(final) and final > 0
    # risk limits should keep the book from catastrophic loss even on chaos data
    assert result.summary["max_drawdown"] > -0.5
    assert "sharpe" in result.summary
