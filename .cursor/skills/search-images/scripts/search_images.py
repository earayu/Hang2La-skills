"""
search_images.py — 使用必应（Bing）图片搜索下载图片素材，无需 API Key。

用法：
    python search_images.py --keywords "故宫 宫殿" --output projects/myvideo/images/slide_01/
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
import yaml


def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        for parent in Path.cwd().parents:
            candidate = parent / "config.yaml"
            if candidate.exists():
                path = candidate
                break
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _make_session() -> requests.Session:
    """Create a session that bypasses system proxy."""
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })
    return s


def search_bing(keywords: str, count: int, orientation: str) -> list[dict]:
    """
    Search images via Bing Images (no API key required).
    Accessible in mainland China.
    """
    session = _make_session()

    filter_parts = []
    if orientation == "landscape":
        filter_parts.append("filterui:aspect-wide")
    elif orientation == "portrait":
        filter_parts.append("filterui:aspect-tall")

    params = {
        "q": keywords,
        "count": min(count * 6, 50),
        "mkt": "en-US",
        "adlt": "moderate",
        "first": 1,
    }
    if filter_parts:
        params["qft"] = "+".join(filter_parts)

    try:
        resp = session.get("https://www.bing.com/images/search", params=params, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[search-images] Bing request error: {e}", file=sys.stderr)
        return []

    # murl is the original media URL, encoded in the search result HTML
    murls = re.findall(r'murl&quot;:&quot;(https?://[^&<"]+?)&quot;', resp.text)
    if not murls:
        # Fallback pattern for different HTML encoding
        murls = re.findall(r'"murl":"(https?://[^"]+)"', resp.text)

    seen = set()
    results = []
    for url in murls:
        if url in seen:
            continue
        seen.add(url)
        results.append({"url": url, "source": "bing", "title": ""})

    print(f"[search-images] Bing returned {len(results)} candidates for: {keywords}", file=sys.stderr)
    return results


def search_pexels(keywords: str, count: int, orientation: str, api_key: str) -> list[dict]:
    """Fallback: search Pexels if API key is configured."""
    if not api_key or api_key in ("YOUR_PEXELS_KEY", ""):
        return []
    session = _make_session()
    try:
        resp = session.get(
            "https://api.pexels.com/v1/search",
            params={"query": keywords, "per_page": count, "orientation": orientation},
            headers={"Authorization": api_key},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        photos = resp.json().get("photos", [])
        return [{"url": p["src"]["large"], "source": "pexels", "title": p.get("photographer", "")} for p in photos]
    except Exception as e:
        print(f"[search-images] Pexels error: {e}", file=sys.stderr)
        return []


def download_images(candidates: list[dict], output_dir: Path, count: int) -> list[dict]:
    """Download images, automatically skipping corrupt or truncated files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    session = _make_session()
    session.headers["Referer"] = "https://www.bing.com/"

    downloaded = []
    for candidate in candidates:
        if len(downloaded) >= count:
            break

        url = candidate["url"]
        raw_ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        ext = raw_ext if raw_ext in ("jpg", "jpeg", "png", "webp") else "jpg"
        dest = output_dir / f"photo_{len(downloaded):02d}.{ext}"

        try:
            resp = session.get(url, timeout=20, stream=True)
            resp.raise_for_status()

            data = b"".join(resp.iter_content(8192))
            if len(data) < 5_000:
                print(f"[search-images] Skipping tiny file ({len(data)}B): {url[:60]}", file=sys.stderr)
                continue

            dest.write_bytes(data)

            # Integrity check with PIL
            try:
                from PIL import Image
                img = Image.open(dest)
                img.load()
            except Exception:
                print(f"[search-images] Corrupt image, skipping: {dest.name}", file=sys.stderr)
                dest.unlink(missing_ok=True)
                continue

            downloaded.append({"path": str(dest), "source": candidate.get("source", "bing"), "url": url})
            print(f"[search-images] OK  {dest.name}  ({len(data)//1024}KB)", file=sys.stderr)

        except Exception as e:
            print(f"[search-images] Download failed {url[:60]}: {e}", file=sys.stderr)

        time.sleep(0.1)

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="搜索并下载图片素材（必应，无需 API Key）。")
    parser.add_argument("--keywords", required=True, help="以空格分隔的搜索关键词")
    parser.add_argument("--output", required=True, help="图片保存目录")
    parser.add_argument("--count", type=int, default=None, help="下载数量")
    parser.add_argument("--orientation", default=None, choices=["landscape", "portrait", "square"])
    parser.add_argument("--config", default="config.yaml", help="config.yaml 路径")
    args = parser.parse_args()

    config = load_config(args.config)
    count = args.count or config.get("images_per_slide", 3)
    orientation = args.orientation or config.get("image_orientation", "landscape")
    pexels_key = config.get("pexels_api_key", "")

    output_dir = Path(args.output)

    # Primary: Bing (free, no API key, accessible in mainland China)
    candidates = search_bing(args.keywords, count, orientation)

    # Fallback: Pexels (if key is configured and Bing got too few)
    if len(candidates) < count and pexels_key:
        print("[search-images] Falling back to Pexels...", file=sys.stderr)
        candidates += search_pexels(args.keywords, count - len(candidates), orientation, pexels_key)

    if not candidates:
        print(json.dumps({"error": "未找到图片候选。", "images": []}), flush=True)
        sys.exit(1)

    downloaded = download_images(candidates, output_dir, count)

    if not downloaded:
        print(json.dumps({"error": "所有图片下载失败。", "images": []}), flush=True)
        sys.exit(1)

    print(json.dumps({"images": downloaded}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
