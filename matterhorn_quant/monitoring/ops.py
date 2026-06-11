"""Operations: structured logging, health monitoring, alerting, and an
append-only audit trail.

The reference implementation logs to files and stdout; production swaps the
sinks (Prometheus metrics, PagerDuty/SNS for alerts, object storage with
write-once retention for the audit log) without changing call sites.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable


def setup_logging(log_dir: str | Path = "logs", level: int = logging.INFO) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    logging.basicConfig(
        level=level, format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Path(log_dir) / "platform.log"),
        ],
    )


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertManager:
    """Fan-out alerts to registered channels (email, mobile push, chat).

    Channels are callables `(severity, subject, body) -> None`; production
    registers SES/SNS/PagerDuty senders. Critical alerts are also raised on
    every channel regardless of its severity filter.
    """

    def __init__(self):
        self._channels: list[tuple[Severity, Callable[[Severity, str, str], None]]] = []
        self.log = logging.getLogger("alerts")

    def register(self, min_severity: Severity,
                 channel: Callable[[Severity, str, str], None]) -> None:
        self._channels.append((min_severity, channel))

    def alert(self, severity: Severity, subject: str, body: str = "") -> None:
        order = [Severity.INFO, Severity.WARNING, Severity.CRITICAL]
        self.log.log(
            logging.CRITICAL if severity == Severity.CRITICAL else
            logging.WARNING if severity == Severity.WARNING else logging.INFO,
            "[%s] %s — %s", severity.value, subject, body)
        for min_sev, channel in self._channels:
            if order.index(severity) >= order.index(min_sev):
                try:
                    channel(severity, subject, body)
                except Exception:  # noqa: BLE001 — alerting must never crash trading
                    self.log.exception("alert channel failed")


class HealthMonitor:
    """Heartbeat-based liveness checks for every subsystem.

    Each component calls `beat(name)` on every cycle; `check()` reports
    components whose heartbeat is stale. The orchestrator escalates stale
    critical components to the AlertManager and can trigger safe-mode.
    """

    def __init__(self, stale_after_s: float = 120.0):
        self.stale_after_s = stale_after_s
        self._beats: dict[str, float] = {}

    def beat(self, component: str) -> None:
        self._beats[component] = time.monotonic()

    def check(self) -> dict[str, bool]:
        now = time.monotonic()
        return {c: (now - t) <= self.stale_after_s for c, t in self._beats.items()}

    def unhealthy(self) -> list[str]:
        return [c for c, ok in self.check().items() if not ok]


class AuditLog:
    """Append-only JSONL audit trail: every decision, order, fill, risk
    override and configuration change gets a timestamped record."""

    def __init__(self, path: str | Path = "logs/audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, payload: Any) -> None:
        if is_dataclass(payload) and not isinstance(payload, type):
            payload = asdict(payload)
        entry = {"ts": time.time(), "type": event_type, "payload": payload}
        with self.path.open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
