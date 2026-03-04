---
name: generate-tts
description: 使用 edge-tts（免费）、OpenAI TTS 或 Fish Audio TTS 将旁白文案转换为音频文件。当片段缺少 audio 字段、用户要求生成配音、或需要将脚本合成语音时使用。
---

# generate-tts

将文本转换为 MP3 音频文件，并输出实际音频时长。

## 脚本用法

```bash
python .cursor/skills/generate-tts/scripts/tts.py \
  --text "要朗读的文案" \
  --output 输出音频路径.mp3 \
  [--voice 音色名称] \
  [--provider edge-tts|openai|fish] \
  [--config config.yaml]
```

**参数说明：**
- `--text` — 旁白文案（用引号包裹）
- `--output` — 输出 MP3 路径（目录不存在时自动创建）
- `--voice` — TTS 音色名（覆盖 config 中该语言的默认音色）
- `--provider` — `edge-tts`、`openai` 或 `fish`（覆盖 config 设置）
- `--config` — `config.yaml` 路径（默认：当前目录下的 `config.yaml`）

**标准输出（JSON）：**
```json
{"path": "projects/myvideo/audio/slide_01.mp3", "duration_seconds": 8.4}
```

## 工作流

对每个缺少 `audio` 字段的片段：

1. 确认片段有 `text` 字段，没有则先生成文案。
2. 确定音色：片段级 `tts_voice` → 项目级 `tts_voice` → config 中 `tts_voices[language]`。
3. 执行脚本，保存到 `projects/{name}/audio/slide_{index:02d}.mp3`。
4. 更新 `project.yaml`：将返回的路径写入 `audio`，将 `duration_seconds` 写入 `duration`。

## 音色选择

**edge-tts（免费，默认）：**
- 中文：`zh-CN-XiaoxiaoNeural`（默认，温柔女声）、`zh-CN-YunxiNeural`（男声）、`zh-CN-YunyangNeural`（播音男声）
- 英文：`en-US-AriaNeural`（默认）、`en-US-GuyNeural`、`en-GB-SoniaNeural`

**OpenAI TTS：**
- 音色：`alloy`、`echo`、`fable`、`onyx`、`nova`、`shimmer`
- 使用前需在 `config.yaml` 中设置 `openai_api_key`。

**Fish Audio TTS：**
- `--voice` 传入 Fish Audio 的 `reference_id`（声音模型 ID，可在 [fish.audio](https://fish.audio) 平台找到）
- 不传 `--voice` 则使用平台默认声音（S1 模型）
- 使用前需在 `config.yaml` 中设置 `fish_api_key`，或设置环境变量 `FISH_API_KEY`
- `config.yaml` 中可用 `fish_tts_voice` 设置项目级默认 reference_id

**config.yaml 示例：**
```yaml
tts_provider: fish           # 默认 provider（edge-tts / openai / fish）
fish_api_key: "your_key"     # Fish Audio API Key
fish_tts_voice: "8ef4a238714b45718ce04243307c57a7"  # 可选，voice reference_id
```

## 文案长度说明

- edge-tts 无硬性字符限制，超长文本会流式处理。
- OpenAI TTS：每次最多 4096 个字符。更长的文本会自动按句子边界拆分，再将各段音频拼接。
- Fish Audio TTS：单次请求无严格字符限制，建议控制在合理长度内。
