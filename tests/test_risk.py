import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from matterhorn_quant.config import RiskConfig
from matterhorn_quant.core.types import TradeDecision
from matterhorn_quant.risk.manager import RiskManager
from matterhorn_quant.risk.var import expected_shortfall, historical_var, parametric_var


def _decisions(symbols, score=0.8, conf=0.8):
    return [TradeDecision(symbol=s, score=score, confidence=conf, target_weight=0.0)
            for s in symbols]


def _returns(n=500, seed=0):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0003, 0.01, n))


def test_var_estimators_positive_and_ordered():
    r = _returns()
    var99 = historical_var(r, 0.99)
    var95 = historical_var(r, 0.95)
    assert var99 > var95 > 0
    assert parametric_var(r, 0.99) > 0
    assert expected_shortfall(r, 0.975) >= var95


def test_position_cap_and_gross_limit():
    rm = RiskManager(RiskConfig())
    rm.start_of_day(1_000_000)
    decisions, state = rm.size_positions(
        _decisions(list("ABCDEFGHIJKLMNOP")), 1_000_000, 1_000_000,
        {s: 0.05 for s in "ABCDEFGHIJKLMNOP"},  # very low vol -> big raw sizes
        _returns())
    assert all(abs(d.target_weight) <= RiskConfig().max_position_weight + 1e-9
               for d in decisions)
    assert sum(abs(d.target_weight) for d in decisions) <= RiskConfig().max_gross_exposure + 1e-6


def test_daily_loss_circuit_breaker():
    rm = RiskManager(RiskConfig())
    rm.start_of_day(1_000_000)
    _, state = rm.size_positions(
        _decisions(["A"]), 970_000, 1_000_000, {"A": 0.2}, _returns())
    assert state.halted


def test_kill_switch_flattens_book():
    rm = RiskManager(RiskConfig())
    rm.start_of_day(800_000)
    decisions, state = rm.size_positions(
        _decisions(["A", "B"]), 790_000, 1_000_000, {"A": 0.2, "B": 0.2}, _returns())
    assert state.kill_switch
    assert all(d.target_weight == 0.0 for d in decisions)
    # stays halted until manual reset
    decisions2, state2 = rm.size_positions(
        _decisions(["A"]), 900_000, 1_000_000, {"A": 0.2}, _returns())
    assert state2.kill_switch and decisions2[0].target_weight == 0.0
    rm.manual_reset()
    assert not rm.kill_switch_fired


def test_drawdown_ladder_derisks():
    cfg = RiskConfig()
    rm = RiskManager(cfg)
    rm.start_of_day(1_000_000)
    full, _ = rm.size_positions(_decisions(["A"]), 1_000_000, 1_000_000,
                                {"A": 0.2}, _returns())
    rm2 = RiskManager(cfg)
    rm2.start_of_day(850_000)
    derisked, _ = rm2.size_positions(_decisions(["A"]), 850_000, 1_000_000,
                                     {"A": 0.2}, _returns())
    assert abs(derisked[0].target_weight) < abs(full[0].target_weight)
