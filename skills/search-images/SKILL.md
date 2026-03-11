---
name: search-images
description: 使用 DuckDuckGo 搜索并下载视频幻灯片所需的图片素材（无需 API Key）。当视频项目缺少 image 字段、某个片段没有图片、或用户要求根据关键词搜图时使用。
---

# search-images

根据关键词从 DuckDuckGo 搜索并下载图片。DuckDuckGo 对**中文关键词**效果极佳，能直接找到相关的动漫截图、人物配图等。若 DuckDuckGo 触发限速，自动降级到 Bing 抓取。无需任何 API Key。

## 脚本用法

```bash
python skills/search-images/scripts/search_images.py \
  --keywords "凡人修仙传 银月" \
  --output projects/myvideo/images/contestant_02/ \
  [--count 5] \
  [--config config.yaml]
```

**参数说明：**
- `--keywords` — 搜索关键词，**优先使用中文**（如 `"凡人修仙传 银月"`、`"灌篮高手 流川枫"`）
- `--output` — 图片保存目录（不存在时自动创建）
- `--count` — 下载数量（默认取 config 中的 `images_per_slide`，通常为 5）
- `--config` — `config.yaml` 路径（默认：当前目录下的 `config.yaml`）

**标准输出（JSON）：**
```json
{
  "images": [
    {"path": "projects/myvideo/images/contestant_02/photo_00.jpg", "source": "duckduckgo", "url": "...", "title": "凡人修仙传 银月 角色介绍"},
    {"path": "projects/myvideo/images/contestant_02/photo_01.jpg", "source": "duckduckgo", "url": "...", "title": "..."},
    {"path": "projects/myvideo/images/contestant_02/photo_02.jpg", "source": "duckduckgo", "url": "...", "title": "..."}
  ]
}
```

每张图片包含 `title` 字段（来自 DuckDuckGo 的页面标题），供 agent 判断图片内容。

## 工作流

对每个缺少 `image` 字段的片段：

1. 使用片段的 `keywords` 字段。若也没有 keywords，则根据 `text` 和项目 `topic` 生成 2-4 个**中文**关键词。
2. 执行脚本，保存到 `projects/{name}/images/contestant_{index:02d}/`，下载 3-5 张候选图。
3. **agent 根据 `title` 和 `url` 选择最相关的图片**（通常 DuckDuckGo 默认排在最前的最佳，但 title 明显不符时应选其他）。
4. 更新 `project.yaml` 中对应片段的 `image` 路径（填入选中的图片路径）。

## 关键词技巧

- **中文关键词效果远好于英文**：搜索 `"凡人修仙传 银月"` 直接返回动漫截图；`"silver wolf spirit Chinese mythology"` 只能返回泛图。
- 格式：`"{作品名} {角色名}"` 或 `"{作品名} {场景/事件}"`。
- 对于非动漫话题，也可用中文描述视觉内容：`"NBA 詹姆斯 扣篮"`、`"深圳 城市夜景"`。
- 避免用 webp 图（脚本已自动过滤）。

## 常见错误与修复

| 错误信息 | 原因 | 修复方法 |
|---------|------|---------|
| `ModuleNotFoundError: No module named 'requests'` | Python 依赖未安装 | 在项目根目录执行 `uv sync`（或 `pip install requests`） |
| `Ratelimited by DuckDuckGo, falling back to Bing` | DuckDuckGo 触发限速 | 脚本会自动降级到 Bing，无需手动干预 |
| `All sources failed` / 下载 0 张图 | 两个图源均被限速或关键词太冷僻 | 等待 30 秒后重试；或换一组关键词；或手动将图片放入 `materials/contestant_XX/` 目录 |
| 下载的图片全是错误的内容 | 关键词不够具体 | 加入更多限定词，如作品名、角色全名、场景描述 |
| `SSLError` / 证书错误 | 网络环境问题 | 检查是否使用了代理，或尝试更换网络 |
