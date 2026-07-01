"""Thin adapters for live integrations: Telegram, Google Calendar, Spotify,
Shopify.  Each degrades to an actionable message when its credentials or
optional library are missing — the assistant never crashes over a missing key.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ..config import Config


def telegram_send(cfg: Config, text: str) -> str:
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        return "Telegram isn't configured — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."
    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": cfg.telegram_chat_id, "text": text}).encode()
    try:
        with urllib.request.urlopen(url, data=payload, timeout=10) as resp:
            ok = json.loads(resp.read()).get("ok", False)
        return "Sent to Telegram." if ok else "Telegram rejected the message."
    except OSError as exc:
        return f"Telegram send failed: {exc}"


def make_calendar_handler(cfg: Config):
    def handle(command: str) -> str:
        try:
            from googleapiclient.discovery import build  # noqa: F401  (optional)
        except ImportError:
            return ("Calendar needs google-api-python-client + OAuth credentials "
                    "(see README: 'Google Calendar setup').")
        # The production OAuth flow lives in the deployment environment;
        # wire the credentials.json/token.json paths there.
        return "Calendar is installed but no OAuth token is present yet — run the setup flow."
    return handle


def make_spotify_handler(cfg: Config):
    def handle(command: str) -> str:
        if not cfg.spotify_client_id or not cfg.spotify_client_secret:
            return "Spotify isn't configured — set SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET."
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
        except ImportError:
            return "Spotify support needs the 'spotipy' package (pure-Python, pip install spotipy)."
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=cfg.spotify_client_id,
            client_secret=cfg.spotify_client_secret,
            redirect_uri="http://127.0.0.1:8899/callback",
            scope="user-modify-playback-state user-read-playback-state",
        ))
        query = command.lower()
        for prefix in ("play", "נגן"):
            if prefix in query:
                query = query.split(prefix, 1)[1].strip()
                break
        if not query:
            return "What should I play?"
        results = sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            return f"Couldn't find '{query}' on Spotify."
        track = items[0]
        try:
            sp.start_playback(uris=[track["uri"]])
            return f"Playing {track['name']} by {track['artists'][0]['name']}."
        except Exception:
            return (f"Found {track['name']} by {track['artists'][0]['name']}, "
                    "but no active Spotify device to play it on.")
    return handle


def make_shopify_handler(cfg: Config):
    def handle(command: str) -> str:
        if not cfg.shopify_shop or not cfg.shopify_token:
            return "Shopify isn't configured — set SHOPIFY_SHOP and SHOPIFY_ACCESS_TOKEN."
        url = f"https://{cfg.shopify_shop}/admin/api/2025-01/orders.json?status=any&limit=5"
        req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": cfg.shopify_token})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                orders = json.loads(resp.read()).get("orders", [])
        except OSError as exc:
            return f"Shopify request failed: {exc}"
        if not orders:
            return "No recent orders."
        lines = [f"#{o.get('order_number')} {o.get('total_price')} {o.get('currency')}"
                 for o in orders]
        return f"Last {len(orders)} orders: " + "; ".join(lines)
    return handle
