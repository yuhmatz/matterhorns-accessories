"""Central configuration for ACHILLES.

Every secret and every tunable lives in the environment (optionally loaded
from a local ``.env`` file that is git-ignored).  Nothing in this repository
ever contains a real key — this is the fix for the "exposed API keys" blocker:
keys are read here, used server-side, and never served to a client.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_dotenv(path: str | os.PathLike = ".env") -> dict[str, str]:
    """Tiny dependency-free .env loader.

    Lines are ``KEY=VALUE``; ``#`` comments and blank lines are ignored.
    Existing environment variables are never overwritten.
    """
    loaded: dict[str, str] = {}
    p = Path(path)
    if not p.is_file():
        return loaded
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass
class WakeConfig:
    """Hardened wake-word settings (v4.73 semantics: final-only + noise rejection)."""

    wake_word: str = "achilles"
    sample_rate: int = 16000
    # Only Vosk *final* results are considered; partials caused the false-fire storm.
    min_confidence: float = 0.85
    # RMS gate: frames quieter than this are treated as noise and never decoded.
    rms_gate: float = 0.012
    # Refractory period after a trigger, seconds.
    cooldown_s: float = 3.0
    # After this many consecutive rejected candidates, back off (media playing nearby).
    noise_backoff_after: int = 4
    noise_backoff_s: float = 10.0
    # Speaker verification (the durable fix): cosine-similarity threshold.
    speaker_verify_enabled: bool = True
    speaker_threshold: float = 0.80
    vosk_model_path: str = ""

    @classmethod
    def from_env(cls) -> "WakeConfig":
        return cls(
            wake_word=_env("ACHILLES_WAKE_WORD", "achilles"),
            sample_rate=_env_int("ACHILLES_SAMPLE_RATE", 16000),
            min_confidence=_env_float("ACHILLES_WAKE_MIN_CONF", 0.85),
            rms_gate=_env_float("ACHILLES_WAKE_RMS_GATE", 0.012),
            cooldown_s=_env_float("ACHILLES_WAKE_COOLDOWN_S", 3.0),
            noise_backoff_after=_env_int("ACHILLES_WAKE_NOISE_BACKOFF_AFTER", 4),
            noise_backoff_s=_env_float("ACHILLES_WAKE_NOISE_BACKOFF_S", 10.0),
            speaker_verify_enabled=_env("ACHILLES_SPEAKER_VERIFY", "1") not in ("0", "false", "no"),
            speaker_threshold=_env_float("ACHILLES_SPEAKER_THRESHOLD", 0.80),
            vosk_model_path=_env("ACHILLES_VOSK_MODEL", ""),
        )


@dataclass
class WorldViewConfig:
    """WorldView geospatial dashboard.

    ``host`` defaults to ``0.0.0.0`` and the frontend uses only relative URLs,
    so the map is reachable from a phone on the LAN (fixes the ``localhost``
    hardcode blocker).  The bounding box is configurable; set
    ``ACHILLES_WV_BBOX=global`` to remove the Israel cap.
    """

    host: str = "0.0.0.0"
    port: int = 8590
    # "global" or "south,west,north,east"
    bbox: str = "29.3,33.8,33.4,36.0"  # Israel + margins, the current default
    center: str = "31.5,34.9"
    zoom: float = 7.0
    openweathermap_key: str = ""  # used server-side only, never sent to clients
    aircraft_radius_nm: int = 250

    @classmethod
    def from_env(cls) -> "WorldViewConfig":
        return cls(
            host=_env("ACHILLES_WV_HOST", "0.0.0.0"),
            port=_env_int("ACHILLES_WV_PORT", 8590),
            bbox=_env("ACHILLES_WV_BBOX", "29.3,33.8,33.4,36.0"),
            center=_env("ACHILLES_WV_CENTER", "31.5,34.9"),
            zoom=_env_float("ACHILLES_WV_ZOOM", 7.0),
            openweathermap_key=_env("OPENWEATHERMAP_API_KEY", ""),
            aircraft_radius_nm=_env_int("ACHILLES_WV_AIRCRAFT_RADIUS_NM", 250),
        )

    def bbox_tuple(self) -> tuple[float, float, float, float] | None:
        if self.bbox.strip().lower() == "global":
            return None
        parts = [float(x) for x in self.bbox.split(",")]
        if len(parts) != 4:
            raise ValueError(f"bbox must be 'south,west,north,east' or 'global', got {self.bbox!r}")
        return tuple(parts)  # type: ignore[return-value]


@dataclass
class MemoryConfig:
    """Local-first data layer: Obsidian vault + tiered storage (SSD text / HDD audio)."""

    vault_path: str = "data/vault"
    audio_archive_path: str = "data/audio_archive"

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        return cls(
            vault_path=_env("ACHILLES_VAULT_PATH", "data/vault"),
            audio_archive_path=_env("ACHILLES_AUDIO_ARCHIVE", "data/audio_archive"),
        )


@dataclass
class Config:
    wake: WakeConfig = field(default_factory=WakeConfig)
    worldview: WorldViewConfig = field(default_factory=WorldViewConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    # Integrations — all optional, all env-driven, all degrade gracefully.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    shopify_shop: str = ""
    shopify_token: str = ""
    marantz_host: str = ""
    marantz_port: int = 23
    data_dir: str = "data"

    @classmethod
    def from_env(cls, dotenv: str | None = ".env") -> "Config":
        if dotenv:
            load_dotenv(dotenv)
        return cls(
            wake=WakeConfig.from_env(),
            worldview=WorldViewConfig.from_env(),
            memory=MemoryConfig.from_env(),
            anthropic_api_key=_env("ANTHROPIC_API_KEY", ""),
            anthropic_model=_env("ACHILLES_CLAUDE_MODEL", "claude-opus-4-8"),
            telegram_bot_token=_env("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=_env("TELEGRAM_CHAT_ID", ""),
            spotify_client_id=_env("SPOTIFY_CLIENT_ID", ""),
            spotify_client_secret=_env("SPOTIFY_CLIENT_SECRET", ""),
            shopify_shop=_env("SHOPIFY_SHOP", ""),
            shopify_token=_env("SHOPIFY_ACCESS_TOKEN", ""),
            marantz_host=_env("MARANTZ_HOST", ""),
            marantz_port=_env_int("MARANTZ_PORT", 23),
            data_dir=_env("ACHILLES_DATA_DIR", "data"),
        )
