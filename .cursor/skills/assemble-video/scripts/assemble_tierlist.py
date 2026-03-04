"""
assemble_tierlist.py — Assemble a "tier list" ranking video from project.yaml.

Video format:
  - Background: full-screen tier list image with tier labels on the left
  - Intro segment: background only + intro audio
  - Per contestant:
      Phase 1 (commentary): large contestant image centered on screen + audio narration
      Phase 2 (placement):  0.6s animation — image shrinks and flies to its tier row
  - Outro segment: complete tier list + outro audio

Usage:
    python assemble_tierlist.py \\
      --project projects/myvideo/project.yaml \\
      --output  projects/myvideo/output/video.mp4 \\
      [--config config.yaml]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import yaml
from PIL import Image


# ─── Layout constants ─────────────────────────────────────────────────────────

ANIMATION_DURATION = 0.6    # seconds for the placement animation
FEATURED_MAX_SIZE  = 720    # max width / height for the featured contestant image
THUMBNAIL_PADDING  = 6      # pixels between thumbnail and tier-row edge (top/bottom)
THUMBNAIL_GAP      = 4      # pixels between adjacent thumbnails in the same row
DEFAULT_LABEL_W_RATIO = 0.127  # label column width as a fraction of video width


# ─── Utilities ────────────────────────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        for parent in [Path.cwd()] + list(Path.cwd().parents):
            candidate = parent / "config.yaml"
            if candidate.exists():
                path = candidate
                break
    return yaml.safe_load(path.read_text()) if path.exists() else {}


def load_project(project_path: Path) -> dict:
    return yaml.safe_load(project_path.read_text()) or {}


def resolve_path(base_dir: Path, path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (base_dir / p).resolve()


def smoothstep(t: float) -> float:
    """Smooth easing: maps [0,1] → [0,1] with zero derivative at endpoints."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def load_rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def resize_contain(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Scale down to fit within (max_w, max_h), preserving aspect ratio."""
    img = img.copy()
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def center_crop_square(img: Image.Image, size: int) -> Image.Image:
    """Center-crop to square then resize to `size × size`."""
    w, h = img.size
    s = min(w, h)
    left = (w - s) // 2
    top  = (h - s) // 2
    return img.crop((left, top, left + s, top + s)).resize((size, size), Image.LANCZOS)


def paste_rgba(canvas: Image.Image, img: Image.Image, x: int, y: int) -> None:
    """Paste an RGBA image onto canvas using its alpha channel as mask."""
    if img.mode == "RGBA":
        canvas.paste(img, (x, y), mask=img)
    else:
        canvas.paste(img, (x, y))


def pil_to_numpy(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGB"))


# ─── Layout ───────────────────────────────────────────────────────────────────

class TierListLayout:
    """
    Manages thumbnail placement within tier rows.

    Coordinate system: (0, 0) = top-left of video frame.
    Each tier row spans the full video width, with the label column on the left.
    Thumbnails are placed left-to-right within each row.
    """

    def __init__(self, video_w: int, video_h: int, tiers: list[dict], label_w: int):
        self.video_w  = video_w
        self.video_h  = video_h
        self.tiers    = tiers
        self.tier_ids = [t["id"] for t in tiers]
        self.label_w  = label_w

        self.num_tiers      = len(tiers)
        self.tier_h         = video_h // self.num_tiers
        self.thumbnail_size = self.tier_h - 2 * THUMBNAIL_PADDING
        self.thumbnail_stride = self.thumbnail_size + THUMBNAIL_GAP

        # Track how many thumbnails have been placed in each tier
        self.tier_counts: dict[str, int] = {t["id"]: 0 for t in tiers}

    def tier_index(self, tier_id: str) -> int:
        return self.tier_ids.index(tier_id)

    def thumbnail_topleft(self, tier_id: str, position: int) -> tuple[int, int]:
        """(x, y) top-left corner for thumbnail at `position` in the given tier."""
        row = self.tier_index(tier_id)
        x   = self.label_w + position * self.thumbnail_stride
        y   = row * self.tier_h + THUMBNAIL_PADDING
        return x, y

    def featured_topleft(self, feat_w: int, feat_h: int) -> tuple[int, int]:
        """(x, y) to center an image of (feat_w × feat_h) on the video frame."""
        return (self.video_w - feat_w) // 2, (self.video_h - feat_h) // 2

    def allocate(self, tier_id: str) -> int:
        """Reserve a position in the tier and return its index."""
        pos = self.tier_counts[tier_id]
        self.tier_counts[tier_id] += 1
        return pos


# ─── Frame composition ────────────────────────────────────────────────────────

PlacedThumb = tuple[Image.Image, int, int]   # (thumbnail, x, y)


def build_base(bg: Image.Image, placed: list[PlacedThumb]) -> Image.Image:
    """Compose background + all previously placed thumbnails."""
    frame = bg.copy()
    for thumb, x, y in placed:
        paste_rgba(frame, thumb, x, y)
    return frame


def build_frame(
    base: Image.Image,
    overlay: Optional[Image.Image] = None,
    ox: int = 0,
    oy: int = 0,
) -> np.ndarray:
    """Composite overlay onto base and return as RGB numpy array."""
    frame = base.copy()
    if overlay is not None:
        paste_rgba(frame, overlay, ox, oy)
    return pil_to_numpy(frame)


# ─── Animation helpers ────────────────────────────────────────────────────────

def make_placement_frames(
    base: Image.Image,
    src_img: Image.Image,
    src_pos: tuple[int, int],
    dst_pos: tuple[int, int],
    dst_size: int,
    n_frames: int,
) -> list[np.ndarray]:
    """
    Generate `n_frames` frames animating `src_img` from its featured position/size
    to the small thumbnail position/size in the tier row.
    """
    src_w, src_h = src_img.size
    sx0, sy0 = src_pos   # top-left of featured image (full size)
    tx, ty   = dst_pos   # top-left of final thumbnail

    frames = []
    for i in range(n_frames):
        t = smoothstep(i / max(1, n_frames - 1))

        # Interpolate size (featured → thumbnail)
        cw = max(1, int(src_w + (dst_size - src_w) * t))
        ch = max(1, int(src_h + (dst_size - src_h) * t))

        # Keep the image visually centered during shrink:
        # start center = src center, end center = thumbnail center
        start_cx = sx0 + src_w // 2
        start_cy = sy0 + src_h // 2
        end_cx   = tx  + dst_size // 2
        end_cy   = ty  + dst_size // 2

        cx = int(start_cx + (end_cx - start_cx) * t)
        cy = int(start_cy + (end_cy - start_cy) * t)

        current = src_img.resize((cw, ch), Image.LANCZOS)
        ox = cx - cw // 2
        oy = cy - ch // 2

        frames.append(build_frame(base, current, ox, oy))

    return frames


# ─── Video assembly ───────────────────────────────────────────────────────────

def build_video(project: dict, project_dir: Path, output: Path, fps: int) -> float:
    from moviepy import AudioFileClip, ImageClip, VideoClip, concatenate_videoclips

    # ── Parse project config ────────────────────────────────────────────────
    video_w, video_h = map(int, project["resolution"].split("x"))
    tiers_config  = project.get("tiers", [])
    tierlist_cfg  = project.get("tierlist", {})

    bg_path = resolve_path(project_dir, tierlist_cfg["background"])
    bg_img  = load_rgba(bg_path).resize((video_w, video_h), Image.LANCZOS)

    label_w = int(video_w * tierlist_cfg.get("label_width_ratio", DEFAULT_LABEL_W_RATIO))
    layout  = TierListLayout(video_w, video_h, tiers_config, label_w)

    placed: list[PlacedThumb] = []
    clips = []

    # ── Intro ────────────────────────────────────────────────────────────────
    intro = project.get("intro")
    if intro and intro.get("audio"):
        audio = AudioFileClip(str(resolve_path(project_dir, intro["audio"])))
        base  = build_base(bg_img, placed)
        frame = build_frame(base)
        clips.append(ImageClip(frame).with_duration(audio.duration).with_audio(audio))

    # ── Contestants ──────────────────────────────────────────────────────────
    for contestant in project.get("contestants", []):
        img_path   = resolve_path(project_dir, contestant["image"])
        audio_path = resolve_path(project_dir, contestant["audio"])
        tier_id    = contestant["tier"]

        raw         = load_rgba(img_path)
        featured    = resize_contain(raw.copy(), FEATURED_MAX_SIZE, FEATURED_MAX_SIZE)
        feat_w, feat_h = featured.size
        feat_x, feat_y = layout.featured_topleft(feat_w, feat_h)

        thumb_size  = layout.thumbnail_size
        thumbnail   = center_crop_square(raw.copy(), thumb_size)

        pos_in_tier = layout.allocate(tier_id)
        thumb_x, thumb_y = layout.thumbnail_topleft(tier_id, pos_in_tier)

        # Phase 1: commentary — static composite with featured image
        audio = AudioFileClip(str(audio_path))
        base  = build_base(bg_img, placed)
        frame = build_frame(base, featured, feat_x, feat_y)
        commentary_clip = (
            ImageClip(frame)
            .with_duration(audio.duration)
            .with_audio(audio)
        )
        clips.append(commentary_clip)

        # Phase 2: placement animation — featured image flies to tier row
        n_frames    = max(2, int(ANIMATION_DURATION * fps))
        anim_base   = build_base(bg_img, placed)
        anim_frames = make_placement_frames(
            anim_base,
            featured,
            (feat_x, feat_y),
            (thumb_x, thumb_y),
            thumb_size,
            n_frames,
        )

        def _make_frame(t, frames=anim_frames, dur=ANIMATION_DURATION):
            idx = min(int(t / dur * len(frames)), len(frames) - 1)
            return frames[idx]

        anim_clip = VideoClip(_make_frame, duration=ANIMATION_DURATION)
        clips.append(anim_clip)

        # Register this thumbnail for all subsequent frames
        placed.append((thumbnail, thumb_x, thumb_y))

    # ── Outro ────────────────────────────────────────────────────────────────
    outro = project.get("outro")
    if outro and outro.get("audio"):
        audio = AudioFileClip(str(resolve_path(project_dir, outro["audio"])))
        base  = build_base(bg_img, placed)
        frame = build_frame(base)
        clips.append(ImageClip(frame).with_duration(audio.duration).with_audio(audio))

    # ── Concatenate & export ─────────────────────────────────────────────────
    if not clips:
        raise ValueError("No clips generated — check that intro/contestants/outro have audio.")

    final = concatenate_videoclips(clips, method="compose")
    output.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(output), fps=fps, logger=None)

    total = round(final.duration, 2)
    for clip in clips:
        clip.close()
    final.close()

    return total


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Assemble a tier-list ranking video from project.yaml.")
    parser.add_argument("--project", required=True, help="Path to project.yaml")
    parser.add_argument("--output",  required=True, help="Output MP4 path")
    parser.add_argument("--config",  default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    project_path = Path(args.project)
    project_dir  = project_path.parent
    project      = load_project(project_path)

    if project.get("type") != "tierlist":
        print(json.dumps({"error": "project.yaml 的 type 字段必须为 'tierlist'。"}), flush=True)
        sys.exit(1)

    fps = project.get("fps") or load_config(args.config).get("default_fps", 24)

    try:
        total = build_video(project, project_dir, Path(args.output), fps)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), flush=True)
        sys.exit(1)

    print(
        json.dumps({"path": args.output, "duration_seconds": total}, ensure_ascii=False),
        flush=True,
    )


if __name__ == "__main__":
    main()
