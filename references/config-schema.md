# config.json Schema Reference

## Full Example Configuration

```json
{
  "sources": {
    "github": [
      {
        "type": "user_events",
        "username": "torvalds",
        "enabled": true
      },
      {
        "type": "repo_releases",
        "owner": "kubernetes",
        "repo": "kubernetes",
        "enabled": true
      }
    ],
    "hackernews": {
      "enabled": true,
      "fetch_top_stories": true,
      "min_score": 100
    },
    "rss": [
      {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "enabled": true,
        "category": "startups"
      },
      {
        "name": "ArXiv CS",
        "url": "https://arxiv.org/rss/cs.AI",
        "enabled": true,
        "category": "research"
      }
    ],
    "reddit": {
      "enabled": true,
      "subreddits": {
        "enabled": true,
        "list": ["r/programming", "r/golang", "r/rust"]
      },
      "users": {
        "enabled": false,
        "list": []
      },
      "fetch_comments": true
    },
    "telegram": {
      "enabled": true,
      "channels": {
        "enabled": true,
        "list": ["@channel_name_1", "@channel_name_2"]
      }
    }
  },
  "filtering": {
    "time_window_hours": 24
  },
  "output": {
    "languages": ["en"],
    "top_n": 10,
    "output_dir": "output"
  }
}
```

## Field Reference

### sources.github[]

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Either `user_events` or `repo_releases` |
| username | string | Conditional | GitHub username (required when type is `user_events`) |
| owner | string | Conditional | Repository owner (required when type is `repo_releases`) |
| repo | string | Conditional | Repository name (required when type is `repo_releases`) |
| enabled | boolean | No | Enable/disable this source (default: true) |

### sources.hackernews

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| enabled | boolean | No | Enable/disable HackerNews source (default: true) |
| fetch_top_stories | boolean | No | Fetch top stories instead of new (default: true) |
| min_score | number | No | Minimum score threshold for stories (default: 0) |

### sources.rss[]

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Display name for the RSS feed |
| url | string | Yes | Feed URL (supports `${ENV_VAR}` substitution) |
| enabled | boolean | No | Enable/disable this feed (default: true) |
| category | string | No | Category tag for organization |

### sources.reddit

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| enabled | boolean | No | Enable/disable Reddit source (default: true) |
| subreddits.enabled | boolean | No | Enable subreddit fetching (default: true) |
| subreddits.list | string[] | No | List of subreddits (e.g., `["r/programming", "r/golang"]`) |
| users.enabled | boolean | No | Enable user profile fetching (default: false) |
| users.list | string[] | No | List of usernames to monitor |
| fetch_comments boolean | No | Include comments in analysis (default: true) |

### sources.telegram

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| enabled | boolean | No | Enable/disable Telegram source (default: true) |
| channels.enabled | boolean | No | Enable channel fetching (default: true) |
| channels.list | string[] | No | List of channel names (e.g., `["@channel_name"]`) |

### filtering

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| time_window_hours | number | No | 24 | Hours to look back for content |

### output

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| languages | string[] | No | `["en"]` | Output languages (ISO 639-1 codes) |
| top_n | number | No | 10 | Number of top items to include in briefing |
| output_dir | string | No | `"output"` | Directory for generated briefings |

## Environment Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| GITHUB_TOKEN | string | No | GitHub API token for higher rate limits and private repo access. Recommended for production use. |

### onment Variables in Config

Environment variables can be referenced in RSS feed URLs using the `${ENV_VAR}` syntax:

```json
{
  "rss": [
    {
      "name": "Private Feed",
      "url": "https://example.com/feed?token=${FEED_TOKEN}",
      "enabled": true
    }
  ]
}
```
