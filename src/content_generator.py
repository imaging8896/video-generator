"""
content_generator.py
Uses the Grok AI API (xAI) to generate a short-video script optimised for
YouTube Shorts:
  - Topic selected for maximum organic reach
  - Script ≤ 120 words so TTS fits within 60 seconds
  - No copyrighted material or YouTube-guideline violations
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert YouTube Shorts content strategist.
Your goal is to create viral, educational short-video scripts that:
1. Grab attention in the first 3 seconds with a compelling hook
2. Deliver genuine educational or entertainment value
3. Are completely original — no copyrighted material, no trademarked content,
   no music references, no celebrity quotes
4. Comply fully with YouTube's Community Guidelines
5. Use plain, accessible language suitable for a global audience

Output ONLY valid JSON — no markdown fences, no extra text."""

USER_PROMPT = """Create a YouTube Shorts script for today's video.
Choose a trending, educational topic (e.g. science facts, productivity tips,
psychology insights, history, technology, nature, life hacks).

Return a JSON object with exactly these fields:
{
  "title": "<catchy title ≤ 60 chars, include #Shorts>",
  "description": "<YouTube description ≤ 300 chars, include #Shorts, #Educational>",
  "tags": ["tag1", "tag2", ...],  // 10-15 relevant tags, no spaces within each tag
  "hook": "<first sentence spoken aloud, ≤ 15 words, must create curiosity>",
  "segments": [
    {"text": "<spoken text for this slide>", "heading": "<1-5 word slide heading>"},
    ...
  ],  // 4-7 segments, each ≤ 25 words
  "call_to_action": "<final sentence ≤ 15 words, encourage like/follow>",
  "color_scheme": "<one of: blue, green, orange, purple, red, teal>",
  "category": "<one of: Education, Science, Technology, Lifestyle, Psychology, History>"
}

Total spoken words (hook + all segment texts + call_to_action) must be ≤ 120 words."""


@dataclass
class VideoScript:
    title: str
    description: str
    tags: List[str]
    hook: str
    segments: List[dict]
    call_to_action: str
    color_scheme: str
    category: str
    full_narration: str = field(init=False)

    def __post_init__(self):
        parts = [self.hook]
        parts += [s["text"] for s in self.segments]
        parts.append(self.call_to_action)
        self.full_narration = " ".join(parts)

    @property
    def slide_texts(self) -> List[dict]:
        """Returns all slides including hook and CTA."""
        slides = [{"heading": "Did you know?", "text": self.hook}]
        slides += self.segments
        slides.append({"heading": "Follow for more!", "text": self.call_to_action})
        return slides


def generate_script(api_key: str | None = None) -> VideoScript:
    """
    Calls Grok AI to generate a VideoScript for today's YouTube Shorts video.

    Args:
        api_key: xAI API key. Falls back to XAI_API_KEY env variable.

    Returns:
        A populated VideoScript dataclass.

    Raises:
        ValueError: If the API response cannot be parsed.
        RuntimeError: If the API call fails.
    """
    resolved_key = api_key or os.environ.get("XAI_API_KEY")
    if not resolved_key:
        raise RuntimeError(
            "XAI_API_KEY is not set. "
            "Export it as an environment variable or pass it explicitly."
        )

    client = OpenAI(api_key=resolved_key, base_url="https://api.x.ai/v1")

    logger.info("Requesting script from Grok AI …")
    try:
        response = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            temperature=0.9,
            max_tokens=800,
        )
    except Exception as exc:
        raise RuntimeError(f"Grok API call failed: {exc}") from exc

    raw = response.choices[0].message.content.strip()
    logger.debug("Raw Grok response: %s", raw)

    data = _parse_json(raw)
    _validate_script_data(data)

    script = VideoScript(
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        hook=data["hook"],
        segments=data["segments"],
        call_to_action=data["call_to_action"],
        color_scheme=data.get("color_scheme", "blue"),
        category=data.get("category", "Education"),
    )

    word_count = len(script.full_narration.split())
    logger.info(
        "Script generated — title: %r | words: %d | slides: %d",
        script.title,
        word_count,
        len(script.slide_texts),
    )
    return script


def _parse_json(raw: str) -> dict:
    """Extracts and parses JSON from the model's response."""
    # Strip markdown code fences if the model added them despite instructions
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Grok returned non-JSON content. Raw response:\n{raw}"
        ) from exc


def _validate_script_data(data: dict) -> None:
    required = {"title", "description", "tags", "hook", "segments", "call_to_action"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Script JSON is missing required fields: {missing}")
    if not isinstance(data["segments"], list) or len(data["segments"]) == 0:
        raise ValueError("Script must have at least one segment.")
    for i, seg in enumerate(data["segments"]):
        if "text" not in seg or "heading" not in seg:
            raise ValueError(f"Segment {i} missing 'text' or 'heading' field.")
