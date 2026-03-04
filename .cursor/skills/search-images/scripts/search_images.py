"""
search_images.py — 从 Pexels 和 Unsplash 下载图片素材。

用法：
    python search_images.py --keywords "故宫 宫殿" --output projects/myvideo/images/slide_01/
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
import yaml


def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        # 向上查找 config.yaml
        for parent in Path.cwd().parents:
            candidate = parent / "config.yaml"
            if candidate.exists():
                path = candidate
                break
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def search_pexels(keywords: str, count: int, orientation: str, api_key: str) -> list[dict]:
    if not api_key or api_key == "YOUR_PEXELS_KEY":
        return []
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        params={"query": keywords, "per_page": count, "orientation": orientation},
        headers={"Authorization": api_key},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"[search-images] Pexels error {resp.status_code}: {resp.text}", file=sys.stderr)
        return []
    photos = resp.json().get("photos", [])
    return [
        {"url": p["src"]["large"], "source": "pexels", "photographer": p.get("photographer", "")}
        for p in photos
    ]


def search_unsplash(keywords: str, count: int, orientation: str, access_key: str) -> list[dict]:
    if not access_key or access_key == "YOUR_UNSPLASH_KEY":
        return []
    resp = requests.get(
        "https://api.unsplash.com/search/photos",
        params={"query": keywords, "per_page": count, "orientation": orientation},
        headers={"Authorization": f"Client-ID {access_key}"},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"[search-images] Unsplash error {resp.status_code}: {resp.text}", file=sys.stderr)
        return []
    results = resp.json().get("results", [])
    return [
        {"url": r["urls"]["regular"], "source": "unsplash", "photographer": r["user"]["name"]}
        for r in results
    ]


def download_image(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[search-images] Download failed {url}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="搜索并下载图片素材。")
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
    unsplash_key = config.get("unsplash_access_key", "")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = search_pexels(args.keywords, count, orientation, pexels_key)
    if len(candidates) < count:
        remaining = count - len(candidates)
        candidates += search_unsplash(args.keywords, remaining, orientation, unsplash_key)

    if not candidates:
        print(
            json.dumps({"error": "未找到图片，请检查 config.yaml 中的 API Key。", "images": []}),
            flush=True,
        )
        sys.exit(1)

    downloaded = []
    for i, candidate in enumerate(candidates[:count]):
        ext = ".jpg"
        dest = output_dir / f"photo_{i:02d}{ext}"
        if download_image(candidate["url"], dest):
            downloaded.append(
                {
                    "path": str(dest),
                    "source": candidate["source"],
                    "url": candidate["url"],
                    "photographer": candidate.get("photographer", ""),
                }
            )

    print(json.dumps({"images": downloaded}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
