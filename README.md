# Hang2La-skills

AI 驱动的视频生成流水线。只需提供一个话题，让 Agent 自动完成所有工作；也可以自行提供素材，实现精细控制。

---

## 工作原理

Agent（Claude / Cursor）读取 `.cursor/skills/` 中的技能，理解自己能做什么，再通过 Python 脚本执行固定任务：

```
话题 / 素材
      ↓
[Agent] 撰写旁白脚本 + 搜图关键词
      ↓
[search-images]  从 Pexels / Unsplash 下载图片
      ↓
[generate-tts]   将旁白转换为音频
      ↓
[process-images] 统一图片尺寸和比例
      ↓
[assemble-video] 合成最终 MP4
```

---

## 安装

### 1. 安装依赖

```bash
uv sync
```

系统依赖（视频编码必须）：
```bash
brew install ffmpeg   # macOS
# apt install ffmpeg  # Ubuntu
```

添加新依赖包：
```bash
uv add <包名>
```

### 2. 配置 API Key

复制模板并填写你的密钥：

```bash
cp config.template.yaml config.yaml
```

`config.yaml` 已加入 `.gitignore`，密钥不会提交到仓库。

最少必填：
- `pexels_api_key` — 免费申请：[pexels.com/api](https://www.pexels.com/api/)
- 其余均有免费默认值（edge-tts 无需 API Key）

---

## 使用方式

### 全自动 — 只需给出话题

在 Cursor 中打开本项目（或在 Claude 中加载 skills），直接说：

> "帮我做一个关于故宫历史的视频，约 90 秒。"

Agent 会读取 `make-video` 技能，自动完成后续所有步骤。

### 半自动 — 提供部分素材

在项目目录中预先填写 `project.yaml`，然后告诉 Agent：

> "我在 projects/gugong/ 下有一个 project.yaml，请帮我完成视频。"

Agent 会自动补全缺失字段（图片、文案、音频），然后合成视频。

### 手动合成 — 自己提供全部素材

写好完整的 `project.yaml`，告诉 Agent：

> "使用 projects/gugong/project.yaml 合成视频。"

---

## 目录结构

```
Hang2La-skills/
├── .cursor/skills/         # Agent 技能文件（Claude / Cursor 读取）
│   ├── make-video/         # 主编排技能
│   ├── search-images/      # 搜图技能
│   ├── generate-tts/       # 语音合成技能
│   ├── process-images/     # 图片预处理技能
│   └── assemble-video/     # 视频合成技能
├── projects/               # 每个视频项目一个子目录
│   └── {项目名}/
│       ├── project.yaml    # 项目配置（Agent 创建和维护）
│       ├── images/         # 原始图片（下载或用户提供）
│       ├── audio/          # 生成的音频文件
│       └── output/         # 最终视频
├── config.template.yaml    # 配置模板（提交到仓库）
├── config.yaml             # 本地配置，含真实 API Key（已 gitignore）
└── pyproject.toml
```

---

## project.yaml 字段说明

此文件由 Agent 创建和维护，也可以手动编写。

```yaml
# ── 必填 ────────────────────────────────────────────────────
name: "my-video"          # 项目名，作为输出文件名前缀
topic: "故宫的历史"         # 主题（Agent 生成内容时使用）
language: zh              # zh | en（决定 TTS 音色选择）
style: documentary        # 风格提示：documentary | storytelling | educational

# ── 可选覆盖（未填则使用 config.yaml 默认值）────────────────
resolution: "1920x1080"   # 输出分辨率
fps: 24
tts_voice: zh-CN-XiaoxiaoNeural   # 覆盖全局 TTS 音色
transition_duration: 0.5           # 幻灯片间淡入淡出时长（秒）

# ── 幻灯片列表 ───────────────────────────────────────────────
slides:
  - index: 1
    # keywords: search-images 用于搜索图片的关键词。
    # 若不填且 image 也不填，Agent 会根据 text 自动生成关键词。
    keywords: "故宫 宫墙 历史"

    # text: 本片段的旁白文案。
    # 若不填，Agent 会根据图片和主题自动生成。
    text: "故宫，又称紫禁城，始建于明代永乐年间，历经六百年风雨。"

    # image: 相对于项目目录的图片路径。
    # 若不填，search-images 会用 keywords 自动下载。
    image: images/slide_01.jpg

    # audio: 相对于项目目录的音频路径。
    # 若不填，generate-tts 会用 text 自动生成。
    audio: audio/slide_01.mp3

    # duration: 音频时长（秒），TTS 生成后自动填入。
    duration: 8.4

  - index: 2
    keywords: "太和殿 金銮殿"
    # text / image / audio 均未填 → Agent 全部自动处理
```

**规则：**
- 任何字段均可省略，Agent 或脚本会自动补全。
- `image` 和 `audio` 路径相对于项目目录（如 `projects/gugong/`）。
- 流水线执行完毕后，所有字段都应被填满。

---

## config.yaml 参数说明

完整注释版请查看 `config.template.yaml`。核心参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pexels_api_key` | — | 搜图必填 |
| `unsplash_access_key` | — | 可选备用图片来源 |
| `openai_api_key` | — | 可选，仅 OpenAI TTS 需要 |
| `tts_provider` | `edge-tts` | `edge-tts`（免费）或 `openai` |
| `tts_voices.zh` | `zh-CN-XiaoxiaoNeural` | 默认中文音色 |
| `tts_voices.en` | `en-US-AriaNeural` | 默认英文音色 |
| `openai_tts_model` | `tts-1` | `tts-1` 或 `tts-1-hd` |
| `openai_tts_voice` | `nova` | OpenAI 音色名 |
| `default_resolution` | `1920x1080` | 输出分辨率 |
| `default_fps` | `24` | 帧率 |
| `default_slides_count` | `8` | Agent 自动规划时的片段数 |
| `default_language` | `zh` | 默认语言 |
| `transition_duration` | `0.5` | 幻灯片间淡入淡出时长（秒） |

---

## 可用 TTS 音色

### edge-tts（免费，无需 API Key）

中文：
- `zh-CN-XiaoxiaoNeural` — 温柔女声（推荐）
- `zh-CN-YunxiNeural` — 男声
- `zh-CN-YunyangNeural` — 播音男声
- `zh-TW-HsiaoChenNeural` — 台湾普通话女声

英文：
- `en-US-AriaNeural` — 对话女声（推荐）
- `en-US-GuyNeural` — 男声
- `en-GB-SoniaNeural` — 英式英语女声

查看所有可用音色：
```bash
python -m edge_tts --list-voices
```

### OpenAI TTS

音色：`alloy`、`echo`、`fable`、`onyx`、`nova`、`shimmer`
模型：`tts-1`（快速）、`tts-1-hd`（高音质）
