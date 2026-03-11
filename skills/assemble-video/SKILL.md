---
name: assemble-video
description: 读取 project.yaml，将排行榜图片和音频合成为最终 MP4 视频。当所有选手的图片和音频均已就绪、或用户要求渲染/导出/完成视频时使用。
---

# assemble-video

读取 `project.yaml`（`type: "tierlist"`），生成"从夯到拉"排行榜动画视频。

## 脚本用法

```bash
python skills/assemble-video/scripts/assemble_tierlist.py \
  --project projects/myvideo/project.yaml \
  --output  projects/myvideo/output/video.mp4 \
  [--config config.yaml]
```

**标准输出（JSON）：**
```json
{"path": "projects/myvideo/output/video.mp4", "duration_seconds": 245.7}
```

## 视频结构

1. **片头**（intro）：排行榜背景 + 旁白音频
2. **逐一处理每位选手**：
   - 解说阶段：选手大图居中展示 + 旁白音频
   - 入榜动画（0.6 秒）：图片从中央缩小飞入对应档位行，同一档位的后续选手排列到右侧
3. **片尾**（outro）：完整排行榜 + 旁白音频

## 前置条件

`project.yaml` 中：
- `type: "tierlist"`
- 每位 `contestant` 均有 `image`、`audio`、`tier` 字段
- `intro` 和 `outro` 均有 `audio` 字段

若有字段缺失，请先运行 **search-images** 和 **generate-tts** 补全。

## 资产

排行榜背景图（五档）：`skills/assemble-video/assets/tierlist_bg.png`
