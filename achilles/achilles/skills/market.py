"""S&P 500 market briefing — read-only, with RSI(14) and MACD(12,26,9).

The indicator math is pure Python and unit-tested; only the price fetch
touches the network (yfinance if installed, else Stooq CSV via urllib —
both keyless and read-only).
"""
from __future__ import annotations

import csv
import io
import urllib.request
from typing import Sequence


def ema(values: Sequence[float], period: int) -> list[float]:
    """Exponential moving average, seeded with the SMA of the first period."""
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out = [seed]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes: Sequence[float], period: int = 14) -> float:
    """Wilder-smoothed RSI of the last close."""
    if len(closes) < period + 1:
        raise ValueError(f"need at least {period + 1} closes, got {len(closes)}")
    gains, losses = [], []
    for prev, cur in zip(closes, closes[1:]):
        change = cur - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(closes: Sequence[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> tuple[float, float, float]:
    """(macd_line, signal_line, histogram) for the last close."""
    if len(closes) < slow + signal:
        raise ValueError(f"need at least {slow + signal} closes, got {len(closes)}")
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    # align: ema_slow starts (slow - fast) entries later than ema_fast
    offset = slow - fast
    macd_line = [f - s for f, s in zip(ema_fast[offset:], ema_slow)]
    signal_line = ema(macd_line, signal)
    return macd_line[-1], signal_line[-1], macd_line[-1] - signal_line[-1]


def fetch_sp500_closes(days: int = 120) -> list[float]:
    """Daily closes for the S&P 500, most recent last."""
    try:
        import yfinance as yf  # optional

        hist = yf.Ticker("^GSPC").history(period=f"{days}d")
        closes = [float(c) for c in hist["Close"].tolist()]
        if closes:
            return closes
    except Exception:
        pass
    # Keyless fallback: Stooq daily CSV (^spx)
    url = "https://stooq.com/q/d/l/?s=%5Espx&i=d"
    with urllib.request.urlopen(url, timeout=15) as resp:
        text = resp.read().decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    closes = [float(r["Close"]) for r in rows if r.get("Close") not in (None, "", "-")]
    return closes[-days:]


def briefing() -> str:
    closes = fetch_sp500_closes()
    if len(closes) < 40:
        return "Market data is unavailable right now."
    last = closes[-1]
    change = (last / closes[-2] - 1.0) * 100.0
    r = rsi(closes)
    m, s, h = macd(closes)
    bias = "bullish" if h > 0 else "bearish"
    zone = "overbought" if r >= 70 else "oversold" if r <= 30 else "neutral"
    return (f"S&P 500 at {last:,.2f} ({change:+.2f}% on the day). "
            f"RSI(14) {r:.1f} ({zone}); MACD histogram {h:+.2f} ({bias}).")


def handle(command: str) -> str:
    try:
        return briefing()
    except Exception as exc:  # network may be down — degrade, don't crash
        return f"Couldn't fetch market data: {exc}"
