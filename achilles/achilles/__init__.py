"""ACHILLES — a local-first, voice-activated personal AI assistant.

Design constraints (from the project brief):
- Python 3.11+ (including 3.14: only pure-Python / version-independent deps).
- Offline wake word via Vosk; no cloud STT required.
- No hardcoded API keys anywhere — everything comes from the environment.
- WorldView binds to a configurable host (no ``localhost`` hardcodes) so the
  dashboard is reachable from a phone on the LAN.
"""

__version__ = "5.0.0"
