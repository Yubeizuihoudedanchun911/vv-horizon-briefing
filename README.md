# vv-horizon-briefing

A Claude Code SKILL for daily tech briefings — no external AI API key required.

Extracted and adapted from the [Horizon](https://github.com/Thysrael/Horizon) open-source project. Horizon is an AI-driven information aggregation system; this skill packages its data-fetching capabilities into a standalone Claude Code skill, using Claude itself for analysis.

## How It Works

```
config.json → fetch.py → fetched.json → Claude scores → Markdown output
```

1. Fetch — `fetch.py` pulls items from all configured sources into `fetched.json`
2. Score — Claude evaluates each item in-context (novelty, impact, depth, community signal, timeliness)
3. Summarize — Claude writes a daily digest in each configured language
4. Analyze — Claude generates a deep-dive article for each top item

## Installation

```bash
git clone https://github.com/<your-username>/vv-horizon-briefing ~/.claude/skills/vv-horizon-briefing
```

## Setup

Create `config.json` in your working directory:

```json
{
  "sources": {
    "hackernews": { "enabled": true, "fetch_top_stories": 30, "min_score": 100 },
    "rss": [
      { "name": "Hacker News RSS", "url": "https://hnrss.org/frontpage", "enabled": true }
    ]
  },
  "filtering": { "time_window_hours": 24 },
  "output": { "languages": ["zh"], "top_n": 10, "output_dir": "output" }
}
```

See [config-schema.md](references/config-schema.md) for full reference.

For GitHub sources, set the optional env var:

```bash
export GITHUB_TOKEN=your_token_here
```

## Usage

In Claude Code, type:

```
/horizon-briefing
```

Or just say: "Generate today's tech briefing"

## Output

```
output/
└── 2026-04-11/
    ├── summary-en.md
    ├── summary-zh.md
    └── articles/
        ├── 1-some-article-title-en.md
        ├── 1-some-article-title-zh.md
        ├── 2-another-article-en.md
        └── ...
```

## Data Sources

| Source     | Description                                      |
|------------|--------------------------------------------------|
| GitHub     | User events (pushes, stars, releases) and repo releases |
| HackerNews | Top stories with top comments from news.ycombinator.com |
| RSS        | Any RSS/Atom feed URL                                   |
| Reddit     | Subreddit hot posts + user submissions, with comments   |
| Telegram   | Public channel messages via web preview                  |

## Use Case: AI Agent & LLM 7-Day Weekly Briefing

> Fetching the last 7 days, prioritizing AI agent engineering and LLM model content.

**Trigger:**
```
拉取近7天的信息, 优先读取ai agent工程、llm模型内容
```

**Result (2026-04-12):** 86 items fetched from 4 sources → Top 10 selected

| Rank | Title | Score |
|------|-------|-------|
| 1 | Small models also found the vulnerabilities that Mythos found (HN 348↑) | 10/10 |
| 2 | GLM 5.1 crushes every model except Opus in agentic benchmark at 1/3 cost (Reddit 282↑) | 9/10 |
| 3 | DFlash speculative decoding on Apple Silicon: 85 tok/s, 3.3x on Qwen3.5-9B (Reddit 135↑) | 8/10 |
| 4 | GLM 5.1 tops code arena rankings for open models (Reddit 546↑) | 8/10 |
| 5 | Near-100% Accurate Data for Agent with Comprehensive Context Engineering | 8/10 |
| 6 | Create Expert Content: Local Testing of a Multi-Agent System with Memory | 8/10 |
| 7 | What happened to Deepseek? (Reddit 293↑) | 8/10 |
| 8 | Gemma 4 31B vs Qwen 3.5 27B: long context workflows (Reddit 235↑) | 8/10 |
| 9 | GLM-5.1: Towards Long-Horizon Tasks | 7/10 |
| 10 | Deep Agents Deploy: open alternative to Claude Managed Agents | 7/10 |

**Key themes this week:** GLM-5.1 agent capability surge · Gemma 4 local inference optimization · AI Agent context engineering

**Output:** `summary-zh.md` + 10 deep-analysis articles under `data/2026-04-12/articles/`

---

## Acknowledgements

Built upon [Horizon](https://github.com/Thysrael/Horizon) by Thysrael and contributors.

## License

MIT
