"""Configuration for the GitHub GenAI trend detector, from defaults + environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# GitHub Search API query fragments. Each is one search; a `created:>=<date>` clause is
# appended at run time from `lookback_days`. Focused on Generative-AI + the "make coding
# agents cheaper / more efficient" space you care about (token efficiency, agent tooling).
DEFAULT_QUERIES = [
    "topic:llm",
    "topic:llm-agent",
    "topic:ai-agents",
    "topic:rag",
    "topic:generative-ai",
    "topic:llmops",
    "llm token efficient",
    "coding agent context",
]

# Relevance gate: a repo is kept only if one of these appears in its name, description,
# or topics. Keeps generic repos that slip through a broad query out of the digest.
DEFAULT_RELEVANCE_TERMS = [
    "llm", "gpt", "claude", "gemini", "agent", "rag", "prompt", "token",
    "inference", "embedding", "retrieval", "context", "generative", "genai",
    "fine-tune", "finetune", "mcp", "llmops", "vector", "transformer", "diffusion",
]


@dataclass
class Config:
    queries: list[str] = field(default_factory=lambda: list(DEFAULT_QUERIES))
    relevance_terms: list[str] = field(default_factory=lambda: list(DEFAULT_RELEVANCE_TERMS))
    label: str = "GenAI on GitHub"
    lookback_days: int = 30       # only repos CREATED within this window count as "trending"
    min_stars: int = 20           # ignore noise below this many stars
    max_items: int = 10           # cap the digest size
    per_page: int = 30            # results fetched per query
    discord_webhook: str = ""
    github_token: str = ""        # optional; raises the API rate limit (Actions provides one)
    seen_path: str = "state/seen.json"

    @classmethod
    def from_env(cls) -> Config:
        queries = os.getenv("GHT_QUERIES", "")
        terms = os.getenv("GHT_RELEVANCE_TERMS", "")
        return cls(
            queries=[q.strip() for q in queries.split(";") if q.strip()] or list(DEFAULT_QUERIES),
            relevance_terms=[t.strip().lower() for t in terms.split(";") if t.strip()]
            or list(DEFAULT_RELEVANCE_TERMS),
            label=os.getenv("GHT_LABEL", cls.label),
            lookback_days=int(os.getenv("GHT_LOOKBACK_DAYS", cls.lookback_days)),
            min_stars=int(os.getenv("GHT_MIN_STARS", cls.min_stars)),
            max_items=int(os.getenv("GHT_MAX_ITEMS", cls.max_items)),
            per_page=int(os.getenv("GHT_PER_PAGE", cls.per_page)),
            discord_webhook=os.getenv("DISCORD_WEBHOOK_URL", ""),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            seen_path=os.getenv("GHT_SEEN_PATH", cls.seen_path),
        )
