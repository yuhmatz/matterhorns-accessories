"""Obsidian vault logging + tiered storage.

Every exchange is appended to a daily markdown note inside the vault (SSD
tier).  Audio blobs, when kept, go to the archive path (HDD tier); if the
archive drive isn't mounted, audio falls back to the vault side rather than
being dropped.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..config import MemoryConfig


class Vault:
    def __init__(self, config: MemoryConfig) -> None:
        self.root = Path(config.vault_path)
        self.audio_root = Path(config.audio_archive_path)

    def _daily_note(self, when: datetime) -> Path:
        folder = self.root / "Achilles" / f"{when:%Y}" / f"{when:%m}"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{when:%Y-%m-%d}.md"

    def log_exchange(self, command: str, response: str,
                     when: datetime | None = None) -> Path:
        when = when or datetime.now()
        note = self._daily_note(when)
        if not note.exists():
            note.write_text(f"# Achilles — {when:%Y-%m-%d}\n", encoding="utf-8")
        with note.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {when:%H:%M:%S}\n**You:** {command}\n\n**Achilles:** {response}\n")
        return note

    def archive_audio(self, pcm: bytes, when: datetime | None = None) -> Path:
        """Store raw audio on the HDD tier; fall back to the vault tier."""
        when = when or datetime.now()
        name = f"{when:%Y%m%d-%H%M%S}.pcm"
        try:
            self.audio_root.mkdir(parents=True, exist_ok=True)
            target = self.audio_root / name
            target.write_bytes(pcm)
            return target
        except OSError:
            fallback = self.root / "Achilles" / "_audio_overflow"
            fallback.mkdir(parents=True, exist_ok=True)
            target = fallback / name
            target.write_bytes(pcm)
            return target


def search(vault_root: str | Path, query: str, limit: int = 5) -> list[tuple[Path, str]]:
    """Memory search over the vault: rank .md files by term hits, return snippets."""
    root = Path(vault_root)
    terms = [t for t in query.lower().split() if len(t) > 1]
    if not terms or not root.is_dir():
        return []
    scored: list[tuple[int, Path, str]] = []
    for md in root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lowered = text.lower()
        score = sum(lowered.count(t) for t in terms)
        if score <= 0:
            continue
        # snippet around the first hit
        first = min((lowered.find(t) for t in terms if t in lowered), default=0)
        start = max(0, first - 80)
        snippet = " ".join(text[start:first + 160].split())
        scored.append((score, md, snippet))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [(path, snippet) for _score, path, snippet in scored[:limit]]


def make_search_handler(vault_root: str | Path):
    def handle(command: str) -> str:
        # strip routing words so the query is just the subject
        query = command
        for word in ("search my notes", "remember", "notes", "חפש בפתקים", "פתקים", "זוכר"):
            query = query.replace(word, " ")
        results = search(vault_root, query.strip() or command)
        if not results:
            return "Nothing matching that in the vault."
        lines = [f"{path.name}: …{snippet}…" for path, snippet in results]
        return "Found in your notes — " + " | ".join(lines)
    return handle
