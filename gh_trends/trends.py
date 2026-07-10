"""Pure trend logic: parse, score, filter, dedupe, rank, and format repos.

No network or third-party deps, so every function here is unit-tested. "Trending" is
approximated by star *velocity* (stars per day since creation) on recently-created repos,
because GitHub exposes no star-history API. It's a proxy, but a good one for surfacing
new, fast-rising tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

DAY_MS = 86_400_000


@dataclass(frozen=True)
class Repo:
    full_name: str
    url: str
    description: str
    stars: int
    language: str
    topics: tuple[str, ...]
    created_ms: int
    pushed_ms: int


def parse_iso(value: str) -> int:
    """Parse a GitHub ISO-8601 timestamp (e.g. '2026-06-01T12:00:00Z') into epoch ms."""
    if not value:
        return 0
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def age_days(repo: Repo, now_ms: int) -> float:
    """Repo age in days, floored at 1 so brand-new repos don't divide toward infinity."""
    return max((now_ms - repo.created_ms) / DAY_MS, 1.0)


def velocity(repo: Repo, now_ms: int) -> float:
    """Stars per day since creation — the trend score."""
    return repo.stars / age_days(repo, now_ms)


def is_relevant(repo: Repo, terms: list[str]) -> bool:
    """True if any relevance term appears in the name, description, or topics."""
    hay = f"{repo.full_name} {repo.description} {' '.join(repo.topics)}".lower()
    return any(term in hay for term in terms)


def is_recent(repo: Repo, now_ms: int, lookback_days: int) -> bool:
    """Created within the lookback window — i.e. genuinely new, not just active."""
    cutoff = now_ms - lookback_days * DAY_MS
    return repo.created_ms >= cutoff


def dedupe(repos: list[Repo]) -> list[Repo]:
    """Drop duplicate repos by full_name (the same repo matches multiple queries)."""
    seen: set[str] = set()
    out: list[Repo] = []
    for r in repos:
        if r.full_name not in seen:
            seen.add(r.full_name)
            out.append(r)
    return out


def build_digest(repos: list[Repo], now_ms: int, *, lookback_days: int, min_stars: int,
                 max_items: int, relevance_terms: list[str],
                 seen: set[str] | None = None) -> list[Repo]:
    """Full pipeline: relevance -> recency -> min-stars -> drop-seen -> dedupe -> rank -> top N."""
    seen = seen or set()
    kept = [
        r for r in repos
        if is_relevant(r, relevance_terms)
        and is_recent(r, now_ms, lookback_days)
        and r.stars >= min_stars
        and r.full_name not in seen
    ]
    ranked = sorted(dedupe(kept), key=lambda r: (velocity(r, now_ms), r.stars), reverse=True)
    return ranked[:max_items]


def format_digest(repos: list[Repo], date_str: str, label: str, now_ms: int) -> str:
    """Render a concise Discord message. Links wrapped in <> to suppress embeds."""
    header = f"🚀 GitHub Trend Detector — {label} — {date_str}"
    if not repos:
        return f"{header}\nNo new trending repos in the window."
    lines = [header]
    for r in repos:
        vel = velocity(r, now_ms)
        lang = f" · {r.language}" if r.language else ""
        desc = f"\n  {r.description}" if r.description else ""
        lines.append(
            f"⭐ {r.stars} (+{vel:.1f}/day){lang} — {r.full_name}{desc}\n  <{r.url}>"
        )
    return "\n".join(lines)


def to_records(repos: list[Repo], now_ms: int) -> list[dict]:
    """Serialize repos to plain dicts (for the web dashboard's data.json)."""
    return [
        {
            "full_name": r.full_name,
            "url": r.url,
            "description": r.description,
            "stars": r.stars,
            "language": r.language,
            "topics": list(r.topics),
            "velocity_per_day": round(velocity(r, now_ms), 2),
            "created_ms": r.created_ms,
            "pushed_ms": r.pushed_ms,
        }
        for r in repos
    ]
