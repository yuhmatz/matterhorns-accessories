"""ACHILLES core: wire the wake engine, skill router, brain, and vault together."""
from __future__ import annotations

import threading

from . import skills
from .brain import Brain
from .config import Config
from .memory import vault as vault_mod
from .memory.vault import Vault
from .skills import fitness, integrations, marantz, market
from .wake.engine import build_engine


class Assistant:
    def __init__(self, config: Config | None = None, text_mode: bool = False) -> None:
        self.config = config or Config.from_env()
        self.vault = Vault(self.config.memory)
        self.brain = Brain(self.config)
        self.router = skills.Router(fallback=self.brain.ask)
        self._register_skills()
        self.engine = build_engine(self.config.wake, self.config.data_dir, text_mode)

    def _register_skills(self) -> None:
        cfg = self.config
        self.router.register("market", market.handle)
        self.router.register("audio", marantz.make_handler(cfg.marantz_host, cfg.marantz_port))
        self.router.register("fitness",
                             fitness.make_handler(f"{cfg.data_dir}/workouts.json"))
        self.router.register("memory",
                             vault_mod.make_search_handler(cfg.memory.vault_path))
        self.router.register("calendar", integrations.make_calendar_handler(cfg))
        self.router.register("music", integrations.make_spotify_handler(cfg))
        self.router.register("shop", integrations.make_shopify_handler(cfg))

    def handle(self, command: str) -> str:
        response = self.router.dispatch(command)
        self.vault.log_exchange(command, response)
        return response

    def run(self, with_worldview: bool = False) -> None:
        if with_worldview:
            from .worldview.server import serve

            threading.Thread(target=serve, args=(self.config.worldview,),
                             daemon=True, name="worldview").start()
        brain_state = "online" if self.brain.online else "offline (no API key)"
        print(f"[achilles] ready — brain {brain_state}")
        for command in self.engine.listen():
            print(f"[you] {command}")
            response = self.handle(command)
            print(f"[achilles] {response}")
