"""Fetch repositories from the GitHub Search API (no key required; a token just raises
the rate limit). JSON parsing uses only the standard library, and the HTTP fetch is
injectable so the pipeline is tested offline with canned JSON.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .trends import Repo, parse_iso

SEARCH_API = "https://api.github.com/search/repositories"
USER_AGENT = "github-genai-trends/0.1 (+https://github.com)"


def cutoff_date(now_ms: int, lookback_days: int) -> str:
    """The `created:>=` date (YYYY-MM-DD) for the trending window."""
    dt = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc) - timedelta(days=lookback_days)
    return dt.strftime("%Y-%m-%d")


def query_url(term: str, since: str, per_page: int = 30) -> str:
    """Build a search URL: the term, scoped to repos created since `since`, top stars first."""
    q = f"{term} created:>={since}"
    params = urllib.parse.urlencode(
        {"q": q, "sort": "stars", "order": "desc", "per_page": per_page}
    )
    return f"{SEARCH_API}?{params}"


def parse_search(json_text: str) -> list[Repo]:
    """Parse a GitHub search-repositories response into Repo objects."""
    data = json.loads(json_text)
    repos: list[Repo] = []
    for it in data.get("items", []):
        repos.append(
            Repo(
                full_name=it.get("full_name", ""),
                url=it.get("html_url", ""),
                description=(it.get("description") or "").strip(),
                stars=int(it.get("stargazers_count", 0)),
                language=it.get("language") or "",
                topics=tuple(it.get("topics", []) or ()),
                created_ms=parse_iso(it.get("created_at", "")),
                pushed_ms=parse_iso(it.get("pushed_at", "")),
            )
        )
    return repos


def _http_get(url: str, token: str = "", timeout: float = 20.0) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted host)
        return resp.read().decode("utf-8", errors="replace")


def gather(queries: list[str], since: str, per_page: int = 30, token: str = "",
           fetch=None) -> list[Repo]:
    """Fetch and merge repos across all queries. ``fetch`` is injectable for tests."""
    getter = fetch or (lambda url: _http_get(url, token=token))
    repos: list[Repo] = []
    for term in queries:
        try:
            repos.extend(parse_search(getter(query_url(term, since, per_page))))
        except Exception as exc:  # one bad query shouldn't kill the run
            print(f"WARN: query failed ({term!r}): {exc}")
    return repos
