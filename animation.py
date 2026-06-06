"""在普通终端中播放像素风小猫动画。

运行:
    python animation.py

依赖:
    python -m pip install pillow opencv-python numpy
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageSequence

GIF_PATH = Path(__file__).with_name("cat_pixel_animation.gif")

WHITE_DISTANCE_THRESHOLD = 24
WHITE_SPREAD_THRESHOLD = 14
EDGE_WHITE_DISTANCE_THRESHOLD = 42
DEFAULT_RENDER_WIDTH = 48
MIN_RENDER_WIDTH = 20
FRAME_DELAY_FALLBACK_MS = 100
CAT_GAP = "    "


def build_foreground_mask(frame_rgb: np.ndarray) -> np.ndarray:
    """抠除接近纯白的背景，并尽量去掉猫周围的浅色底板。"""
    white_distance = 255 - frame_rgb.max(axis=2)
    channel_spread = frame_rgb.max(axis=2) - frame_rgb.min(axis=2)

    near_white = (
        (white_distance < WHITE_DISTANCE_THRESHOLD)
        & (channel_spread < WHITE_SPREAD_THRESHOLD)
    ).astype(np.uint8)

    h, w = near_white.shape
    flood_mask = np.zeros((h + 2, w + 2), np.uint8)
    background = near_white.copy() * 255
    cv2.floodFill(background, flood_mask, (0, 0), 128)
    cv2.floodFill(background, flood_mask, (w - 1, 0), 128)
    cv2.floodFill(background, flood_mask, (0, h - 1), 128)
    cv2.floodFill(background, flood_mask, (w - 1, h - 1), 128)

    foreground = np.where(background == 128, 0, 255).astype(np.uint8)

    kernel = np.ones((3, 3), np.uint8)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)
    foreground = cv2.medianBlur(foreground, 3)

    edge_ring = cv2.subtract(foreground, cv2.erode(foreground, kernel, iterations=1))
    edge_white = (
        (white_distance < EDGE_WHITE_DISTANCE_THRESHOLD)
        & (channel_spread < WHITE_SPREAD_THRESHOLD + 6)
    ).astype(np.uint8) * 255
    foreground = np.where((edge_ring > 0) & (edge_white > 0), 0, foreground).astype(
        np.uint8
    )
    return foreground


def content_bbox(alpha: np.ndarray) -> tuple[int, int, int, int]:
    points = cv2.findNonZero(alpha)
    if points is None:
        raise RuntimeError("当前帧没有检测到小猫主体。")

    x, y, w, h = cv2.boundingRect(points)
    pad = 2
    x0 = max(x - pad, 0)
    y0 = max(y - pad, 0)
    x1 = min(x + w + pad, alpha.shape[1])
    y1 = min(y + h + pad, alpha.shape[0])
    return x0, y0, x1, y1


def union_bbox(boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    x0 = min(box[0] for box in boxes)
    y0 = min(box[1] for box in boxes)
    x1 = max(box[2] for box in boxes)
    y1 = max(box[3] for box in boxes)
    return x0, y0, x1, y1


def target_size(src_w: int, src_h: int) -> tuple[int, int]:
    term_size = shutil.get_terminal_size((80, 24))
    max_width = max(MIN_RENDER_WIDTH, term_size.columns - 4)
    max_height = max(4, (term_size.lines - 2) * 2)

    scale = min(max_width / src_w, max_height / src_h, 1.0)
    preferred_width = min(DEFAULT_RENDER_WIDTH / src_w, 1.0)
    scale = min(scale, preferred_width) if preferred_width > 0 else scale

    width = max(MIN_RENDER_WIDTH, round(src_w * scale))
    width = min(width, max_width)
    height = max(2, round(src_h * (width / src_w)))
    return width, height


def resize_rgba(image: np.ndarray, width: int, height: int) -> np.ndarray:
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_NEAREST)


def ansi_rgb_fg(pixel: np.ndarray) -> str:
    return f"\033[38;2;{pixel[0]};{pixel[1]};{pixel[2]}m"


def ansi_rgb_bg(pixel: np.ndarray) -> str:
    return f"\033[48;2;{pixel[0]};{pixel[1]};{pixel[2]}m"


def frame_to_ansi(rgba: np.ndarray) -> str:
    """把 RGBA 帧转成终端可显示的 ANSI 彩色字符。"""
    if rgba.shape[0] % 2 == 1:
        pad = np.zeros((1, rgba.shape[1], 4), dtype=np.uint8)
        rgba = np.vstack([rgba, pad])

    lines: list[str] = []
    reset = "\033[0m"

    for row in range(0, rgba.shape[0], 2):
        top = rgba[row]
        bottom = rgba[row + 1]
        parts: list[str] = []

        for top_px, bottom_px in zip(top, bottom):
            top_a = top_px[3] > 0
            bottom_a = bottom_px[3] > 0

            if top_a and bottom_a:
                parts.append(
                    f"{ansi_rgb_fg(top_px[:3])}{ansi_rgb_bg(bottom_px[:3])}▀"
                )
            elif top_a:
                parts.append(f"{ansi_rgb_fg(top_px[:3])}▀")
            elif bottom_a:
                parts.append(f"{ansi_rgb_fg(bottom_px[:3])}▄")
            else:
                parts.append(reset + " ")

        lines.append("".join(parts) + reset)

    return "\n".join(lines)


def prepare_animation(gif_path: Path) -> tuple[list[str], list[float]]:
    image = Image.open(gif_path)
    rgba_frames: list[np.ndarray] = []
    boxes: list[tuple[int, int, int, int]] = []
    durations: list[float] = []

    for frame in ImageSequence.Iterator(image):
        rgba = np.array(frame.convert("RGBA"), dtype=np.uint8)
        alpha = build_foreground_mask(rgba[..., :3])
        composed = np.dstack([rgba[..., :3], alpha])

        rgba_frames.append(composed)
        boxes.append(content_bbox(alpha))
        durations.append(
            max(frame.info.get("duration", FRAME_DELAY_FALLBACK_MS), 20) / 1000.0
        )

    if not rgba_frames:
        raise RuntimeError("GIF 中没有可播放的帧。")

    x0, y0, x1, y1 = union_bbox(boxes)
    crop_w = x1 - x0
    crop_h = y1 - y0
    width, height = target_size(crop_w, crop_h)

    rendered_frames: list[str] = []
    for frame in rgba_frames:
        cropped = frame[y0:y1, x0:x1]
        scaled = resize_rgba(cropped, width, height)
        rendered_frames.append(frame_to_ansi(scaled))

    return rendered_frames, durations


def play(frames: list[str], durations: list[float]) -> None:
    hide_cursor = "\033[?25l"
    show_cursor = "\033[?25h"
    clear = "\033[2J"
    home = "\033[H"

    sys.stdout.write(hide_cursor + clear)
    sys.stdout.flush()

    try:
        while True:
            for frame, duration in zip(frames, durations):
                start = time.perf_counter()
                sys.stdout.write(home + frame)
                sys.stdout.flush()

                elapsed = time.perf_counter() - start
                remaining = duration - elapsed
                if remaining > 0:
                    time.sleep(remaining)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\n" + show_cursor)
        sys.stdout.flush()


def duplicate_cat_frame(frame: str, gap: str = CAT_GAP) -> str:
    return "\n".join(f"{line}{gap}{line}" for line in frame.splitlines())


def quadruple_cat_frame(frame: str, gap: str = CAT_GAP) -> str:
    top_row = duplicate_cat_frame(frame, gap)
    return f"{top_row}\n{top_row}"


def main() -> None:
    if not GIF_PATH.exists():
        raise SystemExit(f"找不到 GIF 文件: {GIF_PATH}")

    frames, durations = prepare_animation(GIF_PATH)
    grid_frames = [quadruple_cat_frame(frame) for frame in frames]
    play(grid_frames, durations)


if __name__ == "__main__":
    main()
