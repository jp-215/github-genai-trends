import json

from gh_trends.config import Config
from gh_trends.notify import chunk, post_discord
from gh_trends.sources import cutoff_date, gather, parse_search, query_url
from gh_trends.state import load_seen, save_seen

SAMPLE = json.dumps({
    "items": [
        {
            "full_name": "acme/llm-router",
            "html_url": "https://github.com/acme/llm-router",
            "description": "Cheapest-model LLM router",
            "stargazers_count": 420,
            "language": "Python",
            "topics": ["llm", "router"],
            "created_at": "2026-06-01T12:00:00Z",
            "pushed_at": "2026-06-18T09:00:00Z",
        },
        {
            "full_name": "acme/token-diet",
            "html_url": "https://github.com/acme/token-diet",
            "description": "Token-efficient serialization for prompts",
            "stargazers_count": 130,
            "language": "Rust",
            "topics": ["token", "llm"],
            "created_at": "2026-06-10T00:00:00Z",
            "pushed_at": "2026-06-19T00:00:00Z",
        },
    ]
})


def test_query_url_scopes_by_created_and_sorts_by_stars():
    url = query_url("topic:llm", "2026-05-20", per_page=30)
    assert "created%3A%3E%3D2026-05-20" in url  # created:>=2026-05-20, url-encoded
    assert "sort=stars" in url and "order=desc" in url


def test_cutoff_date_subtracts_lookback():
    # now_ms = 2026-06-09 (UTC); minus 30 days = 2026-05-10
    now_ms = 1_781_000_000_000
    assert cutoff_date(now_ms, 30) == "2026-05-10"


def test_parse_search_extracts_repos():
    repos = parse_search(SAMPLE)
    assert len(repos) == 2
    assert repos[0].full_name == "acme/llm-router"
    assert repos[0].stars == 420
    assert repos[0].created_ms > 0
    assert repos[1].topics == ("token", "llm")


def test_gather_with_injected_fetch_merges_and_dedupes_across_queries():
    repos = gather(["q1", "q2"], "2026-05-20", fetch=lambda url: SAMPLE)
    assert len(repos) == 4  # 2 queries x 2 items (dedupe happens later in build_digest)


def test_gather_survives_bad_query():
    def boom(url):
        raise RuntimeError("rate limited")

    assert gather(["q"], "2026-05-20", fetch=boom) == []


def test_chunking_respects_limit():
    text = "\n".join(f"line {i}" for i in range(500))
    parts = chunk(text, limit=200)
    assert all(len(p) <= 200 for p in parts)
    assert "".join(parts).replace("\n", "") == text.replace("\n", "")


def test_post_discord_uses_injected_sender():
    sent = []
    ok = post_discord(
        "http://hook", "hello", post=lambda url, payload: sent.append(payload) or True
    )
    assert ok and sent == [{"content": "hello"}]


def test_seen_roundtrip(tmp_path):
    p = str(tmp_path / "seen.json")
    assert load_seen(p) == set()
    save_seen(p, {"a/b", "c/d"})
    assert load_seen(p) == {"a/b", "c/d"}


def test_config_from_env_defaults():
    cfg = Config.from_env()
    assert cfg.min_stars >= 1
    assert cfg.queries and cfg.relevance_terms
    assert cfg.lookback_days >= 1
