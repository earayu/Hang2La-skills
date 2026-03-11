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

## 常见错误与修复

| 错误信息 | 原因 | 修复方法 |
|---------|------|---------|
| `ffmpeg not found` / `FileNotFoundError: ffmpeg` | 系统未安装 ffmpeg | macOS: `brew install ffmpeg`；Ubuntu: `sudo apt install ffmpeg` |
| `ModuleNotFoundError: No module named 'moviepy'` | Python 依赖未安装 | 在项目根目录执行 `uv sync`（或 `pip install moviepy pillow numpy`） |
| `FileNotFoundError: [image path]` | project.yaml 中的图片路径不存在 | 确认 `image` 字段路径正确，或先运行 search-images 补全 |
| `FileNotFoundError: [audio path]` | project.yaml 中的音频路径不存在 | 确认 `audio` 字段路径正确，或先运行 generate-tts 补全 |
| `PIL.UnidentifiedImageError` | 图片文件损坏或格式不支持 | 删除该图片，重新运行 search-images 下载 |
| 视频合成卡住不动 | 某段音频时长为 0 或 duration 字段错误 | 检查 project.yaml 中所有 `duration` 字段，值应大于 0 |
| 输出视频无声音 | ffmpeg 版本过旧 | 升级 ffmpeg：`brew upgrade ffmpeg` |
