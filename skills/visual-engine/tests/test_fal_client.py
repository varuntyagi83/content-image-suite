"""Tests for fal_client_wrapper.py helper functions.

These exercise the parts of the module that don't require network access:
- aspect ratio normalization
- error classification
- environment checks
- result parsing
- input validation

The actual generate_image() function calls fal.ai and is not tested here.
That's covered by a real smoke test on the user's machine.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from fal_client_wrapper import (
    ASPECT_RATIOS_SUPPORTED, ASPECT_RATIO_FALLBACK,
    GenerationError, _extract_image_url, check_environment,
    classify_error, generate_image, normalize_aspect_ratio,
)


class TestAspectRatioNormalization:
    def test_supported_ratio_unchanged(self):
        for ratio in ["16:9", "1:1", "9:16", "4:3", "3:2", "5:4", "4:5", "3:4", "2:3", "21:9", "auto"]:
            result, remapped = normalize_aspect_ratio(ratio)
            assert result == ratio
            assert remapped is False

    def test_1_91_to_1_falls_back_to_16_9(self):
        result, remapped = normalize_aspect_ratio("1.91:1")
        assert result == "16:9"
        assert remapped is True

    def test_unknown_ratio_falls_back_to_auto(self):
        result, remapped = normalize_aspect_ratio("7:13")
        assert result == "auto"
        assert remapped is True

    def test_all_fallback_targets_are_supported(self):
        """Every fallback target must itself be in the supported set."""
        for source, target in ASPECT_RATIO_FALLBACK.items():
            assert target in ASPECT_RATIOS_SUPPORTED, (
                f"Fallback {source} -> {target} but {target} is not supported"
            )


class TestErrorClassification:
    def test_rate_limit(self):
        err_type, msg = classify_error(Exception("HTTP 429 rate limit exceeded"))
        assert err_type == "rate_limit"

    def test_timeout(self):
        err_type, msg = classify_error(TimeoutError("request timed out"))
        assert err_type == "timeout"

    def test_policy_violation(self):
        err_type, msg = classify_error(Exception("Content rejected by safety filter"))
        assert err_type == "policy_violation"

    def test_policy_blocked(self):
        err_type, msg = classify_error(Exception("Request blocked by moderation"))
        assert err_type == "policy_violation"

    def test_auth_401(self):
        err_type, _ = classify_error(Exception("HTTP 401 Unauthorized"))
        assert err_type == "auth"

    def test_auth_403(self):
        err_type, _ = classify_error(Exception("Forbidden access"))
        assert err_type == "auth"

    def test_auth_invalid_key(self):
        err_type, _ = classify_error(Exception("Invalid API key"))
        assert err_type == "auth"

    def test_endpoint_not_found(self):
        err_type, _ = classify_error(Exception("HTTP 404 endpoint not found"))
        assert err_type == "invalid_request"

    def test_bad_aspect_ratio(self):
        err_type, _ = classify_error(Exception("HTTP 400 invalid aspect_ratio value"))
        assert err_type == "invalid_request"

    def test_network(self):
        err_type, _ = classify_error(Exception("Connection refused"))
        assert err_type == "network"

    def test_dns_failure(self):
        err_type, _ = classify_error(Exception("Could not resolve hostname"))
        assert err_type == "network"

    def test_unknown_falls_through(self):
        err_type, _ = classify_error(Exception("something else weird"))
        assert err_type == "unknown"

    def test_fal_typed_timeout(self):
        # Simulate fal-client's typed FalClientTimeoutError by exception class name
        class FalClientTimeoutError(Exception):
            pass
        err_type, _ = classify_error(FalClientTimeoutError("client timeout"))
        assert err_type == "timeout"


class TestExtractImageUrl:
    def test_valid_response(self):
        result = {"images": [{"url": "https://fal.media/files/abc.png"}]}
        url = _extract_image_url(result)
        assert url == "https://fal.media/files/abc.png"

    def test_non_dict_response_raises(self):
        with pytest.raises(GenerationError) as exc:
            _extract_image_url("not a dict")
        assert exc.value.error_type == "unknown"

    def test_no_images_key(self):
        with pytest.raises(GenerationError) as exc:
            _extract_image_url({"foo": "bar"})
        assert "no images" in exc.value.message.lower()

    def test_empty_images_list(self):
        with pytest.raises(GenerationError):
            _extract_image_url({"images": []})

    def test_images_not_a_list(self):
        with pytest.raises(GenerationError):
            _extract_image_url({"images": "not-a-list"})

    def test_image_entry_not_dict(self):
        with pytest.raises(GenerationError):
            _extract_image_url({"images": ["url-as-string"]})

    def test_image_dict_missing_url(self):
        with pytest.raises(GenerationError):
            _extract_image_url({"images": [{"width": 1024}]})

    def test_url_is_empty_string(self):
        with pytest.raises(GenerationError):
            _extract_image_url({"images": [{"url": ""}]})


class TestGenerateImageValidation:
    """generate_image() input validation (raises BEFORE any API call)."""

    def test_short_prompt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "fake-key")
        with pytest.raises(GenerationError) as exc:
            generate_image(
                prompt="too short",
                aspect_ratio="16:9",
                output_path=tmp_path / "x.png",
            )
        assert exc.value.error_type == "invalid_prompt"

    def test_overly_long_prompt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "fake-key")
        with pytest.raises(GenerationError) as exc:
            generate_image(
                prompt="x" * 4001,
                aspect_ratio="16:9",
                output_path=tmp_path / "x.png",
            )
        assert exc.value.error_type == "invalid_prompt"

    def test_missing_fal_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FAL_KEY", raising=False)
        with pytest.raises(GenerationError) as exc:
            generate_image(
                prompt="A" * 50,
                aspect_ratio="16:9",
                output_path=tmp_path / "x.png",
            )
        assert exc.value.error_type == "fal_key_missing"

    def test_bad_num_images(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "fake-key")
        with pytest.raises(GenerationError) as exc:
            generate_image(
                prompt="A" * 50,
                aspect_ratio="16:9",
                output_path=tmp_path / "x.png",
                num_images=99,
            )
        assert exc.value.error_type == "invalid_request"


class TestCheckEnvironment:
    def test_returns_key_when_set(self, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "my-secret-key")
        assert check_environment() == "my-secret-key"

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("FAL_KEY", raising=False)
        assert check_environment() is None
