---
name: generate-tts
description: 使用 edge-tts（免费）、OpenAI TTS 或 Fish Audio TTS 将旁白文案转换为音频文件。当片段缺少 audio 字段、用户要求生成配音、或需要将脚本合成语音时使用。
---

# generate-tts

将文本转换为 MP3 音频文件，并输出实际音频时长。

## 脚本用法

```bash
python skills/generate-tts/scripts/tts.py \
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
2. 确定音色：`--voice` 参数 → config 中 `tts_voice`。通常只传 `--config`，音色由 config 统一管理。
3. 执行脚本，保存到 `projects/{name}/audio/slide_{index:02d}.mp3`。
4. 更新 `project.yaml`：将返回的路径写入 `audio`，将 `duration_seconds` 写入 `duration`。

## 音色选择

**edge-tts（免费，默认）：**
- 中文：`zh-CN-XiaoxiaoNeural`（温柔女声）、`zh-CN-YunxiNeural`（男声）、`zh-CN-YunyangNeural`（播音男声）
- 英文：`en-US-AriaNeural`、`en-US-GuyNeural`、`en-GB-SoniaNeural`

**OpenAI TTS：**
- 音色：`alloy`、`echo`、`fable`、`onyx`、`nova`、`shimmer`
- 使用前需在 `config.yaml` 中设置 `openai_api_key`。

**Fish Audio TTS：**
- `tts_voice` 填写 Fish Audio 的 `reference_id`（在 [fish.audio](https://fish.audio) 平台声音模型页面 URL 中获取）
- 不填则使用平台默认声音（S1 模型）
- 使用前需在 `config.yaml` 中设置 `fish_api_key`，或设置环境变量 `FISH_API_KEY`

**config.yaml 示例：**
```yaml
tts_provider: fish           # 默认 provider（edge-tts / openai / fish）
fish_api_key: "your_key"     # Fish Audio API Key
tts_voice: "2d25cc5dfbdc45cb996d2b200a6b72a1"  # 音色（edge-tts 填音色名，Fish Audio 填 reference_id）
```

## 文案长度说明

- edge-tts 无硬性字符限制，超长文本会流式处理。
- OpenAI TTS：每次最多 4096 个字符。更长的文本会自动按句子边界拆分，再将各段音频拼接。
- Fish Audio TTS：单次请求无严格字符限制，建议控制在合理长度内。

## 常见错误与修复

| 错误信息 | 原因 | 修复方法 |
|---------|------|---------|
| `ModuleNotFoundError: No module named 'edge_tts'` | Python 依赖未安装 | 在项目根目录执行 `uv sync`（或 `pip install edge-tts`） |
| `edge-tts: connect call failed` / `aiohttp.ClientConnectorError` | 网络问题，edge-tts 需要访问微软服务器 | 检查网络，必要时尝试切换到 `--provider openai` |
| `AuthenticationError` / `Incorrect API key` | OpenAI API Key 无效 | 检查 `config.yaml` 中的 `openai_api_key` |
| `fish_api_key not set` | Fish Audio Key 缺失 | 在 `config.yaml` 中添加 `fish_api_key` 或设置环境变量 `FISH_API_KEY` |
| `Voice not found` | 音色名称错误 | edge-tts 运行 `python -m edge_tts --list-voices` 查看所有可用音色 |
| 生成的音频只有 0 秒 | 文本为空或只有空白字符 | 确认 `project.yaml` 对应片段的 `text` 字段不为空 |
