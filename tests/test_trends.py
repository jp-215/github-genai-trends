from gh_trends.trends import (
    DAY_MS,
    Repo,
    build_digest,
    dedupe,
    format_digest,
    is_recent,
    is_relevant,
    parse_iso,
    to_records,
    velocity,
)

NOW = 1_780_000_000_000  # fixed "now" in ms


def mk(name, stars, age_days, desc="an llm agent tool", topics=("llm",)):
    return Repo(
        full_name=name,
        url=f"https://github.com/{name}",
        description=desc,
        stars=stars,
        language="Python",
        topics=topics,
        created_ms=NOW - int(age_days * DAY_MS),
        pushed_ms=NOW,
    )


def test_parse_iso_handles_z_suffix():
    assert parse_iso("2026-06-01T12:00:00Z") > 0
    assert parse_iso("") == 0
    assert parse_iso("not-a-date") == 0


def test_velocity_is_stars_per_day_floored_at_one_day():
    # 100 stars, 10 days old -> 10/day
    assert velocity(mk("a/b", 100, 10), NOW) == 10.0
    # brand-new repo: age floored at 1 day so it doesn't explode
    assert velocity(mk("a/c", 50, 0), NOW) == 50.0


def test_relevance_gate():
    assert is_relevant(mk("x/y", 10, 1, desc="RAG pipeline"), ["rag"])
    assert not is_relevant(
        mk("x/z", 10, 1, desc="a knitting pattern generator", topics=()), ["llm", "agent"]
    )


def test_is_recent_window():
    assert is_recent(mk("a/new", 10, 5), NOW, lookback_days=30)
    assert not is_recent(mk("a/old", 10, 400), NOW, lookback_days=30)


def test_dedupe_by_full_name():
    repos = [mk("a/b", 10, 1), mk("a/b", 99, 1), mk("c/d", 5, 1)]
    out = dedupe(repos)
    assert [r.full_name for r in out] == ["a/b", "c/d"]
    assert out[0].stars == 10  # keeps first seen


def test_build_digest_filters_rank_and_caps():
    repos = [
        mk("fast/rising", 300, 10),        # 30/day  -> top
        mk("slow/steady", 300, 300),       # created 300d ago -> filtered (not recent)
        mk("tiny/repo", 5, 1),             # below min_stars -> filtered
        mk("mid/tool", 200, 20),           # 10/day
        mk("off/topic", 500, 5, desc="static site theme", topics=()),  # not relevant
    ]
    out = build_digest(
        repos, NOW, lookback_days=30, min_stars=20, max_items=10,
        relevance_terms=["llm", "agent", "rag"],
    )
    names = [r.full_name for r in out]
    assert names == ["fast/rising", "mid/tool"]  # ranked by velocity, others filtered


def test_build_digest_drops_seen():
    repos = [mk("fast/rising", 300, 10), mk("mid/tool", 200, 20)]
    out = build_digest(
        repos, NOW, lookback_days=30, min_stars=20, max_items=10,
        relevance_terms=["llm"], seen={"fast/rising"},
    )
    assert [r.full_name for r in out] == ["mid/tool"]


def test_format_digest_empty_and_populated():
    assert "No new trending repos" in format_digest([], "2026-06-20", "GenAI", NOW)
    text = format_digest([mk("a/b", 100, 10)], "2026-06-20", "GenAI", NOW)
    assert "a/b" in text and "⭐ 100" in text and "<https://github.com/a/b>" in text


def test_to_records_shape():
    rec = to_records([mk("a/b", 100, 10)], NOW)[0]
    assert rec["full_name"] == "a/b"
    assert rec["velocity_per_day"] == 10.0
    assert rec["stars"] == 100
