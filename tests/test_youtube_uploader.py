"""
tests/test_youtube_uploader.py
Unit tests for youtube_uploader — credentials construction and tag handling.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from youtube_uploader import _ensure_shorts_tag, _build_credentials


class TestEnsureShortsTag:
    def test_adds_shorts_when_absent(self):
        result = _ensure_shorts_tag("Amazing science facts")
        assert "#Shorts" in result

    def test_does_not_duplicate_shorts_tag(self):
        title = "Amazing science facts #Shorts"
        result = _ensure_shorts_tag(title)
        assert result.count("#Shorts") == 1

    def test_lowercase_shorts_not_duplicated(self):
        title = "Amazing science facts #shorts"
        result = _ensure_shorts_tag(title)
        # Lowercase #shorts is already present — #Shorts must not be appended
        assert "#Shorts" not in result
        assert "#shorts" in result


class TestBuildCredentials:
    def test_missing_env_vars_raises(self):
        env = {}
        with patch.dict(os.environ, env, clear=True):
            for var in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
                os.environ.pop(var, None)
            with pytest.raises(RuntimeError, match="Missing YouTube credentials"):
                _build_credentials()

    def test_missing_single_var_raises(self):
        env = {
            "YOUTUBE_CLIENT_ID": "cid",
            "YOUTUBE_CLIENT_SECRET": "csecret",
        }
        with patch.dict(os.environ, env, clear=True):
            os.environ.pop("YOUTUBE_REFRESH_TOKEN", None)
            with pytest.raises(RuntimeError, match="YOUTUBE_REFRESH_TOKEN"):
                _build_credentials()

    def test_credentials_built_with_valid_env(self):
        env = {
            "YOUTUBE_CLIENT_ID": "test-client-id",
            "YOUTUBE_CLIENT_SECRET": "test-client-secret",
            "YOUTUBE_REFRESH_TOKEN": "test-refresh-token",
        }
        with patch.dict(os.environ, env):
            with patch("youtube_uploader.google.auth.transport.requests.Request"):
                with patch("youtube_uploader.Credentials") as MockCreds:
                    mock_creds = MagicMock()
                    MockCreds.return_value = mock_creds

                    _build_credentials()

                    MockCreds.assert_called_once_with(
                        token=None,
                        refresh_token="test-refresh-token",
                        client_id="test-client-id",
                        client_secret="test-client-secret",
                        token_uri="https://oauth2.googleapis.com/token",
                        scopes=["https://www.googleapis.com/auth/youtube.upload"],
                    )
                    mock_creds.refresh.assert_called_once()
