"""Entry point: gather -> detect trends -> deliver -> persist seen-set."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from .config import Config
from .notify import deliver
from .sources import cutoff_date, gather
from .state import load_seen, save_seen
from .trends import build_digest, format_digest, to_records


def run(config: Config, post: bool, now_ms: int | None = None,
        json_path: str | None = None, update_seen: bool = True) -> str:
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    since = cutoff_date(now_ms, config.lookback_days)

    raw = gather(config.queries, since, per_page=config.per_page, token=config.github_token)
    seen = load_seen(config.seen_path)
    repos = build_digest(
        raw, now_ms,
        lookback_days=config.lookback_days,
        min_stars=config.min_stars,
        max_items=config.max_items,
        relevance_terms=config.relevance_terms,
        seen=seen,
    )

    date_str = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    text = format_digest(repos, date_str, config.label, now_ms)
    deliver(text, config.discord_webhook if post else "")

    if json_path:
        payload = {
            "label": config.label,
            "date": date_str,
            "generated_ms": now_ms,
            "repos": to_records(repos, now_ms),
        }
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"Wrote {json_path}")

    if update_seen and repos:
        seen.update(r.full_name for r in repos)
        save_seen(config.seen_path, seen)
        print(f"Updated seen-set ({len(seen)} repos) at {config.seen_path}")

    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GitHub GenAI trend detector")
    parser.add_argument("--post", action="store_true", help="post to the Discord webhook")
    parser.add_argument("--days", type=int, help="lookback window in days (repo age)")
    parser.add_argument("--min-stars", type=int, help="minimum stars to consider")
    parser.add_argument("--limit", type=int, help="max repos in the digest")
    parser.add_argument("--json", dest="json_path", help="also write the digest to this JSON file")
    parser.add_argument("--no-seen", action="store_true",
                        help="don't read/update the seen-set (useful for a one-off preview)")
    args = parser.parse_args(argv)

    config = Config.from_env()
    if args.days is not None:
        config.lookback_days = args.days
    if args.min_stars is not None:
        config.min_stars = args.min_stars
    if args.limit is not None:
        config.max_items = args.limit
    if args.no_seen:
        config.seen_path = ""

    run(config, post=args.post, json_path=args.json_path, update_seen=not args.no_seen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
