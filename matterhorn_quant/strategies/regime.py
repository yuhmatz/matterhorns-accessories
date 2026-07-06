"""Market regime detection and state classification.

A Gaussian mixture over (trailing return, realized volatility) classifies
each day into bull / bear / high-vol-chop. The decision engine uses the
regime to modulate strategy weights (momentum favored in trends, mean
reversion in chop) and the risk manager uses it to scale exposure —
"market regime adaptation" in one place, consumed everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture


@dataclass
class RegimeState:
    label: str            # "bull" | "bear" | "chop"
    probability: float    # confidence of classification
    realized_vol: float   # annualized


class RegimeDetector:
    """Rolling regime classifier over an equal-weight universe index."""

    LABELS = ("bull", "bear", "chop")

    def __init__(self, refit_every: int = 63, lookback: int = 756):
        self.refit_every = refit_every
        self.lookback = lookback
        self._model: GaussianMixture | None = None
        self._label_map: dict[int, str] = {}
        self._last_fit = -1

    @staticmethod
    def _features(index_close: pd.Series) -> pd.DataFrame:
        ret = index_close.pct_change()
        return pd.DataFrame({
            "trail_ret": ret.rolling(63).mean() * 252,
            "vol": ret.rolling(21).std() * np.sqrt(252),
        })

    def classify(self, index_close: pd.Series, i: int) -> RegimeState:
        feats = self._features(index_close.iloc[: i + 1]).dropna()
        if len(feats) < 200:
            return RegimeState("chop", 0.0, float("nan"))

        if self._model is None or i - self._last_fit >= self.refit_every:
            train = feats.iloc[-self.lookback:]
            model = GaussianMixture(n_components=3, covariance_type="full",
                                    random_state=0, n_init=3).fit(train.values)
            # name components by their mean (return, vol) profile
            means = model.means_
            order_by_ret = np.argsort(means[:, 0])
            label_map = {int(order_by_ret[0]): "bear", int(order_by_ret[-1]): "bull"}
            label_map[int(order_by_ret[1])] = "chop"
            self._model, self._label_map, self._last_fit = model, label_map, i

        x = feats.values[-1:].astype(float)
        probs = self._model.predict_proba(x)[0]
        k = int(probs.argmax())
        return RegimeState(
            label=self._label_map[k],
            probability=float(probs[k]),
            realized_vol=float(feats["vol"].iloc[-1]),
        )

    @staticmethod
    def strategy_tilts(regime: RegimeState) -> dict[str, float]:
        """Multiplicative strategy-weight tilts per regime."""
        if regime.label == "bull":
            return {"momentum": 1.3, "breakout": 1.2, "mean_reversion": 0.8, "ml": 1.0}
        if regime.label == "bear":
            return {"momentum": 1.1, "breakout": 1.0, "mean_reversion": 0.6, "ml": 0.9}
        return {"momentum": 0.7, "breakout": 0.7, "mean_reversion": 1.3, "ml": 1.0}

    @staticmethod
    def exposure_scalar(regime: RegimeState) -> float:
        """Gross-exposure multiplier per regime (dynamic risk adjustment)."""
        return {"bull": 1.0, "chop": 0.85, "bear": 0.6}[regime.label]
