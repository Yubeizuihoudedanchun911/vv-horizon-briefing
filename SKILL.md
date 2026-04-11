---
name: horizon-briefing
description: Fetch tech news from configured sources, score and filter with AI, generate daily briefing with deep analysis
---

# Horizon Briefing

Generate a daily tech briefing from configured data sources (GitHub, HackerNews, RSS, Reddit, Telegram). Fetches content via a Python script, then uses AI to score, filter, summarize, and deeply analyze top items. No external AI API key required.

## Trigger

User types `/horizon-briefing` or asks to "generate a briefing" / "run horizon briefing".

## Phase 1: Environment Check

1. Locate `config.json` in the current working directory. If not found:
   - Show the user two options:
     - **A)** Create a custom config — read `references/config-schema.md` from this skill directory and show the example
     - **B)** Use the built-in preset — copy `assets/presets/default-config.json` to `config.json` (LLM/Agent engineering sources: HackerNews, Reddit r/LocalLLaMA + r/MachineLearning, 量子位, 新智元, Simon Willison, Hugging Face, LangChain, ArXiv cs.AI, Google Cloud Blog, GitHub releases for anthropics/anthropic-sdk-python and langchain-ai/langchain)
   - If user chooses B, copy the preset file and continue
   - Stop until config exists
2. Check Python deps: `python3 -c "import httpx; import feedparser; import bs4; print('OK')"`
3. If deps are missing, tell the user and ask if they want to run `scripts/install_deps.sh`. If the user declines, stop and explain manual install.

## Phase 2: Fetch Data

1. Ask the user: "抓取最近几天的内容？（默认 3 天，输入数字或直接回车）"
2. Run with the user's input (default 3 if no input):
   `python3 <skill_dir>/scripts/fetch.py --config config.json --days N`
3. Verify `fetched.json` was created, then read it.
4. Report item count and source count to the user.

## Phase 3: Score and Filter

Read `references/scoring-criteria.md` from this skill directory before scoring.

Score each item 0–10 using the 5-dimension rubric (新颖性, 影响力, 技术深度, 社区信号, 时效性 — 2 points each). Sort descending, take top N from `config_snapshot.top_n` (default 10).

Output a scoring summary table to the user showing rank, title, and score.

## Phase 3.5: Source Analysis

After scoring, before generating summaries:

1. Count items and average score per source
2. Identify the top source (most high-scoring items)
3. Extract 3 trending themes from top-N item titles and content
4. Compose the `{source_analysis}` paragraph:

```
共抓取 {total} 条，来自 {source_count} 个源。
最活跃源：{top_source}（{n} 条，均分 {avg}/10）
今日热点主题：{theme_1}、{theme_2}、{theme_3}
```

## Phase 4: Generate Summary

Read `references/summary-writing-guide.md` from this skill directory before writing.

For each language in `config_snapshot.languages`, generate a summary following `assets/templates/summary.md`:
- Language handling: `"en"` = English, `"zh"` = Chinese with Pangu spacing (space between CJK and ASCII)
- Each item gets a `{one_sentence_abstract}` — one complete sentence, not a title rewrite
- Include the `{source_analysis}` paragraph from Phase 3.5

Write to: `./fetchs/{output_dir}/{YYYY-MM-DD}/summary-{lang}.md`

## Phase 5: Deep Analysis

Read `references/article-writing-guide.md` from this skill directory before writing.

For each top-N item, generate a deep analysis following `assets/templates/article.md`:
- Sections: 摘要, 核心内容, 技术背景, 方法与实现, 影响与意义, 前景展望, 社区讨论
- 社区讨论: only generate if the item has comments data; otherwise omit the section entirely
- Write to: `./fetchs/{output_dir}/{YYYY-MM-DD}/articles/{N}-{title_slug}-{lang}.md`
- `title_slug`: lowercase, spaces to hyphens, remove non-alphanumeric, truncate to 50 chars

## Phase 6: Completion Report

- Total items fetched, items selected, files generated (list paths), any errors

## Notes

- The fetch script handles all network requests. Do not use WebFetch or curl for source data.
- All AI analysis is done by Claude in-context. No external AI API calls.
- If 0 items are fetched, skip phases 3–5.
- For 100+ items, score in batches of ~30 to avoid context overflow.
