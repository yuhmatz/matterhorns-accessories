"""Home-audio control: Marantz NR1605 over LAN.

Denon/Marantz AVRs speak a plain-text telnet protocol on port 23 — commands
like ``PWON``, ``MV45``, ``SIGAME`` terminated with ``\r``.  Command
construction is pure (tested); only ``send`` opens a socket.
"""
from __future__ import annotations

import socket

VALID_INPUTS = {
    "game": "GAME", "tv": "TV", "bluetooth": "BT", "aux": "AUX1",
    "cd": "CD", "tuner": "TUNER", "usb": "USB/IPOD", "net": "NET",
    "mplay": "MPLAY", "bd": "BD", "dvd": "DVD",
}


def build_command(action: str, value: str | int | None = None) -> str:
    """Build a Denon/Marantz protocol command string (without the CR)."""
    action = action.lower()
    if action == "power_on":
        return "PWON"
    if action == "power_off":
        return "PWSTANDBY"
    if action == "volume_up":
        return "MVUP"
    if action == "volume_down":
        return "MVDOWN"
    if action == "set_volume":
        vol = int(value)  # type: ignore[arg-type]
        if not 0 <= vol <= 98:
            raise ValueError(f"volume must be 0-98, got {vol}")
        return f"MV{vol:02d}"
    if action == "mute_on":
        return "MUON"
    if action == "mute_off":
        return "MUOFF"
    if action == "set_input":
        src = VALID_INPUTS.get(str(value).lower())
        if not src:
            raise ValueError(f"unknown input {value!r}; one of {sorted(VALID_INPUTS)}")
        return f"SI{src}"
    if action == "status":
        return "PW?"
    raise ValueError(f"unknown action {action!r}")


class Marantz:
    def __init__(self, host: str, port: int = 23, timeout: float = 3.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, action: str, value: str | int | None = None) -> str:
        cmd = build_command(action, value)
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall((cmd + "\r").encode("ascii"))
            sock.settimeout(self.timeout)
            try:
                reply = sock.recv(256).decode("ascii", "replace").strip()
            except socket.timeout:
                reply = ""
        return reply or cmd


def parse_voice_command(command: str) -> tuple[str, str | int | None] | None:
    """Map a spoken command to a (action, value) pair, or None."""
    c = command.lower()
    if "off" in c or "standby" in c or "כבה" in c:
        return ("power_off", None)
    if "on" in c or "הדלק" in c:
        return ("power_on", None)
    if "up" in c or "הגבר" in c:
        return ("volume_up", None)
    if "down" in c or "הנמך" in c:
        return ("volume_down", None)
    for word in c.split():
        if word.isdigit():
            return ("set_volume", int(word))
    for name in VALID_INPUTS:
        if name in c:
            return ("set_input", name)
    return None


def make_handler(host: str, port: int):
    def handle(command: str) -> str:
        if not host:
            return "Receiver control isn't configured — set MARANTZ_HOST in .env."
        parsed = parse_voice_command(command)
        if not parsed:
            return "Say e.g. 'receiver on', 'volume up', 'volume 45' or 'input game'."
        try:
            reply = Marantz(host, port).send(*parsed)
            return f"Receiver: {reply}"
        except OSError as exc:
            return f"Couldn't reach the receiver at {host}:{port} — {exc}"
    return handle
