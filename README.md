# 🏆 Hang2La — AI Tier List Video Generator

> **Give it a topic. Get a ready-to-post ranking video.**
> Powered by LLMs (Claude / GPT) + edge-tts + ffmpeg.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Free to Use](https://img.shields.io/badge/TTS-Free%20%28edge--tts%29-green.svg)](https://github.com/rany2/edge-tts)

---

## 什么是 Hang2La？

**"夯到拉"** 是一种风靡中文互联网的锐评排行榜格式——把一组事物分为从「夯（顶级）」到「拉（垫底）」的几个档次，配上毒舌点评，一句话戳穿本质。

**Hang2La** 把这件事交给 AI Agent 全自动完成：

1. 你只需说出一个话题
2. Agent 自动撰写每个选手的锐评旁白
3. 自动搜图、自动配音、自动合成视频
4. 输出一个可以直接发布的 1080p MP4

```
你说: "帮我做一个 A股主要指数的夯到拉排行榜视频"
           ↓
    Agent 撰写剧本 + 搜图关键词
           ↓
    [search-images]  DuckDuckGo 搜图，无需 API Key
           ↓
    [generate-tts]   edge-tts 配音，完全免费
           ↓
    [assemble-video] ffmpeg 合成带动画的 MP4
           ↓
你得到: 一个可以直接发布的排行榜视频 🎬
```

---

## Demo

### 太阳系九大行星·夯到拉排名

> 完整示例见 [`examples/solar-system-planets/`](examples/solar-system-planets/)，含所有图片和音频素材，可直接运行合成视频。

**旁白节选 · 冥王星（拉完了档）：**

> *"2006年，国际天文联合会开会，把冥王星的行星资格给撤了，降级为'矮行星'。*
> *想象一下，你上班几十年，突然有一天公司开会宣布你不是员工了，你是实习生，这就是冥王星的遭遇。*
> *…不好意思，有没有爱心都改变不了被除名的结局，拉完了。"*

---

## 快速开始

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/earayu/Hang2La-skills.git
cd Hang2La-skills

# 安装 Python 依赖（推荐使用 uv）
uv sync
# 或者: pip install -r requirements.txt

# 安装 ffmpeg（视频合成必须）
brew install ffmpeg        # macOS
# sudo apt install ffmpeg  # Ubuntu/Debian
```

### 2. 配置（可选）

```bash
cp config.template.yaml config.yaml
# 用编辑器打开 config.yaml，填写你的 API Key（最少只需要 pexels_api_key）
```

> **零配置即可运行**：默认使用 edge-tts（完全免费，无需 API Key）+ DuckDuckGo 搜图。
> 想要更高质量配音可以配置 OpenAI TTS；想要更多图片来源可以配置 Pexels。

### 3. 运行示例

在 [Cursor](https://cursor.sh) 中打开本项目，然后直接说：

```
使用 examples/solar-system-planets/project.yaml 合成视频。
```

Agent 会调用 `assemble-video` skill 在 `examples/solar-system-planets/output/` 生成最终 MP4。

### 4. 创建你自己的视频

```
帮我做一个"国内主要互联网大厂·从夯到拉排行榜"视频，大约 3 分钟。
```

Agent 会自动规划选手列表、撰写锐评脚本、搜图、配音、合成视频，全程无需人工干预。

---

## 目录结构

```
Hang2La-skills/
├── skills/                      # Agent 技能文件（核心，框架无关）
│   ├── make-tierlist/           # 主编排技能：从话题到视频全流程
│   ├── search-images/           # 搜图技能（DuckDuckGo，无需 Key）
│   ├── generate-tts/            # 语音合成（edge-tts / OpenAI / Fish Audio）
│   └── assemble-video/          # 视频合成（ffmpeg）
├── examples/                    # 可直接运行的完整示例
│   └── solar-system-planets/    # 太阳系行星排行榜（含图片+音频）
│       ├── project.yaml
│       ├── materials/           # 原始图片
│       └── audio/               # 生成的音频（可用 generate-tts 重新生成）
├── projects/                    # 你的本地项目（已 gitignore）
├── config.template.yaml         # 配置模板
└── pyproject.toml
```

> **编辑器集成**：Cursor 用户可在 `.cursor/skills` 创建软链接指向 `skills/`，即可享受 Agent Skills 自动注入功能（本地配置，不提交到 git）。

---

## project.yaml 结构

`project.yaml` 是整个流水线的核心配置文件，由 Agent 创建和维护，也可以手动编写。

```yaml
name: "my-tierlist"
type: "tierlist"
topic: "国产操作系统从夯到拉排名"
language: zh

tiers:
  - id: "hang"
    label: "夯"
  - id: "top"
    label: "顶级"
  - id: "npc"
    label: "NPC"
  - id: "la"
    label: "拉完了"

style: "幽默犀利，互联网口语，偶尔夹杂科普"

contestants:
  - index: 1
    name: "鸿蒙OS"
    keywords: "鸿蒙 HarmonyOS 华为"
    tier: "hang"
    # text / image / audio 均可省略，Agent 会自动补全
```

**所有字段均可省略，Agent 会根据 `topic` 和 `style` 自动填充缺失内容。**

---

## TTS 配置

| 方案 | 费用 | 音质 | 配置 |
|------|------|------|------|
| edge-tts（默认） | **免费** | 良好 | 无需 API Key |
| OpenAI TTS | 按量付费 | 优秀 | 需要 `openai_api_key` |
| Fish Audio | 按量付费 | 出色（可克隆声音） | 需要 `fish_audio_api_key` |

常用中文音色（edge-tts）：
- `zh-CN-XiaoxiaoNeural` — 温柔女声（默认推荐）
- `zh-CN-YunxiNeural` — 活泼男声
- `zh-CN-YunyangNeural` — 新闻播音腔

查看全部音色：
```bash
python -m edge_tts --list-voices
```

---

## 适合做什么话题？

理论上任何「一组事物的横向对比」都可以做，越有争议越好：

- 🏙️ 城市排行 — "国内新一线城市从夯到拉"
- 🍜 美食排行 — "中国八大菜系哪个最能打"
- 📱 产品排行 — "国内主要手机品牌夯到拉"
- 🎬 影视排行 — "漫威电影宇宙各阶段实力对比"
- 🖥️ 技术排行 — "主流编程语言从夯到拉"
- 🌍 地理排行 — "世界七大洲颜值与宜居度排名"

---

## 核心依赖

- [edge-tts](https://github.com/rany2/edge-tts) — 微软 TTS，完全免费
- [ffmpeg](https://ffmpeg.org/) — 视频合成引擎
- [Pillow](https://pillow.readthedocs.io/) — 图片处理
- [uv](https://github.com/astral-sh/uv) — Python 包管理

---

## License

MIT
