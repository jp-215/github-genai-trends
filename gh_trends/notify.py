"""Deliver the digest: always print, optionally POST to a Discord webhook (free)."""

from __future__ import annotations

import json
import urllib.request

DISCORD_LIMIT = 1900  # leave headroom under Discord's 2000-char message cap


def chunk(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """Split text into <=limit chunks on line boundaries where possible."""
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit and current:
            chunks.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def post_discord(webhook: str, text: str, post=None) -> bool:
    """POST text (chunked) to a Discord webhook. ``post`` is injectable for tests."""
    sender = post or _http_post
    ok = True
    for part in chunk(text):
        ok = sender(webhook, {"content": part}) and ok
    return ok


def _http_post(url: str, payload: dict, timeout: float = 15.0) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except Exception as exc:
        print(f"WARN: Discord post failed: {exc}")
        return False


def deliver(text: str, webhook: str) -> None:
    print(text)
    if webhook:
        ok = post_discord(webhook, text)
        print("Posted to Discord." if ok else "Discord post did not fully succeed.")
    else:
        print("(No DISCORD_WEBHOOK_URL set — printed only.)")
