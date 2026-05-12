"""Integration test for generate_image() with fal-client mocked.

Exercises the full path from input validation through subscribe() to
result parsing and image download — but with fal_client and urlopen
both replaced by stubs.

This catches:
- Wrong arg names passed to fal_client.subscribe
- Wrong response shape assumed
- Image download issues
- Retry logic
- Error classification on actual exceptions
"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import fal_client_wrapper
from fal_client_wrapper import GenerationError, generate_image


# A 1500-byte fake PNG payload (real PNG signature so anything that
# sniffs the magic bytes is satisfied).
FAKE_PNG_HEADER = b'\x89PNG\r\n\x1a\n' + b'\x00' * 1500


class FakeHttpResponse:
    """Pretend to be the object returned by urllib.request.urlopen."""

    def __init__(self, payload, status=200, content_type="image/png"):
        self._payload = payload
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


def install_fake_fal_client(success_result=None, raises=None):
    """Patch sys.modules so the wrapper's lazy import finds our fake."""
    fake = MagicMock()
    if raises:
        fake.subscribe = MagicMock(side_effect=raises)
    else:
        result = success_result or {
            "images": [{"url": "https://fal.media/files/fake.png", "width": 1920, "height": 1080}],
        }
        fake.subscribe = MagicMock(return_value=result)
    sys.modules["fal_client"] = fake
    return fake


class TestGenerateImageMocked:
    def test_happy_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "fake")
        fake_fal = install_fake_fal_client()

        with patch("fal_client_wrapper.urlopen") as urlopen_mock:
            urlopen_mock.return_value = FakeHttpResponse(FAKE_PNG_HEADER)
            result = generate_image(
                prompt="A long enough prompt to pass validation. " * 2,
                aspect_ratio="16:9",
                output_path=tmp_path / "out.png",
            )

        assert result["status"] == "ok"
        assert result["aspect_ratio_used"] == "16:9"
        assert result["aspect_ratio_was_remapped"] is False
        assert (tmp_path / "out.png").exists()
        assert (tmp_path / "out.png").read_bytes().startswith(b'\x89PNG')

        # Verify subscribe was called with the right kwargs
        call_kwargs = fake_fal.subscribe.call_args
        assert call_kwargs.args[0] == "fal-ai/gemini-3-pro-image-preview"
        assert call_kwargs.kwargs["arguments"]["aspect_ratio"] == "16:9"
        assert call_kwargs.kwargs["arguments"]["num_images"] == 1

    def test_remaps_1_91_to_16_9(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "fake")
        fake_fal = install_fake_fal_client()

        with patch("fal_client_wrapper.urlopen") as urlopen_mock:
            urlopen_mock.return_value = FakeHttpResponse(FAKE_PNG_HEADER)
            result = generate_image(
                prompt="A long enough prompt to pass validation. " * 2,
                aspect_ratio="1.91:1",
                output_path=tmp_path / "out.png",
            )

        assert result["aspect_ratio_used"] == "16:9"
        assert result["aspect_ratio_was_remapped"] is True
        assert result["aspect_ratio_requested"] == "1.91:1"
        # The actual fal.ai call should have used 16:9, not 1.91:1
        assert fake_fal.subscribe.call_args.kwargs["arguments"]["aspect_ratio"] == "16:9"

    def test_fallback_to_subscribe_without_client_timeout(self, tmp_path, monkeypatch):
        """Older fal-client doesn't accept client_timeout; we should retry without it."""
        monkeypatch.setenv("FAL_KEY", "fake")

        call_count = [0]
        def subscribe_with_compat_check(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1 and "client_timeout" in kwargs:
                raise TypeError("subscribe() got an unexpected keyword argument 'client_timeout'")
            return {"images": [{"url": "https://fal.media/files/fake.png"}]}

        fake_fal = MagicMock()
        fake_fal.subscribe = MagicMock(side_effect=subscribe_with_compat_check)
        sys.modules["fal_client"] = fake_fal

        with patch("fal_client_wrapper.urlopen") as urlopen_mock:
            urlopen_mock.return_value = FakeHttpResponse(FAKE_PNG_HEADER)
            result = generate_image(
                prompt="A long enough prompt to pass validation. " * 2,
                aspect_ratio="16:9",
                output_path=tmp_path / "out.png",
            )
        assert result["status"] == "ok"
        assert call_count[0] == 2

    def test_rate_limit_then_success(self, tmp_path, monkeypatch):
        """On rate-limit, retry once after a pause."""
        monkeypatch.setenv("FAL_KEY", "fake")

        attempts = [0]
        def flaky_subscribe(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                raise RuntimeError("HTTP 429 rate limit exceeded")
            return {"images": [{"url": "https://fal.media/files/fake.png"}]}

        fake_fal = MagicMock()
        fake_fal.subscribe = MagicMock(side_effect=flaky_subscribe)
        sys.modules["fal_client"] = fake_fal

        with patch("fal_client_wrapper.urlopen") as urlopen_mock, \
             patch("fal_client_wrapper.time.sleep"):  # don't actually sleep 5s in tests
            urlopen_mock.return_value = FakeHttpResponse(FAKE_PNG_HEADER)
            result = generate_image(
                prompt="A long enough prompt to pass validation. " * 2,
                aspect_ratio="16:9",
                output_path=tmp_path / "out.png",
            )
        assert result["status"] == "ok"
        assert attempts[0] == 2

    def test_policy_violation_no_retry(self, tmp_path, monkeypatch):
        """Policy violations should NOT trigger retry — that's not transient."""
        monkeypatch.setenv("FAL_KEY", "fake")

        attempts = [0]
        def policy_blocker(*args, **kwargs):
            attempts[0] += 1
            raise RuntimeError("Content blocked by safety policy")

        fake_fal = MagicMock()
        fake_fal.subscribe = MagicMock(side_effect=policy_blocker)
        sys.modules["fal_client"] = fake_fal

        with pytest.raises(GenerationError) as exc:
            generate_image(
                prompt="A long enough prompt to pass validation. " * 2,
                aspect_ratio="16:9",
                output_path=tmp_path / "out.png",
            )
        assert exc.value.error_type == "policy_violation"
        assert attempts[0] == 1  # No retry

    def test_auth_error_no_retry(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "fake")

        def auth_failure(*args, **kwargs):
            raise RuntimeError("HTTP 401 Unauthorized")

        fake_fal = MagicMock()
        fake_fal.subscribe = MagicMock(side_effect=auth_failure)
        sys.modules["fal_client"] = fake_fal

        with pytest.raises(GenerationError) as exc:
            generate_image(
                prompt="A long enough prompt to pass validation. " * 2,
                aspect_ratio="16:9",
                output_path=tmp_path / "out.png",
            )
        assert exc.value.error_type == "auth"

    def test_non_image_content_type_caught(self, tmp_path, monkeypatch):
        """If fal returns an error page (text/html), we should refuse to save it."""
        monkeypatch.setenv("FAL_KEY", "fake")
        install_fake_fal_client()

        with patch("fal_client_wrapper.urlopen") as urlopen_mock:
            urlopen_mock.return_value = FakeHttpResponse(
                b"<html>error page</html>" * 100,
                content_type="text/html",
            )
            with pytest.raises(GenerationError) as exc:
                generate_image(
                    prompt="A long enough prompt to pass validation. " * 2,
                    aspect_ratio="16:9",
                    output_path=tmp_path / "out.png",
                )
            assert exc.value.error_type == "download_failed"
            assert "non-image" in exc.value.message.lower()

    def test_tiny_payload_caught(self, tmp_path, monkeypatch):
        """Suspiciously small payload (likely an error stub) should be refused."""
        monkeypatch.setenv("FAL_KEY", "fake")
        install_fake_fal_client()

        with patch("fal_client_wrapper.urlopen") as urlopen_mock:
            urlopen_mock.return_value = FakeHttpResponse(b"\x89PNG\r\n\x1a\n" + b'\x00' * 20)
            with pytest.raises(GenerationError) as exc:
                generate_image(
                    prompt="A long enough prompt to pass validation. " * 2,
                    aspect_ratio="16:9",
                    output_path=tmp_path / "out.png",
                )
            assert exc.value.error_type == "download_failed"

    def test_no_partial_file_left_behind_on_failure(self, tmp_path, monkeypatch):
        """If download fails, no .partial file should remain."""
        monkeypatch.setenv("FAL_KEY", "fake")
        install_fake_fal_client()

        from urllib.error import URLError

        with patch("fal_client_wrapper.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = URLError("network down")
            with pytest.raises(GenerationError):
                generate_image(
                    prompt="A long enough prompt to pass validation. " * 2,
                    aspect_ratio="16:9",
                    output_path=tmp_path / "out.png",
                )

        # No .partial or main file should exist
        assert not (tmp_path / "out.png").exists()
        assert not (tmp_path / "out.png.partial").exists()


@pytest.fixture(autouse=True)
def cleanup_fal_client():
    """Ensure each test starts without a cached fake fal_client."""
    yield
    sys.modules.pop("fal_client", None)
    # Force reimport on next call
    fal_client_wrapper.import_fal_client.__wrapped__ = None if hasattr(
        fal_client_wrapper.import_fal_client, "__wrapped__"
    ) else None
