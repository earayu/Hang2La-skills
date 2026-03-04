"""
tts.py — 使用 edge-tts、OpenAI TTS 或 Fish Audio TTS 将文本转换为语音。

用法：
    python tts.py --text "你好，世界" --output projects/myvideo/audio/slide_01.mp3
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import yaml


def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        for parent in [Path.cwd()] + list(Path.cwd().parents):
            candidate = parent / "config.yaml"
            if candidate.exists():
                path = candidate
                break
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_audio_duration(path: str) -> float:
    """用 moviepy 获取音频时长（秒）。"""
    try:
        from moviepy import AudioFileClip
        with AudioFileClip(path) as clip:
            return round(clip.duration, 2)
    except Exception:
        return 0.0


async def run_edge_tts(text: str, voice: str, output: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice)
    output.parent.mkdir(parents=True, exist_ok=True)
    await communicate.save(str(output))


def run_openai_tts(text: str, voice: str, model: str, api_key: str, output: Path) -> None:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    output.parent.mkdir(parents=True, exist_ok=True)

    # 超过 4096 字符时按句子边界拆分，分段合成后拼接
    chunks = split_text(text, max_chars=4096)
    if len(chunks) == 1:
        response = client.audio.speech.create(model=model, voice=voice, input=text)
        output.write_bytes(response.content)
    else:
        import tempfile
        chunk_files = []
        for i, chunk in enumerate(chunks):
            response = client.audio.speech.create(model=model, voice=voice, input=chunk)
            tmp = Path(tempfile.mktemp(suffix=".mp3"))
            tmp.write_bytes(response.content)
            chunk_files.append(tmp)
        concatenate_mp3(chunk_files, output)
        for f in chunk_files:
            f.unlink(missing_ok=True)


def split_text(text: str, max_chars: int = 4096) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = text.replace("。", "。\n").replace(". ", ". \n").split("\n")
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) <= max_chars:
            current += sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks or [text]


def concatenate_mp3(files: list[Path], output: Path) -> None:
    from moviepy import AudioFileClip, concatenate_audioclips
    clips = [AudioFileClip(str(f)) for f in files]
    combined = concatenate_audioclips(clips)
    combined.write_audiofile(str(output), logger=None)
    for c in clips:
        c.close()
    combined.close()


def _find_http_proxy() -> str | None:
    """Detect a local HTTP proxy port from env vars or common MonoCloud/Clash ports."""
    for var in ("https_proxy", "http_proxy", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        val = os.environ.get(var, "")
        if val and not val.startswith("socks"):
            return val
    # Fall back to scanning well-known local proxy ports
    import socket
    for port in (8118, 7890, 8080, 1087, 10809):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return f"http://127.0.0.1:{port}"
        except OSError:
            pass
    return None


def run_fish_tts(text: str, voice: str | None, api_key: str, output: Path) -> None:
    """Call Fish Audio TTS API via curl subprocess (avoids Python proxy CONNECT issues)."""
    import json as _json
    import subprocess

    output.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {"text": text, "format": "mp3"}
    if voice:
        payload["reference_id"] = voice

    cmd = [
        "curl", "-s", "-X", "POST", "https://api.fish.audio/v1/tts",
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-H", "model: s1",
        "-d", _json.dumps(payload, ensure_ascii=False),
        "-o", str(output),
        "-w", "%{http_code}",
        "--max-time", "120",
    ]
    proxy = _find_http_proxy()
    if proxy:
        cmd += ["-x", proxy]

    result = subprocess.run(cmd, capture_output=True, text=True)
    http_code = result.stdout.strip()
    if http_code != "200":
        stderr_hint = result.stderr.strip()
        raise RuntimeError(
            f"Fish Audio API error HTTP {http_code}. stderr: {stderr_hint}"
        )


def main():
    parser = argparse.ArgumentParser(description="文本转语音合成。")
    parser.add_argument("--text", required=True, help="待合成的旁白文案")
    parser.add_argument("--output", required=True, help="输出 MP3 路径")
    parser.add_argument("--voice", default=None, help="TTS 音色名称")
    parser.add_argument("--provider", default=None, choices=["edge-tts", "openai", "fish"])
    parser.add_argument("--config", default="config.yaml", help="config.yaml 路径")
    args = parser.parse_args()

    config = load_config(args.config)
    provider = args.provider or config.get("tts_provider", "edge-tts")
    output = Path(args.output)

    # voice priority: --voice arg > config tts_voice
    voice = args.voice or config.get("tts_voice") or None

    if provider == "openai":
        api_key = config.get("openai_api_key", "") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            print("[tts] 未设置 openai_api_key，请在 config.yaml 或环境变量 OPENAI_API_KEY 中配置。", file=sys.stderr)
            sys.exit(1)
        model = config.get("openai_tts_model", "tts-1")
        run_openai_tts(args.text, voice or "nova", model, api_key, output)
    elif provider == "fish":
        api_key = config.get("fish_api_key", "") or os.environ.get("FISH_API_KEY", "")
        if not api_key:
            print("[tts] 未设置 fish_api_key，请在 config.yaml 中添加 fish_api_key 或设置环境变量 FISH_API_KEY。", file=sys.stderr)
            sys.exit(1)
        run_fish_tts(args.text, voice, api_key, output)
    else:
        asyncio.run(run_edge_tts(args.text, voice or "zh-CN-XiaoxiaoNeural", output))

    duration = get_audio_duration(str(output))
    print(json.dumps({"path": str(output), "duration_seconds": duration}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
