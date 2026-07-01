"""The Claude-powered brain: handles anything no local skill claims.

Optional by design — with no ANTHROPIC_API_KEY (or no ``anthropic`` package)
the assistant still runs fully offline; unknown commands just get a local
fallback message.
"""
from __future__ import annotations

from .config import Config

SYSTEM_PROMPT = (
    "You are Achilles, a concise voice assistant running on the owner's own "
    "hardware. Answers are spoken aloud, so reply in 1-3 short sentences, no "
    "markdown. Answer in the language the user spoke (Hebrew or English)."
)


class Brain:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._client = None
        if config.anthropic_api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            except ImportError:
                self._client = None

    @property
    def online(self) -> bool:
        return self._client is not None

    def ask(self, command: str) -> str:
        if self._client is None:
            return ("I don't have an answer for that locally, and no Claude API "
                    "key is configured (set ANTHROPIC_API_KEY to enable the brain).")
        try:
            response = self._client.messages.create(
                model=self.config.anthropic_model,
                max_tokens=1024,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": command}],
            )
        except Exception as exc:
            return f"The Claude brain is unreachable right now: {exc}"
        if response.stop_reason == "refusal":
            return "I can't help with that one."
        return "".join(block.text for block in response.content
                       if getattr(block, "type", "") == "text").strip() or "(no answer)"
