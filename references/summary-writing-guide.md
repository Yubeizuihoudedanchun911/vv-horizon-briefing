# 摘要写作指南

本指南用于生成 summary 文件中每条目的 `{one_sentence_abstract}` 和整体摘要内容。

## 核心规则

1. **首句点明最重要的事实** — what happened / what was released / what was discovered
2. **包含具体数字或指标**（如有）— 版本号、参数量、性能提升百分比
3. **第二句说明为什么重要** — why it matters to the reader
4. **避免"这是一篇关于..."式开头** — 直接陈述事实
5. **控制在 3-5 句**，使用主动语态
6. `{one_sentence_abstract}` 必须是完整句子，不能是标题的改写

## 示例

**好的摘要：**
> Meta 开源了 Llama 3.1 405B，参数量首次超越 GPT-4，并在多项基准测试中持平或超越闭源模型。这标志着开源 LLM 在能力上正式进入顶级梯队，开发者可免费用于商业用途。

**差的摘要：**
> 这篇文章介绍了 Meta 发布的新模型 Llama 3.1，是一个很重要的进展。

## 今日信源分析写法

`{source_analysis}` 段落格式：

```
共抓取 {total} 条，来自 {source_count} 个源。
最活跃源：{top_source}（{n} 条，均分 {avg}/10）
今日热点主题：{theme_1}、{theme_2}、{theme_3}
```

- 热点主题从高分条目的标题和内容中提取 3 个关键词/短语
- 均分保留一位小数
