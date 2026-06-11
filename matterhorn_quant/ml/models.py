"""ML signal models: walk-forward-trained ensemble with drift monitoring
and explainability.

Design choices that matter more than model sophistication:
- Walk-forward refits (train strictly on the past, predict the next block)
  prevent lookahead — the #1 cause of fake backtest alpha.
- An ensemble of diverse, *regularized* learners beats one deep model on
  small noisy financial samples.
- Continuous evaluation: rolling out-of-sample accuracy gates the model's
  confidence (self-evaluation); feature importances provide explainability;
  population-stability drift checks trigger early refits (adaptive/online
  learning).

Predictions are computed in blocks at refit time (each row is consumed only
at its own bar, so causality holds) — batching keeps backtests and live
replay fast.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..core.types import Signal
from ..strategies.base import Strategy
from .features import FEATURE_COLUMNS, LABEL_HORIZON, build_features


def _make_models() -> dict:
    return {
        "gbm": GradientBoostingClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.05,
            subsample=0.8, random_state=0),
        "rf": RandomForestClassifier(
            n_estimators=200, max_depth=5, min_samples_leaf=50,
            max_features="sqrt", random_state=0, n_jobs=-1),
        "logit": make_pipeline(
            StandardScaler(), LogisticRegression(C=0.1, max_iter=1000)),
    }


class WalkForwardEnsemble:
    """Pooled cross-sectional classifier P(5-day return > 0), refit on a
    rolling window every `refit_every` bars."""

    def __init__(self, train_window: int = 504, refit_every: int = 63,
                 min_train: int = 350):
        self.train_window = train_window
        self.refit_every = refit_every
        self.min_train = min_train
        self.models: dict | None = None
        self.last_fit_i = -10**9
        self.oos_hits: list[float] = []   # rolling out-of-sample correctness
        self._train_means: pd.Series | None = None
        self._train_stds: pd.Series | None = None
        self._importance: pd.Series = pd.Series(dtype=float)
        # symbol -> (block_start_i, P(up) array, agreement array)
        self._pred_cache: dict[str, tuple[int, np.ndarray, np.ndarray]] = {}

    # -- training ------------------------------------------------------
    def maybe_refit(self, features_by_symbol: dict[str, pd.DataFrame], i: int) -> None:
        due = self.models is None or i - self.last_fit_i >= self.refit_every
        if not due and not self._drift_detected(features_by_symbol, i):
            return
        lo = max(0, i - self.train_window)
        rows = []
        for feats in features_by_symbol.values():
            # exclude the label horizon so no training label peeks past bar i
            chunk = feats.iloc[lo: i - LABEL_HORIZON]
            rows.append(chunk.dropna(subset=FEATURE_COLUMNS + ["label_up"]))
        train = pd.concat(rows)
        if len(train) < self.min_train or len(np.unique(train["label_up"])) < 2:
            return
        X, y = train[FEATURE_COLUMNS].values, train["label_up"].values
        self.models = {name: m.fit(X, y) for name, m in _make_models().items()}
        self._train_means = train[FEATURE_COLUMNS].mean()
        self._train_stds = train[FEATURE_COLUMNS].std().replace(0, np.nan)
        self.last_fit_i = i
        self._cache_importance()
        self._cache_predictions(features_by_symbol, i)

    def _drift_detected(self, features_by_symbol: dict[str, pd.DataFrame], i: int) -> bool:
        """Population-stability check: recent feature means vs training
        distribution, in training-std units."""
        if self._train_means is None or i - self.last_fit_i < 21 or i % 5:
            return False
        recent = pd.concat(
            [f.iloc[i - 21: i][FEATURE_COLUMNS] for f in features_by_symbol.values()]
        ).mean()
        z = (recent - self._train_means).abs() / self._train_stds
        return bool((z > 2.0).sum() >= 5)

    # -- prediction ----------------------------------------------------
    def _cache_predictions(self, features_by_symbol: dict[str, pd.DataFrame], i: int) -> None:
        """Batch-predict the upcoming block for every symbol."""
        hi_pad = self.refit_every + 30  # cover drift-delayed refits
        self._pred_cache.clear()
        for sym, feats in features_by_symbol.items():
            X = feats[FEATURE_COLUMNS].iloc[i: i + hi_pad].values
            if len(X) == 0:
                continue
            valid = ~np.isnan(X).any(axis=1)
            probs = np.full((len(self.models), len(X)), np.nan)
            if valid.any():
                for k, m in enumerate(self.models.values()):
                    probs[k, valid] = m.predict_proba(X[valid])[:, 1]
            self._pred_cache[sym] = (i, probs.mean(axis=0),
                                     np.maximum(0.0, 1.0 - 2.0 * probs.std(axis=0)))

    def predict_at(self, symbol: str, i: int) -> Optional[tuple[float, float]]:
        """Return (ensemble P(up), model agreement in [0,1]) for bar i, or None."""
        cached = self._pred_cache.get(symbol)
        if cached is None:
            return None
        start, p_up, agree = cached
        k = i - start
        if k < 0 or k >= len(p_up) or np.isnan(p_up[k]):
            return None
        return float(p_up[k]), float(agree[k])

    def record_outcome(self, predicted_up: bool, realized_up: bool) -> None:
        self.oos_hits.append(float(predicted_up == realized_up))
        if len(self.oos_hits) > 250:
            self.oos_hits.pop(0)

    @property
    def oos_accuracy(self) -> float:
        return float(np.mean(self.oos_hits)) if len(self.oos_hits) >= 30 else 0.5

    # -- explainability --------------------------------------------------
    def _cache_importance(self) -> None:
        imp = np.zeros(len(FEATURE_COLUMNS))
        n = 0
        for m in self.models.values():
            est = m[-1] if hasattr(m, "steps") else m
            if hasattr(est, "feature_importances_"):
                imp += est.feature_importances_
                n += 1
            elif hasattr(est, "coef_"):
                c = np.abs(est.coef_[0])
                imp += c / (c.sum() + 1e-12)
                n += 1
        self._importance = pd.Series(
            imp / max(n, 1), index=FEATURE_COLUMNS).sort_values(ascending=False)

    def feature_importance(self) -> pd.Series:
        return self._importance


class MLStrategy(Strategy):
    """Adapter exposing the walk-forward ensemble as a Strategy.

    Confidence is gated by realized out-of-sample accuracy: if the model
    stops working, its vote automatically fades (self-evaluation feeding
    self-adjustment).
    """

    name = "ml"

    def __init__(self, ensemble: WalkForwardEnsemble):
        self.ensemble = ensemble

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        return df  # ensemble consumes the shared feature store directly

    def signal(self, symbol: str, df: pd.DataFrame, i: int) -> Optional[Signal]:
        pred = self.ensemble.predict_at(symbol, i)
        if pred is None:
            return None
        p_up, agreement = pred
        strength = float(np.clip((p_up - 0.5) * 4, -1, 1))  # 0.5->0, 0.75->1
        if abs(strength) < 0.1:
            return None
        edge_quality = float(np.clip((self.ensemble.oos_accuracy - 0.45) * 5, 0, 1))
        confidence = 0.5 * agreement + 0.5 * edge_quality
        top = self.ensemble.feature_importance().head(3)
        drivers = ", ".join(top.index) if len(top) else "n/a"
        return self._make(
            symbol, strength, confidence,
            f"ensemble P(up,5d)={p_up:.2f}, agreement={agreement:.2f}, "
            f"OOS acc={self.ensemble.oos_accuracy:.2f}; top drivers: {drivers}",
        )
