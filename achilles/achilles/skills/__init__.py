"""Skill registry and intent router for ACHILLES.

Routing is deliberately boring: keyword matching (Hebrew + English) resolves
an intent to a skill; anything unresolved goes to the Claude brain when an
API key is configured, otherwise to a polite fallback.
"""
from __future__ import annotations

from typing import Callable

Handler = Callable[[str], str]

# intent -> keywords (lowercase, substring match on the command)
_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "market": ("market", "s&p", "sp500", "stock", "בורסה", "שוק", "מניות"),
    "audio": ("volume", "receiver", "marantz", "amp", "ווליום", "רסיבר", "מגבר"),
    "fitness": ("workout", "training", "pushup", "situp", "run", "weight",
                "weekly summary", "אימון", "כושר", "ריצה", "שכיבות", "משקל", "סיכום שבועי"),
    "memory": ("remember", "search my notes", "notes", "זוכר", "חפש בפתקים", "פתקים"),
    "calendar": ("calendar", "meeting", "schedule", "יומן", "פגישה", "לוז"),
    "music": ("play", "spotify", "song", "נגן", "שיר", "ספוטיפיי"),
    "shop": ("orders", "shopify", "stock alert", "הזמנות", "מלאי", "חנות"),
}


def resolve_intent(command: str) -> str | None:
    lowered = command.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return intent
    return None


class Router:
    def __init__(self, fallback: Handler) -> None:
        self._handlers: dict[str, Handler] = {}
        self._fallback = fallback

    def register(self, intent: str, handler: Handler) -> None:
        self._handlers[intent] = handler

    def dispatch(self, command: str) -> str:
        intent = resolve_intent(command)
        handler = self._handlers.get(intent) if intent else None
        if handler is None:
            return self._fallback(command)
        return handler(command)
