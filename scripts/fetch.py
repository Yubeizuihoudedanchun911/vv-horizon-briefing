#!/usr/bin/env python3
"""fetch.py — self-contained fetcher for vv-horizon-briefing.

Reads config.json, concurrently fetches from GitHub, HackerNews, RSS,
Reddit, and Telegram, deduplicates by URL, and writes fetched.json.

Dependencies: httpx, feedparser, beautifulsoup4 (plus stdlib)
"""

import argparse
import asyncio
import calendar
import json
import logging
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("fetch")

# ---------------------------------------------------------------------------
# ContentItem dataclass
# ---------------------------------------------------------------------------

@dataclass
class ContentItem:
    id: str
    source_type: str  # "github" | "hackernews" | "rss" | "reddit" | "telegram"
    title: str
    url: str
    content: str
    author: str
    published_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": str(self.url),
            "content": self.content,
            "source_type": self.source_type,
            "published_at": self.published_at.isoformat(),
            "author": self.author,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# ID helper
# ---------------------------------------------------------------------------

def generate_id(source: str, subtype: str, native_id: str) -> str:
    return f"{source}:{subtype}:{native_id}"


# ---------------------------------------------------------------------------
# BaseScraper
# ---------------------------------------------------------------------------

class BaseScraper(ABC):
    def __init__(self, config: dict, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client

    @abstractmethod
    async def fetch(self, since: datetime) -> List[ContentItem]:
        pass


# ---------------------------------------------------------------------------
# GitHubScraper
# ---------------------------------------------------------------------------

class GitHubScraper(BaseScraper):
    def __init__(self, sources: List[dict], http_client: httpx.AsyncClient):
        super().__init__({"sources": sources}, http_client)
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Horizon-Aggregator",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def fetch(self, since: datetime) -> List[ContentItem]:
        items = []
        for source in self.config["sources"]:
            if not source.get("enabled", True):
                continue
            stype = source.get("type", "")
            if stype == "user_events" and source.get("username"):
                items.extend(await self._fetch_user_events(source["username"], since))
            elif stype == "repo_releases" and source.get("owner") and source.get("repo"):
                items.extend(await self._fetch_repo_releases(source["owner"], source["repo"], since))
        return items

    async def _fetch_user_events(self, username: str, since: datetime) -> List[ContentItem]:
        url = f"{self.base_url}/users/{username}/events/public"
        items = []
        try:
            response = await self.client.get(url, headers=self._get_headers(), follow_redirects=True)
            response.raise_for_status()
            for event in response.json():
                created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
                if created_at < since:
                    continue
                if event["type"] not in ("PushEvent", "CreateEvent", "ReleaseEvent", "PublicEvent", "WatchEvent"):
                    continue
                item = self._parse_event(event, username)
                if item:
                    items.append(item)
        except httpx.HTTPError as e:
            logger.warning("GitHub events error for %s: %s", username, e)
        return items

    def _parse_event(self, event: dict, username: str) -> Optional[ContentItem]:
        etype = event["type"]
        event_id = event["id"]
        created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        repo_name = event["repo"]["name"]
        repo_url = f"https://github.com/{repo_name}"

        if etype == "PushEvent":
            commits = event["payload"].get("commits", [])
            title = f"{username} pushed {len(commits)} commit(s) to {repo_name}"
            content = "\n".join(c.get("message", "") for c in commits[:3])
        elif etype == "CreateEvent":
            ref_type = event["payload"].get("ref_type", "repository")
            title = f"{username} created {ref_type} in {repo_name}"
            content = event["payload"].get("description", "")
        elif etype == "ReleaseEvent":
            release = event["payload"].get("release", {})
            title = f"{username} released {release.get('tag_name', '')} in {repo_name}"
            content = release.get("body", "")
            repo_url = release.get("html_url", repo_url)
        elif etype == "PublicEvent":
            title = f"{username} made {repo_name} public"
            content = ""
        elif etype == "WatchEvent":
            title = f"{username} starred {repo_name}"
            content = ""
        else:
            return None

        return ContentItem(
            id=generate_id("github", "event", event_id),
            source_type="github",
            title=title,
            url=repo_url,
            content=content or "",
            author=username,
            published_at=created_at,
            metadata={"event_type": etype, "repo": repo_name},
        )

    async def _fetch_repo_releases(self, owner: str, repo: str, since: datetime) -> List[ContentItem]:
        url = f"{self.base_url}/repos/{owner}/{repo}/releases"
        items = []
        try:
            response = await self.client.get(url, headers=self._get_headers(), follow_redirects=True)
            response.raise_for_status()
            for release in response.json():
                published_at = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
                if published_at < since:
                    continue
                items.append(ContentItem(
                    id=generate_id("github", "release", str(release["id"])),
                    source_type="github",
                    title=f"{owner}/{repo} released {release['tag_name']}",
                    url=release["html_url"],
                    content=release.get("body", "") or "",
                    author=release["author"]["login"],
                    published_at=published_at,
                    metadata={"repo": f"{owner}/{repo}", "tag": release["tag_name"], "prerelease": release.get("prerelease", False)},
                ))
        except httpx.HTTPError as e:
            logger.warning("GitHub releases error for %s/%s: %s", owner, repo, e)
        return items

# ---------------------------------------------------------------------------
# HackerNewsScraper
# ---------------------------------------------------------------------------

TOP_COMMENTS_LIMIT = 5


class HackerNewsScraper(BaseScraper):
    def __init__(self, config: dict, http_client: httpx.AsyncClient):
        super().__init__(config, http_client)
        self.base_url = "https://hacker-news.firebaseio.com/v0"

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.config.get("enabled", True):
            return []
        try:
            response = await self.client.get(f"{self.base_url}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()

            fetch_count = self.config.get("fetch_top_stories", 30)
            story_ids = story_ids[:fetch_count]

            tasks = [self._fetch_story(sid) for sid in story_ids]
            stories = await asyncio.gather(*tasks, return_exceptions=True)

            min_score = self.config.get("min_score", 100)
            valid_stories = []
            comment_tasks = []

            for story in stories:
                if isinstance(story, Exception) or story is None:
                    continue
                if story.get("score", 0) < min_score:
                    continue
                published_at = datetime.fromtimestamp(story["time"], tz=timezone.utc)
                if published_at < since:
                    continue
                valid_stories.append(story)
                comment_ids = story.get("kids", [])[:TOP_COMMENTS_LIMIT]
                comment_tasks.append(self._fetch_comments(comment_ids))

            all_comments = await asyncio.gather(*comment_tasks, return_exceptions=True)

            items = []
            for story, comments in zip(valid_stories, all_comments):
                if isinstance(comments, Exception):
                    comments = []
                item = self._parse_story(story, comments)
                if item:
                    items.append(item)
            return items

        except httpx.HTTPError as e:
            logger.warning("HackerNews fetch error: %s", e)
            return []

    async def _fetch_story(self, story_id: int) -> Optional[dict]:
        try:
            response = await self.client.get(f"{self.base_url}/item/{story_id}.json")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None

    async def _fetch_comments(self, comment_ids: List[int]) -> List[dict]:
        if not comment_ids:
            return []
        tasks = [self._fetch_story(cid) for cid in comment_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        comments = []
        for r in results:
            if isinstance(r, dict) and r.get("text") and not r.get("deleted") and not r.get("dead"):
                comments.append(r)
        return comments

    def _parse_story(self, story: dict, comments: List[dict]) -> Optional[ContentItem]:
        story_id = story["id"]
        title = story.get("title", "")
        url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
        author = story.get("by", "unknown")
        published_at = datetime.fromtimestamp(story["time"], tz=timezone.utc)

        parts = []
        if story.get("text"):
            parts.append(story["text"])
        if comments:
            parts.append("\n--- Top Comments ---")
            for c in comments:
                commenter = c.get("by", "anon")
                text = re.sub(r'<[^>]+>', ' ', c.get("text", "")).strip()
                if len(text) > 500:
                    text = text[:497] + "..."
                parts.append(f"[{commenter}]: {text}")

        content = "\n\n".join(parts)
        hn_url = f"https://news.ycombinator.com/item?id={story_id}"

        return ContentItem(
            id=generate_id("hackernews", "story", str(story_id)),
            source_type="hackernews",
            title=title,
            url=url,
            content=content,
            author=author,
            published_at=published_at,
            metadata={
                "score": story.get("score", 0),
                "descendants": story.get("descendants", 0),
                "type": story.get("type", "story"),
                "discussion_url": hn_url,
                "comment_count": len(comments),
            },
        )


# ---------------------------------------------------------------------------
# RSSScraper
# ---------------------------------------------------------------------------

class RSSScraper(BaseScraper):
    def __init__(self, sources: List[dict], http_client: httpx.AsyncClient):
        super().__init__({"sources": sources}, http_client)

    async def fetch(self, since: datetime) -> List[ContentItem]:
        items = []
        for source in self.config["sources"]:
            if not source.get("enabled", True):
                continue
            items.extend(await self._fetch_feed(source, since))
        return items

    async def _fetch_feed(self, source: dict, since: datetime) -> List[ContentItem]:
        items = []
        try:
            feed_url = re.sub(
                r'\$\{(\w+)\}',
                lambda m: os.environ.get(m.group(1), m.group(0)).strip(),
                str(source.get("url", "")),
            )
            response = await self.client.get(feed_url, follow_redirects=True)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            for entry in feed.entries:
                published_at = self._parse_date(entry)
                if not published_at or published_at < since:
                    continue

                feed_id = str(source.get("url", "")).split("//")[-1].replace("/", "_")
                entry_id = entry.get("id", entry.get("link", ""))
                content = self._extract_content(entry)

                items.append(ContentItem(
                    id=generate_id("rss", feed_id, str(hash(entry_id))),
                    source_type="rss",
                    title=entry.get("title", "Untitled"),
                    url=entry.get("link", str(source.get("url", ""))),
                    content=content,
                    author=entry.get("author", source.get("name", "")),
                    published_at=published_at,
                    metadata={
                        "feed_name": source.get("name", ""),
                        "category": source.get("category", ""),
                        "tags": [tag.term for tag in entry.get("tags", [])],
                    },
                ))
        except httpx.HTTPError as e:
            logger.warning("RSS fetch error for %s: %s", source.get("name"), e)
        except Exception as e:
            logger.warning("RSS parse error for %s: %s", source.get("name"), e)
        return items

    def _parse_date(self, entry) -> Optional[datetime]:
        for field in ("published", "updated", "created"):
            if field in entry:
                try:
                    parsed_field = f"{field}_parsed"
                    if parsed_field in entry and entry[parsed_field]:
                        return datetime.fromtimestamp(calendar.timegm(entry[parsed_field]), tz=timezone.utc)
                    return parsedate_to_datetime(entry[field])
                except Exception:
                    continue
        return None

    def _extract_content(self, entry) -> str:
        if "summary" in entry:
            return entry.summary
        if "description" in entry:
            return entry.description
        if "content" in entry and entry.content:
            return entry.content[0].get("value", "")
        return ""


# ---------------------------------------------------------------------------
# RedditScraper
# ---------------------------------------------------------------------------

REDDIT_BASE = "https://www.reddit.com"
REDDIT_UA = "Horizon/1.0 (content aggregator; +https://github.com/thysrael/horizon)"


class RedditScraper(BaseScraper):
    def __init__(self, config: dict, http_client: httpx.AsyncClient):
        super().__init__(config, http_client)

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.config.get("enabled", True):
            return []

        tasks = []
        for sub_cfg in self.config.get("subreddits", []):
            if sub_cfg.get("enabled", True):
                tasks.append(self._fetch_subreddit(sub_cfg, since))
        for user_cfg in self.config.get("users", []):
            if user_cfg.get("enabled", True):
                tasks.append(self._fetch_user(user_cfg, since))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Reddit source error: %s", result)
            elif isinstance(result, list):
                items.extend(result)
        return items

    async def _fetch_subreddit(self, cfg: dict, since: datetime) -> List[ContentItem]:
        sort = cfg.get("sort", "hot")
        params = {"limit": min(cfg.get("fetch_limit", 25), 100), "raw_json": 1}
        if sort in ("top", "controversial"):
            params["t"] = cfg.get("time_filter", "day")
        url = f"{REDDIT_BASE}/r/{cfg['subreddit']}/{sort}.json"
        data = await self._reddit_get(url, params)
        if not data:
            return []
        posts = [c["data"] for c in data.get("data", {}).get("children", []) if c.get("kind") == "t3"]
        return await self._process_posts(posts, since, "subreddit", cfg["subreddit"], cfg.get("min_score", 0))

    async def _fetch_user(self, cfg: dict, since: datetime) -> List[ContentItem]:
        params = {"limit": min(cfg.get("fetch_limit", 25), 100), "sort": cfg.get("sort", "new"), "raw_json": 1}
        url = f"{REDDIT_BASE}/user/{cfg['username']}/submitted.json"
        data = await self._reddit_get(url, params)
        if not data:
            return []
        posts = [c["data"] for c in data.get("data", {}).get("children", []) if c.get("kind") == "t3"]
        return await self._process_posts(posts, since, "user", cfg["username"], min_score=0)

    async def _process_posts(self, posts: list, since: datetime, subtype: str, source_name: str, min_score: int) -> List[ContentItem]:
        fetch_comments = self.config.get("fetch_comments", 0)

        valid_posts = []
        for post in posts:
            created = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc)
            if created < since:
                continue
            if post.get("score", 0) < min_score:
                continue
            valid_posts.append(post)

        if not valid_posts:
            return []

        if fetch_comments > 0:
            comment_tasks = [self._fetch_comments(post.get("subreddit", ""), post["id"]) for post in valid_posts]
            all_comments = await asyncio.gather(*comment_tasks, return_exceptions=True)
            all_comments = [[] if isinstance(c, Exception) else c for c in all_comments]
        else:
            all_comments = [[] for _ in valid_posts]

        items = []
        for post, comments in zip(valid_posts, all_comments):
            item = self._parse_post(post, comments, subtype)
            if item:
                items.append(item)
        return items

    async def _fetch_comments(self, subreddit: str, post_id: str) -> List[dict]:
        fetch_limit = self.config.get("fetch_comments", 5)
        url = f"{REDDIT_BASE}/r/{subreddit}/comments/{post_id}.json"
        params = {"limit": fetch_limit, "depth": 1, "sort": "top", "raw_json": 1}
        data = await self._reddit_get(url, params)
        if not data or not isinstance(data, list) or len(data) < 2:
            return []
        comments = []
        for child in data[1].get("data", {}).get("children", []):
            if child.get("kind") != "t1":
                continue
            c = child["data"]
            if c.get("body") and c.get("distinguished") != "moderator":
                comments.append(c)
        comments.sort(key=lambda c: c.get("score", 0), reverse=True)
        return comments[:fetch_limit]

    def _parse_post(self, post: dict, comments: List[dict], subtype: str) -> Optional[ContentItem]:
        post_id = post["id"]
        title = post.get("title", "")
        is_self = post.get("is_self", False)
        subreddit = post.get("subreddit", "")
        discussion_url = f"https://www.reddit.com{post.get('permalink', '')}"
        url = discussion_url if is_self else post.get("url", discussion_url)
        author = post.get("author", "unknown")
        created = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc)

        parts = []
        if post.get("selftext"):
            text = post["selftext"]
            if len(text) > 1500:
                text = text[:1497] + "..."
            parts.append(text)
        if comments:
            parts.append("\n--- Top Comments ---")
            for c in comments:
                body = c.get("body", "").strip()
                if len(body) > 500:
                    body = body[:497] + "..."
                parts.append(f"[{c.get('author', 'anon')} ({c.get('score', 0)} pts)]: {body}")

        return ContentItem(
            id=generate_id("reddit", subtype, post_id),
            source_type="reddit",
            title=title,
            url=url,
            content="\n\n".join(parts),
            author=author,
            published_at=created,
            metadata={
                "score": post.get("score", 0),
                "upvote_ratio": post.get("upvote_ratio"),
                "num_comments": post.get("num_comments", 0),
                "subreddit": subreddit,
                "is_self": is_self,
                "flair": post.get("link_flair_text"),
                "discussion_url": discussion_url,
            },
        )

    async def _reddit_get(self, url: str, params: dict) -> Optional[dict]:
        headers = {"User-Agent": REDDIT_UA}
        try:
            response = await self.client.get(url, params=params, headers=headers, follow_redirects=True)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning("Reddit rate limited, retrying after %ds", retry_after)
                await asyncio.sleep(retry_after)
                response = await self.client.get(url, params=params, headers=headers, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.warning("Reddit request failed for %s: %s", url, e)
            return None

# ---------------------------------------------------------------------------
# TelegramScraper
# ---------------------------------------------------------------------------

TELEGRAM_WEB_BASE = "https://t.me/s"
TELEGRAM_UA = "Mozilla/5.0 (compatible; Horizon/1.0; +https://github.com/thysrael/horizon)"


class TelegramScraper(BaseScraper):
    def __init__(self, config: dict, http_client: httpx.AsyncClient):
        super().__init__(config, http_client)

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.config.get("enabled", True):
            return []

        tasks = []
        for channel_cfg in self.config.get("channels", []):
            if channel_cfg.get("enabled", True):
                tasks.append(self._fetch_channel(channel_cfg, since))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Telegram channel error: %s", result)
            elif isinstance(result, list):
                items.extend(result)
        return items

    async def _fetch_channel(self, cfg: dict, since: datetime) -> List[ContentItem]:
        channel = cfg["channel"]
        url = f"{TELEGRAM_WEB_BASE}/{channel}"
        headers = {"User-Agent": TELEGRAM_UA}
        try:
            response = await self.client.get(url, headers=headers, follow_redirects=True, timeout=120.0)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning("Telegram rate limited for %s, retrying after %ds", channel, retry_after)
                await asyncio.sleep(retry_after)
                response = await self.client.get(url, headers=headers, follow_redirects=True, timeout=120.0)
            response.raise_for_status()
        except Exception as e:
            logger.warning("Telegram request failed for %s: %r", channel, e)
            return []
        return self._parse_channel_html(response.text, cfg, since)

    def _parse_channel_html(self, html: str, cfg: dict, since: datetime) -> List[ContentItem]:
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.select("div.tgme_widget_message[data-post]")
        fetch_limit = cfg.get("fetch_limit", 20)
        items = []
        for msg in messages[-fetch_limit:]:
            item = self._parse_message(msg, cfg["channel"], since)
            if item:
                items.append(item)
        return items

    def _parse_message(self, msg_el, channel: str, since: datetime) -> Optional[ContentItem]:
        data_post = msg_el.get("data-post", "")
        msg_id = data_post.split("/")[-1] if "/" in data_post else data_post
        if not msg_id:
            return None

        time_el = msg_el.select_one("time[datetime]")
        if not time_el:
            return None
        try:
            published_at = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            return None

        if published_at < since:
            return None

        text_el = msg_el.select_one("div.tgme_widget_message_text")
        if not text_el:
            return None

        for br in text_el.find_all("br"):
            br.replace_with("\n")
        text = text_el.get_text(separator="").strip()
        if not text:
            return None

        title = self._make_title(text)
        msg_url = f"https://t.me/{channel}/{msg_id}"
        canonical_url = msg_url
        for a in text_el.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "t.me" not in href:
                canonical_url = href
                break

        return ContentItem(
            id=generate_id("telegram", channel, msg_id),
            source_type="telegram",
            title=title,
            url=canonical_url,
            content=text,
            author=channel,
            published_at=published_at,
            metadata={"msg_url": msg_url, "channel": channel},
        )

    @staticmethod
    def _make_title(text: str) -> str:
        first_para = text.split("\n\n")[0].replace("\n", " ").strip()
        if len(first_para) <= 80:
            return first_para
        match = re.search(r"[。！？]", first_para[:80])
        if match:
            return first_para[: match.end()]
        return first_para[:80]


# ---------------------------------------------------------------------------
# merge_cross_source_duplicates
# ---------------------------------------------------------------------------

def merge_cross_source_duplicates(items: List[ContentItem]) -> List[ContentItem]:
    def normalize_url(url: str) -> str:
        parsed = urlparse(str(url))
        host = parsed.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        path = parsed.path.rstrip("/")
        return f"{host}{path}"

    url_groups: Dict[str, List[ContentItem]] = {}
    for item in items:
        key = normalize_url(str(item.url))
        url_groups.setdefault(key, []).append(item)

    merged = []
    for key, group in url_groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        primary = max(group, key=lambda x: len(x.content or ""))
        all_sources = set()
        for item in group:
            all_sources.add(item.source_type)
            for mk, mv in item.metadata.items():
                if mk not in primary.metadata or not primary.metadata[mk]:
                    primary.metadata[mk] = mv
            if item is not primary and item.content:
                if primary.content and item.content not in primary.content:
                    primary.content = (primary.content or "") + f"\n\n--- From {item.source_type} ---\n" + item.content

        primary.metadata["merged_sources"] = list(all_sources)
        merged.append(primary)

    return merged


# ---------------------------------------------------------------------------
# run_fetch — main async logic
# ---------------------------------------------------------------------------

async def run_fetch(config_path: Path) -> None:
    config = load_config(config_path)
    output_dir = config_path.parent

    filtering = config.get("filtering", {})
    output_cfg = config.get("output", {})
    sources_cfg = config.get("sources", {})

    time_window_hours = filtering.get("time_window_hours", 24)
    since = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

    logger.info("Fetching content since %s (%dh window)", since.strftime("%Y-%m-%d %H:%M UTC"), time_window_hours)

    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []

        # GitHub
        github_sources = sources_cfg.get("github", [])
        if github_sources:
            tasks.append(GitHubScraper(github_sources, client).fetch(since))

        # HackerNews
        hn_cfg = sources_cfg.get("hackernews", {})
        if hn_cfg.get("enabled", False):
            tasks.append(HackerNewsScraper(hn_cfg, client).fetch(since))

        # RSS
        rss_sources = sources_cfg.get("rss", [])
        if rss_sources:
            tasks.append(RSSScraper(rss_sources, client).fetch(since))

        # Reddit
        reddit_cfg = sources_cfg.get("reddit", {})
        if reddit_cfg.get("enabled", False):
            tasks.append(RedditScraper(reddit_cfg, client).fetch(since))

        # Telegram
        telegram_cfg = sources_cfg.get("telegram", {})
        if telegram_cfg.get("enabled", False):
            tasks.append(TelegramScraper(telegram_cfg, client).fetch(since))

        if not tasks:
            logger.warning("No sources enabled — nothing to fetch.")
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: List[ContentItem] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Source fetch error: %s", result)
        elif isinstance(result, list):
            all_items.extend(result)

    logger.info("Fetched %d items total", len(all_items))

    merged_items = merge_cross_source_duplicates(all_items)
    if len(merged_items) < len(all_items):
        logger.info("Merged %d duplicates -> %d unique items", len(all_items) - len(merged_items), len(merged_items))

    output = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "config_snapshot": {
            "time_window_hours": time_window_hours,
            "top_n": output_cfg.get("top_n", 10),
            "languages": output_cfg.get("languages", filtering.get("languages", [])),
        },
        "item_count": len(merged_items),
        "items": [item.to_dict() for item in merged_items],
    }

    output_path = output_dir / "fetched.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("Written %d items to %s", len(merged_items), output_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="vv-horizon-briefing fetcher")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to config.json (default: config.json in cwd)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_fetch(args.config))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        logger.error("Fatal error: %s", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
