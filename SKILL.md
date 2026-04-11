---
name: horizon-briefing
description: Fetch tech news from configured sources, score and filter with AI, generate daily briefing with deep analysis
---

# Horizon Briefing

Generate a daily tech briefing from configured data sources (GitHub, HackerNews, RSS, Reddit, Telegram). Fetches content via a Python script, then uses AI to score, filter, summarize, and deeply analyze top items. No external AI API key required.

## Trigger

User types `/horizon-briefing` or asks to "generate a briefing" / "run horizon briefing".

## Phase 1: Environment Check

1. Locate `config.json` in the current working directory. If not found, read `references/config-schema.md` from this skill directory and show the user the example. Ask them to create `config.json`. Stop until config exists.
2. Check Python deps: `python3 -c "import httpx; import feedparser; import bs4; print('OK')"`
3. If deps are missing, tell the user and ask if they want to run `scripts/install_deps.sh`. If the user declines, stop and explain manual install.

## Phase 2: Fetch Data

1. Run: `python3 <skill_dir>/scripts/fetch.py --config config.json`
2. Verify `fetched.json` was created, then read it.
3. Report item count and source count to the user.

## Phase 3: Score and Filter (Claude does this in-context)

- Evaluate each item 0–10 based on: Novelty, Impact, Technical depth, Community signal (score/upvotes/comments from metadata), Timeliness
- Sort descending, take top N from `config_snapshot.top_n` (default 10)
- Output a scoring summary to the user

## Phase 4: Generate Summary

- For each language in `config_snapshot.languages`, generate a summary following `assets/templates/summary.md`
- Language handling: `"en"` = English, `"zh"` = Chinese with Pangu spacing (space between CJK and ASCII), other codes = that language
- Write to: `{output_dir}/{YYYY-MM-DD}/summary-{lang}.md`

## Phase 5: Deep Analysis

- For each top-N item, generate a deep analysis following `assets/templates/article.md`
- Sections: Core Content, Technical Background, Impact & Significance, Community Discussion (only if comments exist in content)
- Write to: `{output_dir}/{YYYY-MM-DD}/articles/{N}-{title_slug}-{lang}.md`
- `title_slug`: lowercase, spaces to hyphens, remove non-alphanumeric, truncate to 50 chars

## Phase 6: Completion Report

- Total items fetched, items selected, files generated (list paths), any errors

## Notes

- The fetch script handles all network requests. Do not use WebFetch or curl for source data.
- All AI analysis is done by Claude in-context. No external AI API calls.
- If 0 items are fetched, skip phases 3–5.
- For 100+ items, score in batches of ~30 to avoid context overflow.
