"""
search_images.py — 使用 DuckDuckGo 图片搜索下载图片素材，无需 API Key。
DuckDuckGo 对中文关键词效果极佳；若触发限速则自动降级到 Bing 抓取。

用法：
    python search_images.py --keywords "凡人修仙传 银月" --output projects/myvideo/images/slide_01/
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
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return s


def search_duckduckgo(keywords: str, max_candidates: int, retries: int = 3) -> list[dict]:
    """
    Search images via DuckDuckGo (no API key, great for Chinese keywords).
    Retries on rate-limit errors with exponential backoff.
    """
    for attempt in range(retries):
        try:
            # Support both package names (ddgs is the new name)
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore

            results = list(DDGS().images(keywords, max_results=max_candidates))
            if results:
                print(f"[search-images] DuckDuckGo: {len(results)} candidates for: {keywords}", file=sys.stderr)
                return [
                    {"url": r["image"], "source": "duckduckgo", "title": r.get("title", "")}
                    for r in results
                ]
            print(f"[search-images] DuckDuckGo returned 0 results", file=sys.stderr)
            return []

        except Exception as e:
            err_str = str(e).lower()
            if "ratelimit" in err_str or "403" in err_str or "no results" in err_str:
                wait = 3 * (2 ** attempt)
                print(f"[search-images] DuckDuckGo rate-limited (attempt {attempt+1}/{retries}), waiting {wait}s…", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"[search-images] DuckDuckGo error: {e}", file=sys.stderr)
                break

    return []


def search_bing_fallback(keywords: str, max_candidates: int) -> list[dict]:
    """Fallback: scrape Bing Images when DuckDuckGo is unavailable."""
    session = _make_session()
    params = {
        "q": keywords,
        "count": min(max_candidates, 50),
        "mkt": "zh-CN",
        "adlt": "moderate",
        "first": 1,
    }
    try:
        resp = session.get("https://www.bing.com/images/search", params=params, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[search-images] Bing fallback error: {e}", file=sys.stderr)
        return []

    murls = re.findall(r'murl&quot;:&quot;(https?://[^&<"]+?)&quot;', resp.text)
    if not murls:
        murls = re.findall(r'"murl":"(https?://[^"]+)"', resp.text)

    seen, results = set(), []
    for url in murls:
        if url not in seen:
            seen.add(url)
            results.append({"url": url, "source": "bing", "title": ""})

    print(f"[search-images] Bing fallback: {len(results)} candidates for: {keywords}", file=sys.stderr)
    return results


def download_images(candidates: list[dict], output_dir: Path, count: int) -> list[dict]:
    """Download images, skipping webp and corrupt files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    session = _make_session()
    session.headers["Referer"] = "https://www.bing.com/"

    downloaded = []
    for candidate in candidates:
        if len(downloaded) >= count:
            break

        url = candidate["url"]

        # Skip webp by URL
        raw_ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if raw_ext == "webp":
            print(f"[search-images] Skipping webp URL: {url[:70]}", file=sys.stderr)
            continue

        ext = raw_ext if raw_ext in ("jpg", "jpeg", "png") else "jpg"
        dest = output_dir / f"photo_{len(downloaded):02d}.{ext}"

        try:
            resp = session.get(url, timeout=20, stream=True)
            resp.raise_for_status()

            # Skip webp by Content-Type
            if "webp" in resp.headers.get("Content-Type", ""):
                print(f"[search-images] Skipping webp Content-Type: {url[:70]}", file=sys.stderr)
                continue

            data = b"".join(resp.iter_content(8192))
            if len(data) < 5_000:
                print(f"[search-images] Skipping tiny file ({len(data)}B): {url[:70]}", file=sys.stderr)
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

            downloaded.append({
                "path": str(dest),
                "source": candidate.get("source", "duckduckgo"),
                "url": url,
                "title": candidate.get("title", ""),
            })
            size_kb = len(data) // 1024
            title_preview = candidate.get("title", "")[:40]
            print(f"[search-images] OK  {dest.name}  ({size_kb}KB)  {title_preview}", file=sys.stderr)

        except Exception as e:
            print(f"[search-images] Download failed {url[:70]}: {e}", file=sys.stderr)

        time.sleep(0.1)

    return downloaded


def save_search_results(output_dir: Path, keywords: str, downloaded: list[dict]) -> None:
    """Save search metadata as search_results.json for future reference."""
    import datetime
    record = {
        "keywords": keywords,
        "searched_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "images": [
            {
                "filename": Path(d["path"]).name,
                "title": d.get("title", ""),
                "url": d.get("url", ""),
                "source": d.get("source", ""),
            }
            for d in downloaded
        ],
    }
    meta_path = output_dir / "search_results.json"
    meta_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(f"[search-images] Metadata saved → {meta_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="搜索并下载图片素材（DuckDuckGo 优先，无需 API Key）。")
    parser.add_argument("--keywords", required=True,
                        help="搜索关键词，优先使用中文（如 '凡人修仙传 银月'）效果更好")
    parser.add_argument("--output", required=True, help="图片保存目录")
    parser.add_argument("--count", type=int, default=None,
                        help="下载数量，默认由 config 中 images_per_slide 决定（通常为 5）")
    parser.add_argument("--config", default="config.yaml", help="config.yaml 路径")
    args = parser.parse_args()

    config = load_config(args.config)
    count = args.count or config.get("images_per_slide", 5)
    output_dir = Path(args.output)

    # Primary: DuckDuckGo (best for Chinese keywords)
    candidates = search_duckduckgo(args.keywords, count * 8)

    # Fallback: Bing scraping
    if not candidates:
        print("[search-images] Falling back to Bing…", file=sys.stderr)
        candidates = search_bing_fallback(args.keywords, count * 8)

    if not candidates:
        print(json.dumps({"error": "未找到图片候选。", "images": []}), flush=True)
        sys.exit(1)

    downloaded = download_images(candidates, output_dir, count)

    if not downloaded:
        print(json.dumps({"error": "所有图片下载失败。", "images": []}), flush=True)
        sys.exit(1)

    # Persist metadata so agent can reference titles when regenerating text later
    save_search_results(output_dir, args.keywords, downloaded)

    print(json.dumps({"images": downloaded}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
