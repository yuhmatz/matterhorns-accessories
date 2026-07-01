"""Entry point: ``python -m achilles [--text] [--worldview] [--worldview-only]``."""
from __future__ import annotations

import argparse

from .assistant import Assistant
from .config import Config


def main() -> None:
    parser = argparse.ArgumentParser(prog="achilles",
                                     description="ACHILLES voice assistant")
    parser.add_argument("--text", action="store_true",
                        help="keyboard mode (no microphone/Vosk needed)")
    parser.add_argument("--worldview", action="store_true",
                        help="also serve the WorldView dashboard")
    parser.add_argument("--worldview-only", action="store_true",
                        help="serve only the WorldView dashboard")
    args = parser.parse_args()

    config = Config.from_env()
    if args.worldview_only:
        from .worldview.server import serve

        serve(config.worldview)
        return
    Assistant(config, text_mode=args.text).run(with_worldview=args.worldview)


if __name__ == "__main__":
    main()
