"""
youtube_uploader.py
Uploads the generated video to YouTube as a Shorts video using the
YouTube Data API v3.

Authentication uses OAuth2 refresh-token flow so it works in headless CI
environments without interactive browser prompts.
"""

import logging
import os

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from content_generator import VideoScript

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"

# YouTube category IDs
CATEGORY_MAP = {
    "Education":   "27",
    "Science":     "28",
    "Technology":  "28",
    "Lifestyle":   "22",
    "Psychology":  "27",
    "History":     "27",
}
DEFAULT_CATEGORY_ID = "22"  # People & Blogs


def _build_credentials() -> Credentials:
    """
    Builds OAuth2 Credentials from environment variables.
    Required env vars:
      - YOUTUBE_CLIENT_ID
      - YOUTUBE_CLIENT_SECRET
      - YOUTUBE_REFRESH_TOKEN
    """
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    missing = [
        name
        for name, val in [
            ("YOUTUBE_CLIENT_ID", client_id),
            ("YOUTUBE_CLIENT_SECRET", client_secret),
            ("YOUTUBE_REFRESH_TOKEN", refresh_token),
        ]
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing YouTube credentials env vars: {', '.join(missing)}. "
            "Run scripts/setup_youtube_auth.py to obtain them."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[YOUTUBE_UPLOAD_SCOPE],
    )

    # Refresh to get a valid access token
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds


def upload_video(video_path: str, script: VideoScript) -> str:
    """
    Uploads *video_path* to YouTube with metadata derived from *script*.

    Args:
        video_path: Local path to the MP4 file.
        script: VideoScript containing title, description, tags, etc.

    Returns:
        The YouTube video ID of the uploaded video.

    Raises:
        RuntimeError: On authentication or upload failure.
        HttpError: On YouTube API errors.
    """
    creds = _build_credentials()
    youtube = build(
        YOUTUBE_API_SERVICE,
        YOUTUBE_API_VERSION,
        credentials=creds,
        cache_discovery=False,
    )

    category_id = CATEGORY_MAP.get(script.category, DEFAULT_CATEGORY_ID)

    # Ensure #Shorts is present in both title and description
    title = _ensure_shorts_tag(script.title)
    description = _ensure_shorts_tag(script.description)
    if len(description) > 5000:
        logger.warning(
            "Description truncated from %d to 5000 characters.", len(description)
        )
        description = description[:5000]

    body = {
        "snippet": {
            "title": title[:100],          # YouTube title limit
            "description": description,
            "tags": script.tags[:500],      # YouTube tags limit
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,  # 1 MB chunks
    )

    logger.info("Uploading video to YouTube …")
    try:
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )
        response = _resumable_upload(request)
    except HttpError as exc:
        raise RuntimeError(
            f"YouTube upload failed (HTTP {exc.resp.status}): {exc.content}"
        ) from exc

    video_id = response.get("id")
    logger.info(
        "Upload complete — video ID: %s | URL: https://youtu.be/%s",
        video_id,
        video_id,
    )
    return video_id


def _ensure_shorts_tag(text: str) -> str:
    """Appends #Shorts if not already present."""
    if "#Shorts" not in text and "#shorts" not in text:
        text = text.rstrip() + " #Shorts"
    return text


def _resumable_upload(insert_request) -> dict:
    """
    Executes a resumable upload with exponential back-off on transient errors.
    """
    import http.client
    import random
    import time

    MAX_RETRIES = 10
    RETRYABLE_STATUS_CODES = {500, 502, 503, 504}

    response = None
    error = None
    retry = 0

    while response is None:
        try:
            logger.debug("Uploading chunk …")
            _, response = insert_request.next_chunk()
        except HttpError as exc:
            if exc.resp.status in RETRYABLE_STATUS_CODES:
                error = exc
            else:
                raise
        except (
            http.client.HTTPException,
            OSError,
        ) as exc:
            error = exc

        if error is not None:
            retry += 1
            if retry > MAX_RETRIES:
                raise RuntimeError(
                    f"Upload failed after {MAX_RETRIES} retries: {error}"
                )
            sleep_seconds = (2**retry) + random.random()
            logger.warning(
                "Transient error — retrying in %.1f s (attempt %d/%d): %s",
                sleep_seconds,
                retry,
                MAX_RETRIES,
                error,
            )
            time.sleep(sleep_seconds)
            error = None

    return response
