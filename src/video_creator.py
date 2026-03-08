"""
video_creator.py
Assembles a YouTube Shorts video (1080×1920, ≤ 60 s) from:
  - Slide images rendered entirely with Pillow (no copyrighted assets)
  - A narration audio track produced by gTTS
  - MoviePy for compositing and MP4 export
"""

import logging
import math
import os
import textwrap
from pathlib import Path
from typing import List, Tuple

import numpy as np
from gtts import gTTS
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont

from content_generator import VideoScript

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1080, 1920
MAX_VIDEO_DURATION = 58.0  # seconds — safety margin below the 60-second limit
FPS = 30

# Gradient palettes (start_colour, end_colour)
COLOR_PALETTES = {
    "blue":   ("#0D1B2A", "#1B4F72"),
    "green":  ("#0B3D2E", "#1E8449"),
    "orange": ("#3D1A00", "#D35400"),
    "purple": ("#1A0030", "#7D3C98"),
    "red":    ("#2D0000", "#C0392B"),
    "teal":   ("#002B36", "#148F77"),
}

# Fallback system font; Pillow will use its internal bitmap font if absent
_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _hex_to_rgb(hex_colour: str) -> Tuple[int, int, int]:
    hex_colour = hex_colour.lstrip("#")
    return tuple(int(hex_colour[i : i + 2], 16) for i in (0, 2, 4))


def _create_gradient_image(
    top_colour: str, bottom_colour: str
) -> Image.Image:
    """Creates a vertical linear gradient background."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    r1, g1, b1 = _hex_to_rgb(top_colour)
    r2, g2, b2 = _hex_to_rgb(bottom_colour)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return img


def _draw_text_centred(
    draw: ImageDraw.ImageDraw,
    text: str,
    y_centre: int,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    max_width_px: int,
) -> int:
    """Draws word-wrapped, centre-aligned text. Returns bottom-most y pixel."""
    chars_per_line = max(1, max_width_px // (font.size // 2))
    lines = textwrap.wrap(text, width=chars_per_line)
    line_height = font.size + 8
    total_height = line_height * len(lines)
    y = y_centre - total_height // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        # Subtle drop shadow (solid black — image is RGB mode)
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def render_slide(
    heading: str,
    body: str,
    colour_scheme: str,
    slide_index: int,
    total_slides: int,
) -> np.ndarray:
    """
    Renders one slide as an RGB numpy array (HEIGHT × WIDTH × 3, uint8).
    """
    top, bottom = COLOR_PALETTES.get(colour_scheme, COLOR_PALETTES["blue"])
    img = _create_gradient_image(top, bottom)
    draw = ImageDraw.Draw(img)

    margin = 80

    # Progress bar at top
    bar_width = int(WIDTH * (slide_index + 1) / total_slides)
    draw.rectangle([(0, 0), (bar_width, 12)], fill=(255, 255, 255, 180))

    # Heading
    heading_font = _load_font(72)
    _draw_text_centred(
        draw,
        heading.upper(),
        HEIGHT // 3,
        heading_font,
        fill=(255, 220, 80),
        max_width_px=WIDTH - 2 * margin,
    )

    # Divider
    div_y = HEIGHT // 3 + 80
    draw.line([(margin, div_y), (WIDTH - margin, div_y)], fill=(255, 255, 255, 100), width=3)

    # Body text
    body_font = _load_font(54)
    _draw_text_centred(
        draw,
        body,
        HEIGHT // 3 + 160 + (HEIGHT // 3),
        body_font,
        fill=(255, 255, 255),
        max_width_px=WIDTH - 2 * margin,
    )

    return np.array(img)


def generate_tts_audio(narration: str, output_path: str, language: str = "en") -> None:
    """Generates a TTS MP3 file from the narration text."""
    logger.info("Generating TTS audio …")
    tts = gTTS(text=narration, lang=language, slow=False)
    tts.save(output_path)
    logger.info("TTS audio saved to %s", output_path)


def create_video(
    script: VideoScript,
    output_dir: str,
    language: str = "en",
) -> str:
    """
    Creates a vertical MP4 video from the script.

    Args:
        script: Populated VideoScript from content_generator.
        output_dir: Directory where temporary and final files are written.
        language: BCP-47 language code for gTTS.

    Returns:
        Absolute path to the final MP4 file.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    audio_path = str(out / "narration.mp3")
    video_path = str(out / "shorts_video.mp4")

    # 1. Generate TTS
    generate_tts_audio(script.full_narration, audio_path, language)

    # 2. Measure total audio duration
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    logger.info("TTS duration: %.2f s", audio_duration)

    if audio_duration > MAX_VIDEO_DURATION:
        logger.warning(
            "Narration is %.2f s — trimming audio to %.2f s",
            audio_duration,
            MAX_VIDEO_DURATION,
        )
        audio_clip = audio_clip.subclip(0, MAX_VIDEO_DURATION)
        audio_duration = MAX_VIDEO_DURATION

    # 3. Distribute duration equally among slides
    slides = script.slide_texts
    slide_duration = audio_duration / len(slides)
    logger.info(
        "Rendering %d slides × %.2f s each", len(slides), slide_duration
    )

    # 4. Render slide images and build video clips
    clips = []
    for i, slide in enumerate(slides):
        frame = render_slide(
            heading=slide["heading"],
            body=slide["text"],
            colour_scheme=script.color_scheme,
            slide_index=i,
            total_slides=len(slides),
        )
        clip = (
            ImageClip(frame)
            .set_duration(slide_duration)
            .set_fps(FPS)
            .fadein(0.3)
            .fadeout(0.3)
        )
        clips.append(clip)

    # 5. Concatenate and add audio
    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(audio_clip)

    # 6. Export
    logger.info("Encoding video → %s", video_path)
    video.write_videofile(
        video_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(out / "temp_audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    audio_clip.close()
    video.close()

    logger.info("Video created: %s", video_path)
    return video_path
