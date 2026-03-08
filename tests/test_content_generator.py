"""
tests/test_content_generator.py
Unit tests for content_generator — uses mocked Grok API responses.
"""

import json
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from content_generator import (
    VideoScript,
    _parse_json,
    _validate_script_data,
    generate_script,
)

VALID_SCRIPT_DATA = {
    "title": "5 Mind-Blowing Science Facts #Shorts",
    "description": "Discover five incredible science facts in under a minute! #Shorts #Educational",
    "tags": ["science", "facts", "educational", "shorts"],
    "hook": "Did you know that humans share 60% of DNA with a banana?",
    "segments": [
        {"heading": "DNA Fun Fact", "text": "Our DNA is 99.9% identical to every other human on Earth."},
        {"heading": "Speed of Light", "text": "Light from the Sun takes 8 minutes to reach Earth."},
        {"heading": "Ocean Depths", "text": "More than 80% of Earth's oceans remain unexplored."},
    ],
    "call_to_action": "Follow for more amazing science facts every day!",
    "color_scheme": "blue",
    "category": "Science",
}


class TestParseJson:
    def test_parses_valid_json(self):
        raw = json.dumps(VALID_SCRIPT_DATA)
        result = _parse_json(raw)
        assert result["title"] == VALID_SCRIPT_DATA["title"]

    def test_strips_markdown_fences(self):
        raw = "```json\n" + json.dumps(VALID_SCRIPT_DATA) + "\n```"
        result = _parse_json(raw)
        assert result["hook"] == VALID_SCRIPT_DATA["hook"]

    def test_raises_on_invalid_json(self):
        with pytest.raises(ValueError, match="non-JSON"):
            _parse_json("this is not json at all")


class TestValidateScriptData:
    def test_valid_data_passes(self):
        _validate_script_data(VALID_SCRIPT_DATA)  # should not raise

    def test_missing_field_raises(self):
        data = {k: v for k, v in VALID_SCRIPT_DATA.items() if k != "hook"}
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_script_data(data)

    def test_empty_segments_raises(self):
        data = {**VALID_SCRIPT_DATA, "segments": []}
        with pytest.raises(ValueError, match="at least one segment"):
            _validate_script_data(data)

    def test_segment_missing_heading_raises(self):
        data = {**VALID_SCRIPT_DATA, "segments": [{"text": "only text"}]}
        with pytest.raises(ValueError, match="heading"):
            _validate_script_data(data)

    def test_segment_missing_text_raises(self):
        data = {**VALID_SCRIPT_DATA, "segments": [{"heading": "only heading"}]}
        with pytest.raises(ValueError, match="text"):
            _validate_script_data(data)


class TestVideoScript:
    def test_full_narration_concatenation(self):
        script = VideoScript(**VALID_SCRIPT_DATA)
        assert VALID_SCRIPT_DATA["hook"] in script.full_narration
        assert VALID_SCRIPT_DATA["call_to_action"] in script.full_narration
        for seg in VALID_SCRIPT_DATA["segments"]:
            assert seg["text"] in script.full_narration

    def test_slide_texts_includes_hook_and_cta(self):
        script = VideoScript(**VALID_SCRIPT_DATA)
        slides = script.slide_texts
        assert slides[0]["text"] == VALID_SCRIPT_DATA["hook"]
        assert slides[-1]["text"] == VALID_SCRIPT_DATA["call_to_action"]
        assert len(slides) == len(VALID_SCRIPT_DATA["segments"]) + 2

    def test_word_count_reasonable(self):
        script = VideoScript(**VALID_SCRIPT_DATA)
        word_count = len(script.full_narration.split())
        assert word_count <= 150, f"Script is too long: {word_count} words"


class TestGenerateScript:
    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("XAI_API_KEY", None)
            with pytest.raises(RuntimeError, match="XAI_API_KEY"):
                generate_script(api_key=None)

    def test_successful_generation(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(VALID_SCRIPT_DATA)

        with patch("content_generator.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.return_value = mock_response

            script = generate_script(api_key="fake-key")

        assert script.title == VALID_SCRIPT_DATA["title"]
        assert script.color_scheme == "blue"
        assert script.category == "Science"

    def test_api_failure_raises_runtime_error(self):
        with patch("content_generator.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.side_effect = Exception("network error")

            with pytest.raises(RuntimeError, match="Grok API call failed"):
                generate_script(api_key="fake-key")
