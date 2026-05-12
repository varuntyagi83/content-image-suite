"""Tests for protagonist-mode handling in prompt_builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from prompt_builder import (
    FACE_TREATMENT_GENERIC,
    FACE_TREATMENT_NAMED,
    build_prompt,
    resolve_protagonist_mode,
)

ENGINE_DIR = Path(__file__).parent.parent
ENGINE_PATH = ENGINE_DIR / "scripts" / "engine.py"


class TestResolveProtagonistMode:
    """Direct tests of the auto-resolver."""

    def test_explicit_mode_passes_through(self):
        assert resolve_protagonist_mode("anything", "named") == "named"
        assert resolve_protagonist_mode("anything", "generic") == "generic"
        assert resolve_protagonist_mode("anything", "none") == "none"

    def test_named_from_founder_with_age(self):
        subj = "A founder, mid-30s, focused expression, building at a laptop"
        assert resolve_protagonist_mode(subj) == "named"

    def test_named_from_expression_marker(self):
        subj = "A woman in her late 20s mid-laugh at a kitchen table"
        assert resolve_protagonist_mode(subj) == "named"

    def test_named_from_explicit_specific_person(self):
        subj = "A specific man at a wooden bench, hands mid-cut on a chair"
        assert resolve_protagonist_mode(subj) == "named"

    def test_generic_from_generic_role(self):
        subj = "A marketer at a cluttered desk surrounded by screens"
        assert resolve_protagonist_mode(subj) == "generic"

    def test_generic_from_a_user(self):
        subj = "A user holding a phone with notifications cascading"
        assert resolve_protagonist_mode(subj) == "generic"

    def test_none_for_pure_object_scene(self):
        subj = "A vast empty filing cabinet drawer with a single screenshot at the bottom"
        assert resolve_protagonist_mode(subj) == "none"

    def test_none_for_landscape(self):
        subj = "A wooden desk covered in printed spreadsheets and a coffee mug"
        assert resolve_protagonist_mode(subj) == "none"


class TestBuildPromptProtagonistMode:
    """Verify the face-treatment hint is injected correctly."""

    def test_named_mode_adds_clear_face_hint(self):
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="centered-subject",
            subject="A founder, mid-30s, focused expression, building something at a laptop",
            engine_dir=ENGINE_DIR,
            protagonist_mode="named",
        )
        assert metadata["protagonist_mode_resolved"] == "named"
        assert "clearly visible" in prompt
        assert "recognizable as a specific person" in prompt

    def test_generic_mode_adds_partial_face_hint(self):
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="rule-of-thirds-left",
            subject="A marketer at a cluttered desk surrounded by monitors",
            engine_dir=ENGINE_DIR,
            protagonist_mode="generic",
        )
        assert metadata["protagonist_mode_resolved"] == "generic"
        assert "partial faces" in prompt or "abstracted features" in prompt
        # Should NOT contain the strong "recognizable as a specific person" directive
        assert "recognizable as a specific person" not in prompt

    def test_none_mode_adds_no_face_hint(self):
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="inline_2",
            style="editorial",
            palette_id="bone-and-rust",
            composition="negative-space-dominant",
            subject="A vast empty filing cabinet with a single screenshot at the bottom",
            engine_dir=ENGINE_DIR,
            protagonist_mode="none",
        )
        assert metadata["protagonist_mode_resolved"] == "none"
        # No protagonist hint anywhere in the prompt
        assert "clearly visible" not in prompt
        assert "partial faces" not in prompt

    def test_auto_mode_detects_named_from_subject(self):
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="centered-subject",
            subject="A founder, mid-30s, focused expression at a workshop bench",
            engine_dir=ENGINE_DIR,
            protagonist_mode="auto",
        )
        assert metadata["protagonist_mode_resolved"] == "named"
        assert "clearly visible" in prompt

    def test_auto_mode_detects_none_from_object_scene(self):
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="inline_2",
            style="editorial",
            palette_id="bone-and-rust",
            composition="negative-space-dominant",
            subject="A wooden desk covered in printed spreadsheets",
            engine_dir=ENGINE_DIR,
            protagonist_mode="auto",
        )
        assert metadata["protagonist_mode_resolved"] == "none"

    def test_named_overrides_generic_default(self):
        """Even if subject says 'marketer' (generic-leaning), if mode=named the prompt should get the strong face hint."""
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="centered-subject",
            subject="A marketer at a cluttered desk",
            engine_dir=ENGINE_DIR,
            protagonist_mode="named",
        )
        assert metadata["protagonist_mode_resolved"] == "named"
        assert "clearly visible" in prompt


class TestEngineCLIProtagonistMode:
    """Verify the engine CLI surfaces protagonist_mode_resolved."""

    def test_cli_includes_protagonist_mode_in_response(self):
        result = subprocess.run(
            [
                sys.executable, str(ENGINE_PATH), "build-prompt",
                "--platform", "medium", "--format", "hero",
                "--style", "editorial", "--palette", "bone-and-rust",
                "--composition", "centered-subject",
                "--subject", "A founder, mid-30s, focused expression at a desk",
                "--protagonist-mode", "auto",
            ],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        assert "protagonist_mode_resolved" in data
        assert data["protagonist_mode_resolved"] == "named"

    def test_cli_explicit_mode_overrides_auto(self):
        result = subprocess.run(
            [
                sys.executable, str(ENGINE_PATH), "build-prompt",
                "--platform", "medium", "--format", "hero",
                "--style", "editorial", "--palette", "bone-and-rust",
                "--composition", "centered-subject",
                "--subject", "A founder building something at a desk",
                "--protagonist-mode", "generic",
            ],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        # Even though subject says "founder" (which auto would resolve to named),
        # explicit generic mode wins.
        assert data["protagonist_mode_resolved"] == "generic"
