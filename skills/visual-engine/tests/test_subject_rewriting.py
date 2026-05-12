"""Tests for the expanded text-leak prevention layer.

Covers:
- New detection cases (ALL-CAPS words, time strings, text-rendering verbs, UI labels)
- The subject rewriter substitutes the textual cues correctly
- The build_prompt response now includes subject_was_rewritten and effective_subject
"""
from __future__ import annotations

from pathlib import Path

import pytest

from prompt_builder import (
    build_prompt,
    detect_label_risk,
    rewrite_subject_to_remove_text_cues,
)

ENGINE_DIR = Path(__file__).parent.parent


class TestExpandedDetection:
    """The expanded detect_label_risk catches more failure modes."""

    def test_all_caps_word_detected(self):
        # The INSPIRATION leak from the previous run.
        subject = "An overhead view of a desk with an INSPIRATION folder partially visible"
        detected, reason = detect_label_risk(subject)
        assert detected is True
        assert "INSPIRATION" in reason

    def test_time_string_with_am_detected(self):
        # The 4:30 AM leak from the previous run.
        subject = "A marketer collapsed at 4:30 AM, exhausted"
        detected, reason = detect_label_risk(subject)
        assert detected is True
        assert "time string" in reason.lower()

    def test_time_string_24h_detected(self):
        subject = "An office at 14:30, half-empty desks"
        detected, reason = detect_label_risk(subject)
        assert detected is True

    def test_text_verb_says_detected(self):
        subject = "A whiteboard with arrows that says SHIP IT in red marker"
        detected, reason = detect_label_risk(subject)
        assert detected is True

    def test_text_verb_labeled_detected(self):
        subject = "A folder labeled Q3 Reports on a wooden desk"
        detected, reason = detect_label_risk(subject)
        assert detected is True

    def test_ui_label_detected(self):
        subject = "A laptop screen showing the Settings panel open"
        detected, reason = detect_label_risk(subject)
        assert detected is True

    def test_short_acronyms_not_flagged(self):
        """3-letter acronyms like KPI, UI, CSV are common and shouldn't trigger."""
        for subject in [
            "A dashboard showing KPI trends",
            "A UI mockup pinned to corkboard",
            "A CSV file open in a spreadsheet program",
        ]:
            detected, _ = detect_label_risk(subject)
            assert detected is False, f"False positive on: {subject}"

    def test_normal_prose_with_capitals_not_flagged(self):
        """Standard prose with normal capitalization should pass."""
        subject = "A teenager on a couch staring at a phone, blue light on her face"
        detected, _ = detect_label_risk(subject)
        assert detected is False


class TestSubjectRewriter:
    """rewrite_subject_to_remove_text_cues replaces textual hints with visual ones."""

    def test_all_caps_replaced_with_illegible(self):
        original = "A folder labeled INSPIRATION sitting on a desk"
        rewritten = rewrite_subject_to_remove_text_cues(original)
        assert "INSPIRATION" not in rewritten
        assert "illegible" in rewritten.lower()

    def test_time_string_replaced(self):
        original = "A man at 4:30 AM hunched over his laptop"
        rewritten = rewrite_subject_to_remove_text_cues(original)
        assert "4:30" not in rewritten
        assert "illegible" in rewritten.lower()

    def test_quoted_text_replaced(self):
        original = 'A neon sign that says "OPEN" in a shop window'
        rewritten = rewrite_subject_to_remove_text_cues(original)
        # Both the quoted "OPEN" and the "that says" pattern should be neutralized
        assert "OPEN" not in rewritten
        assert "says" not in rewritten

    def test_says_phrase_replaced(self):
        original = "A whiteboard that says SHIP IT in red marker"
        rewritten = rewrite_subject_to_remove_text_cues(original)
        assert "says" not in rewritten
        assert "illegible text" in rewritten

    def test_normal_subject_unchanged(self):
        original = "A teenager on a couch staring at a phone"
        rewritten = rewrite_subject_to_remove_text_cues(original)
        # No textual cues, so it should pass through largely unchanged.
        assert rewritten == original

    def test_no_double_spaces_in_output(self):
        original = "A folder labeled INSPIRATION at 4:30 AM"
        rewritten = rewrite_subject_to_remove_text_cues(original)
        assert "  " not in rewritten


class TestBuildPromptIntegratesRewrite:
    """build_prompt applies the rewriter when label risk is detected."""

    def test_subject_rewritten_when_risk_detected(self):
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="centered-subject",
            subject="An overhead view of a desk with an INSPIRATION folder partially visible, never opened",
            engine_dir=ENGINE_DIR,
        )
        assert metadata["label_risk_detected"] is True
        assert metadata["subject_was_rewritten"] is True
        assert metadata["effective_subject"]
        # The rendered prompt should NOT contain the all-caps word.
        assert "INSPIRATION" not in prompt
        # The strong negative is still added
        assert "CRITICAL" in prompt or "zero text" in prompt.lower()

    def test_subject_not_rewritten_when_no_risk(self):
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="centered-subject",
            subject="A teenager on a couch staring at a phone in a dim room",
            engine_dir=ENGINE_DIR,
        )
        assert metadata["label_risk_detected"] is False
        assert metadata["subject_was_rewritten"] is False
        assert metadata["effective_subject"] == ""

    def test_custom_negatives_disables_rewrite(self):
        """If the caller passes custom_negatives, they take full control —
        the rewriter is skipped (caller is the expert)."""
        original_subject = "A folder labeled INSPIRATION at 4:30 AM"
        prompt, _, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="centered-subject",
            subject=original_subject,
            engine_dir=ENGINE_DIR,
            custom_negatives="No animals.",
        )
        # detect_label_risk still runs and reports True
        assert metadata["label_risk_detected"] is True
        # But the subject was NOT rewritten because custom_negatives was passed
        assert metadata["subject_was_rewritten"] is False
        # Custom negative is used; INSPIRATION still in the prompt because no rewrite
        assert "No animals." in prompt
        assert "INSPIRATION" in prompt
