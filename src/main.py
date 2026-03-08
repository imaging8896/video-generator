"""
main.py
Entry point for the daily YouTube Shorts video generation pipeline.

Pipeline:
  1. Generate content script with Grok AI
  2. Create MP4 video (1080×1920, ≤ 60 s)
  3. Upload to YouTube as Shorts

Environment variables (set via .env or CI secrets):
  XAI_API_KEY            — xAI / Grok API key
  YOUTUBE_CLIENT_ID      — YouTube OAuth2 client ID
  YOUTUBE_CLIENT_SECRET  — YouTube OAuth2 client secret
  YOUTUBE_REFRESH_TOKEN  — YouTube OAuth2 refresh token
  TTS_LANGUAGE           — BCP-47 language code (default: en)
  OUTPUT_DIR             — Working directory (default: /tmp/video_output)
"""

import logging
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

from content_generator import generate_script
from video_creator import create_video
from youtube_uploader import upload_video

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("main")


def main() -> None:
    load_dotenv()

    output_dir = os.environ.get("OUTPUT_DIR", "/tmp/video_output")
    language = os.environ.get("TTS_LANGUAGE", "en")

    logger.info("═" * 60)
    logger.info("Daily YouTube Shorts Generator — starting")
    logger.info("Output directory : %s", output_dir)
    logger.info("TTS language     : %s", language)
    logger.info("═" * 60)

    # ── Step 1: Generate script with Grok AI ─────────────────────────────────
    logger.info("STEP 1/3 — Generating script via Grok AI …")
    try:
        script = generate_script()
    except Exception as exc:
        logger.error("Script generation failed: %s", exc)
        sys.exit(1)

    logger.info("Title  : %s", script.title)
    logger.info("Slides : %d", len(script.slide_texts))
    logger.info("Words  : %d", len(script.full_narration.split()))

    # ── Step 2: Create video ──────────────────────────────────────────────────
    logger.info("STEP 2/3 — Creating video …")
    try:
        video_path = create_video(script, output_dir=output_dir, language=language)
    except Exception as exc:
        logger.error("Video creation failed: %s", exc)
        sys.exit(1)

    logger.info("Video ready: %s", video_path)

    # ── Step 3: Upload to YouTube ─────────────────────────────────────────────
    logger.info("STEP 3/3 — Uploading to YouTube …")
    try:
        video_id = upload_video(video_path, script)
    except Exception as exc:
        logger.error("YouTube upload failed: %s", exc)
        sys.exit(1)

    logger.info("═" * 60)
    logger.info("Done! YouTube Shorts URL: https://youtube.com/shorts/%s", video_id)
    logger.info("═" * 60)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    _cleanup(output_dir)


def _cleanup(output_dir: str) -> None:
    """Removes the working directory to free runner disk space."""
    try:
        shutil.rmtree(output_dir, ignore_errors=True)
        logger.info("Cleaned up working directory: %s", output_dir)
    except Exception as exc:
        logger.warning("Cleanup failed (non-fatal): %s", exc)


if __name__ == "__main__":
    main()
