# 🚀 github-genai-trends

A **trend detector for Generative-AI repositories on GitHub** — it finds new, fast-rising
repos (LLM tooling, agents, RAG, LLMOps, token-efficiency tricks) and posts the fresh ones
to Discord on a daily schedule. Built to help you spot the tools that make coding agents
**cheaper and more efficient** (think `toon`-style token savings) before they hit everyone's
feed.

Same architecture as the sibling `datacenter-alert` project, and **free by design**:

- **GitHub Search API** — no key required (the Action passes a built-in token just to raise
  the rate limit).
- **GitHub Actions** — runs on a cron, on the free tier. No servers.
- **Discord webhook** — no paid alerting service. No Amplify / Sprinklr / Sprout, no
  subscriptions, no LLM calls, **no money spent to send an alert.**

## How "trending" is detected

GitHub has no public star-history API, so trend is approximated by **star velocity**:

```
velocity = stars / max(days_since_created, 1)
```

The pipeline (all pure + unit-tested in `gh_trends/trends.py`):

1. **Query** a set of GenAI topics/keywords via the Search API, scoped to repos
   `created:>=` the last 30 days.
2. **Relevance-gate** — keep only repos whose name/description/topics mention GenAI terms
   (`llm`, `agent`, `rag`, `token`, `mcp`, …), so a broad query can't drag in noise.
3. **Recency + floor** — created within the window, and above a star floor (default 20).
4. **Drop already-seen** — a persisted seen-set (`state/seen.json`) means you're never
   alerted about the same repo twice. This is the "don't re-read the same thing" guarantee.
5. **Rank by velocity** (stars/day), tie-break on absolute stars, take the top N.

> It's a proxy, not a leaderboard — it surfaces *new and rising*, which is exactly where
> fresh tooling shows up. Established giants are intentionally out of scope.

## Layout

```
gh_trends/
├── config.py     # queries, relevance terms, thresholds — all env-overridable
├── sources.py    # GitHub Search API client (stdlib urllib; injectable for tests)
├── trends.py     # pure core: score, filter, dedupe, rank, format  (fully tested)
├── state.py      # persisted seen-set (load/save JSON)
├── notify.py     # Discord webhook delivery (chunked; injectable)
└── cli.py        # gather -> detect -> deliver -> persist
.github/workflows/
├── ci.yml        # ruff + pytest on 3.10–3.12
├── alert.yml     # daily cron -> post to Discord -> commit seen-set back
└── pages.yml     # publish the web dashboard
web/              # static dashboard (reads web/data.json)
tests/            # offline, injected fetch — zero network, zero API calls
```

## Run it locally

```bash
pip install -r requirements-dev.txt

# Preview the current trending repos (no Discord, ignores the seen-set):
python -m gh_trends.cli --no-seen --limit 10

# Post to Discord (needs the webhook env var):
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/…"
python -m gh_trends.cli --post

# Tune the window / thresholds:
python -m gh_trends.cli --days 14 --min-stars 50 --limit 8 --no-seen
```

## Deploy (one manual step: the webhook)

1. In your target Discord channel: **Edit Channel → Integrations → Webhooks → New Webhook →
   Copy URL**.
2. In the repo: **Settings → Secrets and variables → Actions → New secret** named
   `DISCORD_WEBHOOK_URL`, paste the URL.
3. That's it. `alert.yml` runs daily (and on-demand via the Actions tab's **Run workflow**),
   posts new trending repos, and commits the updated seen-set. Enable **Pages** (Settings →
   Pages → Source: GitHub Actions) for the live dashboard.

## Configuration (all optional, via env / Actions secrets)

| Var | Default | Meaning |
|-----|---------|---------|
| `DISCORD_WEBHOOK_URL` | — | where alerts post (unset = print only) |
| `GHT_QUERIES` | GenAI topic set | `;`-separated Search API query fragments |
| `GHT_RELEVANCE_TERMS` | llm/agent/rag/… | `;`-separated relevance gate |
| `GHT_LOOKBACK_DAYS` | 30 | max repo age to count as "new" |
| `GHT_MIN_STARS` | 20 | ignore repos below this |
| `GHT_MAX_ITEMS` | 10 | digest size cap |

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest          # fully offline — injected fetch, no API calls, no credit
```

CI runs ruff + pytest on Python 3.10–3.12.

---
*Built by the JayBot mesh. 🤖 No subscriptions were harmed.*
