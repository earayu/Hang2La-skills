---
name: search-images
description: 使用 Pexels 和 Unsplash API 搜索并下载视频幻灯片所需的图片素材。当视频项目缺少图片、某个片段没有 image 字段、或用户要求根据关键词搜图时使用。
---

# search-images

根据关键词从 Pexels（主要）和 Unsplash（备用）下载图片。

## 脚本用法

```bash
python .cursor/skills/search-images/scripts/search_images.py \
  --keywords "关键词" \
  --output 输出目录路径 \
  [--count 3] \
  [--orientation landscape] \
  [--config config.yaml]
```

**参数说明：**
- `--keywords` — 以空格分隔的搜索词（如 `"故宫 宫殿 历史"`）
- `--output` — 图片保存目录（不存在时自动创建）
- `--count` — 下载数量（默认取 config 中的 `images_per_slide`，通常为 3）
- `--orientation` — `landscape`（横向）| `portrait`（纵向）| `square`（方形），默认 landscape
- `--config` — `config.yaml` 路径（默认：当前目录下的 `config.yaml`）

**标准输出（JSON）：**
```json
{
  "images": [
    {"path": "projects/myvideo/images/slide_01_0.jpg", "source": "pexels", "url": "..."},
    {"path": "projects/myvideo/images/slide_01_1.jpg", "source": "pexels", "url": "..."}
  ]
}
```

## 工作流

对每个缺少 `image` 字段的片段：

1. 使用片段的 `keywords` 字段。若也没有 keywords，则根据 `text` 和项目 `topic` 生成 2-4 个关键词。
2. 为每个片段执行脚本，保存到 `projects/{name}/images/slide_{index:02d}/`。
3. 取返回结果中的第一张图片作为该片段的图片（若下载了多张且质量重要，可询问用户）。
4. 更新 `project.yaml` 中对应片段的 `image` 路径。

## 关键词技巧

- 使用 2-4 个具体名词，避免动词和虚词。
- 组合「主体 + 场景 + 风格」：`"故宫 宫殿 传统建筑"`、`"日落 山脉 风景"`。
- 抽象话题用具体视觉形象替代：不用 `"繁荣"`，改用 `"城市 夜景 灯光"`。
