"""Central decision engine.

Combines every model's signals per symbol via confidence-weighted voting,
with three layers of adaptivity:

1. Adaptive strategy weights — each strategy's weight is updated online by
   exponentially-weighted realized signal-vs-outcome performance (a strategy
   that stops working votes less; one that's hot votes more, within bounds).
2. Regime tilts — the regime detector multiplies weights per market state.
3. Quality filters — decisions below confidence/score thresholds are
   dropped; survivors are ranked and capped at max_positions.

Every decision carries a reasoning string concatenating the contributing
signals so each trade is explainable after the fact.
"""

from __future__ import annotations

import numpy as np

from ..config import DecisionConfig
from ..core.types import Signal, TradeDecision


class DecisionEngine:
    def __init__(self, config: DecisionConfig, strategy_names: list[str]):
        self.cfg = config
        self.weights: dict[str, float] = {n: 1.0 for n in strategy_names}
        # EW performance tracker per strategy: mean of strength * realized return sign
        self._perf: dict[str, float] = {n: 0.0 for n in strategy_names}

    # -- adaptive learning -------------------------------------------------
    def record_outcome(self, signal: Signal, realized_return: float) -> None:
        """Online weight update: did the signal point the right way?"""
        name = signal.strategy
        if name not in self.weights:
            self.weights[name] = 1.0
            self._perf[name] = 0.0
        hit = np.sign(signal.strength) * np.sign(realized_return)  # +1 / -1 / 0
        lr = self.cfg.strategy_learning_rate
        self._perf[name] = (1 - lr) * self._perf[name] + lr * hit
        self.weights[name] = float(np.clip(
            1.0 + self._perf[name],
            self.cfg.min_strategy_weight, self.cfg.max_strategy_weight,
        ))

    # -- combination -------------------------------------------------------
    def decide(
        self,
        signals_by_symbol: dict[str, list[Signal]],
        regime_tilts: dict[str, float] | None = None,
    ) -> list[TradeDecision]:
        tilts = regime_tilts or {}
        decisions: list[TradeDecision] = []

        for symbol, signals in signals_by_symbol.items():
            if not signals:
                continue
            num = den = 0.0
            for s in signals:
                w = self.weights.get(s.strategy, 1.0) * tilts.get(s.strategy, 1.0)
                vote = w * s.confidence
                num += vote * s.strength
                den += vote
            if den == 0:
                continue
            score = num / den

            # agreement: do the contributing models point the same way?
            dirs = [np.sign(s.strength) for s in signals if s.strength]
            agreement = abs(np.mean(dirs)) if dirs else 0.0
            avg_conf = float(np.mean([s.confidence for s in signals]))
            confidence = float(0.6 * avg_conf + 0.4 * agreement)

            # quality filter
            if confidence < self.cfg.min_confidence or abs(score) < self.cfg.min_abs_score:
                continue

            parts = [f"{s.strategy}(w={self.weights.get(s.strategy, 1.0):.2f}): "
                     f"{s.strength:+.2f}@{s.confidence:.2f} — {s.reasoning}"
                     for s in signals]
            decisions.append(TradeDecision(
                symbol=symbol, score=float(score), confidence=confidence,
                target_weight=0.0, contributing=list(signals),
                reasoning=(f"combined score {score:+.2f}, confidence {confidence:.2f}, "
                           f"agreement {agreement:.2f} | " + " || ".join(parts)),
            ))

        # rank by edge quality, keep the best
        decisions.sort(key=lambda d: abs(d.score) * d.confidence, reverse=True)
        return decisions[: self.cfg.max_positions]
