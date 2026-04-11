# vv-horizon-briefing

一个无需外部 AI API Key 的 Claude Code SKILL，用于生成每日技术简报。

从 [Horizon](https://github.com/Thysrael/Horizon) 开源项目提取并改编。Horizon 是一个 AI 驱动的信息聚合系统；本 skill 将其数据抓取能力封装为独立的 Claude Code skill，并直接使用 Claude 进行分析。

## 工作原理

```
config.json → fetch.py → fetched.json → Claude 评分 → Markdown 输出
```

1. 抓取 — `fetch.py` 从所有配置的数据源拉取内容，写入 `fetched.json`
2. 评分 — Claude 在上下文中对每条内容评分（新颖性、影响力、技术深度、社区信号、时效性）
3. 摘要 — Claude 按配置的语言生成每日简报
4. 深度分析 — Claude 为每条 top 内容并行生成深度分析文章

## 安装

```bash
git clone https://github.com/<your-username>/vv-horizon-briefing ~/.claude/skills/vv-horizon-briefing
```

## 配置

在工作目录下创建 `config.json`：

```json
{
  "sources": {
    "hackernews": { "enabled": true, "fetch_top_stories": 30, "min_score": 100 },
    "rss": [
      { "name": "Hacker News RSS", "url": "https://hnrss.org/frontpage", "enabled": true }
    ]
  },
  "filtering": { "time_window_hours": 24 },
  "output": { "languages": ["zh"], "top_n": 10, "output_dir": "data" }
}
```

完整配置说明见 [config-schema.md](references/config-schema.md)。

如需使用 GitHub 数据源，可设置可选环境变量：

```bash
export GITHUB_TOKEN=your_token_here
```

## 使用方法

在 Claude Code 中输入：

```
/horizon-briefing
```

或直接说："生成今天的技术简报"

## 输出结构

```
data/
└── 2026-04-11/
    ├── fetched.json
    ├── summary-zh.md
    └── articles/
        ├── 1-some-article-title-zh.md
        ├── 2-another-article-zh.md
        └── ...
```

## 数据源

| 数据源     | 说明                                               |
|------------|----------------------------------------------------|
| GitHub     | 用户动态（push、star、release）及仓库 release 信息  |
| HackerNews | 热门文章及精选评论                                  |
| RSS        | 任意 RSS/Atom feed 地址                             |
| Reddit     | 子版块热帖及用户投稿，含评论                        |
| Telegram   | 公开频道消息（通过网页预览抓取）                    |

## 使用案例：AI Agent & LLM 近 7 天周报

> 拉取近 7 天信息，优先关注 AI Agent 工程和 LLM 模型内容。

**触发语：**
```
拉取近7天的信息, 优先读取ai agent工程、llm模型内容
```

**结果（2026-04-12）：** 从 4 个源抓取 86 条 → 筛选 Top 10

| 排名 | 标题 | 评分 |
|------|------|------|
| 1 | 小模型同样复现了 Mythos 发现的安全漏洞（HN 348↑） | 10/10 |
| 2 | GLM 5.1 以 1/3 成本达到 Opus Agent 水平（Reddit 282↑） | 9/10 |
| 3 | DFlash 推测解码在 Apple Silicon 上实现 85 tok/s、3.3x 加速（Reddit 135↑） | 8/10 |
| 4 | GLM 5.1 在 Code Arena 开源模型排名第一（Reddit 546↑） | 8/10 |
| 5 | 全面上下文工程让 Agent 数据准确率接近 100% | 8/10 |
| 6 | 带记忆的多 Agent 系统本地测试实践 | 8/10 |
| 7 | Deepseek 发生了什么？（Reddit 293↑） | 8/10 |
| 8 | Gemma 4 31B vs Qwen 3.5 27B 长上下文对比（Reddit 235↑） | 8/10 |
| 9 | GLM-5.1：面向长视野任务 | 7/10 |
| 10 | Deep Agents Deploy：Claude Managed Agents 的开源替代 | 7/10 |

**本周三大热点：** GLM-5.1 Agent 能力爆发 · Gemma 4 本地推理优化 · AI Agent Context Engineering

**输出：** `summary-zh.md` + 10 篇深度分析文章，位于 `data/2026-04-12/articles/`

---

## 致谢

基于 [Thysrael](https://github.com/Thysrael) 及贡献者的 [Horizon](https://github.com/Thysrael/Horizon) 项目构建。

## 许可证

MIT
