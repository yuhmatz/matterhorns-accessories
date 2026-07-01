# ACHILLES — עוזר בינה מלאכותית מקומי

A local-first, voice-activated personal AI assistant. Offline wake word,
hardened against the false-trigger storm, with speaker verification, a
WorldView geospatial dashboard reachable from your phone, and skills for
market briefings, home audio, combat fitness, and your Obsidian vault.

Runs on Python 3.11+ — **including 3.14**: the core is stdlib-only and every
optional dependency ships version-independent wheels (the constraint that
blocked openWakeWord/onnxruntime doesn't apply here).

## Quick start

```bash
cd achilles
cp .env.example .env          # fill in what you use; rotate any exposed keys first
python -m achilles --text     # keyboard mode — works with zero dependencies
```

Voice mode (needs a mic):

```bash
pip install vosk sounddevice
python -m achilles --worldview   # wake word + WorldView dashboard
```

WorldView only:

```bash
python -m achilles --worldview-only
# open http://<machine-LAN-IP>:8590/ from any device on the network
```

Claude brain (handles anything no local skill claims):

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...   # or put it in .env
```

## How this addresses the known blockers

| Blocker | Fix in this build |
|---|---|
| Wake-word false-fire storm | `wake/decision.py` — final-only decoding, RMS gate, confidence floor, cooldown, and noise backoff, all unit-tested (`tests/test_wake_decision.py`) |
| Durable fix: speaker verification | `wake/speaker.py` — enroll the owner's voice once; non-owner audio (TV/music) is rejected at the gate. Pure Python, upgradeable to a neural model when the GPU arrives |
| FLIGHTS tab unreachable from phone | WorldView binds `0.0.0.0` and the frontend uses **relative URLs only** — no `localhost` anywhere (tested: `tests/test_worldview.py::test_index_served`) |
| Map capped to Israel | `ACHILLES_WV_BBOX` env var; set `global` to remove the cap |
| Exposed API keys | No key in the repo; keys load from `.env` and stay server-side (cloud tiles are proxied through `/tiles/clouds/...` so the OWM key never reaches a browser — tested) |
| Python 3.14 wheel constraint | Core = stdlib only; DSP (FFT/MFCC) implemented in pure Python; optional deps all ship `py3-none` wheels |
| Source-of-truth risk | Everything lives in this repo; deploy from git, not from ad-hoc copies |

## Layout

```
achilles/
  __main__.py            python -m achilles [--text] [--worldview] [--worldview-only]
  config.py              all settings + secrets from env/.env
  assistant.py           core loop: engine → router → skill/brain → vault
  brain.py               optional Claude API brain (claude-opus-4-8, adaptive thinking)
  audio/dsp.py           pure-Python FFT, MFCC, RMS, cosine similarity
  wake/decision.py       hardened wake policy (pure state machine)
  wake/speaker.py        owner-voice verification (enroll/verify)
  wake/engine.py         VoskWakeEngine (mic) / TextWakeEngine (keyboard)
  skills/                market (RSI/MACD), marantz (NR1605 LAN), fitness coach,
                         integrations (Telegram/Calendar/Spotify/Shopify), router
  memory/vault.py        Obsidian daily notes + tiered storage + memory search
  worldview/             stdlib HTTP server + MapLibre frontend
                         (aircraft, rain radar, clouds, NV/FLIR/CRT filters)
tests/                   57 unit tests — python -m unittest discover -s tests
```

## Speaker enrollment

```python
from achilles.wake.speaker import SpeakerVerifier
from achilles.audio.dsp import pcm16_to_float

v = SpeakerVerifier("data/speaker_profile.json")
# record 3-5 short clips of yourself saying "Achilles" (16 kHz mono PCM16)
v.enroll([pcm16_to_float(open(p, "rb").read()) for p in clips])
```

Until a profile exists the gate fails open, so the assistant works out of the
box; once enrolled, only your voice wakes it.

## Roadmap hooks already in place

- **Satellites / vessels / wider coverage** — add layers next to the aircraft
  source in `worldview/static/index.html`; the server relay pattern
  (`/api/...`) is ready for CelesTrak and AIS feeds.
- **Shopify voice ops** — `skills/integrations.py::make_shopify_handler`
  (orders today; low-stock alerts and drafted descriptions next).
- **Memory search** — `memory/vault.py::search` works today over the vault;
  swap in embeddings when the RTX 3090 lands.
- **Biometric wristband** — feed readings into the vault via
  `Vault.log_exchange` or a new skill; the router makes new intents one-line
  registrations.
