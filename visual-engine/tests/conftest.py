"""Pytest fixtures shared across all engine tests."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Make scripts/ importable for tests.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

ENGINE_DIR = Path(__file__).resolve().parent.parent  # visual-engine/


@pytest.fixture
def engine_dir():
    """Path to the visual-engine root."""
    return ENGINE_DIR


@pytest.fixture
def empty_manifest_path(tmp_path):
    """A path that doesn't exist yet — engine should auto-create."""
    return tmp_path / "manifest.json"


@pytest.fixture
def empty_manifest():
    """An empty in-memory manifest dict."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 2,
        "blog_owner": "@varuntyagi83",
        "created_at": now,
        "updated_at": now,
        "content_pieces": [],
    }


@pytest.fixture
def populated_manifest():
    """A manifest with several content pieces across platforms."""
    return {
        "schema_version": 2,
        "blog_owner": "@varuntyagi83",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-05-10T00:00:00Z",
        "content_pieces": [
            # Most recent first (sorted desc by first_seen_date)
            {
                "content_id": str(uuid.uuid4()),
                "canonical_title": "Cutting BigQuery Costs by 47%",
                "canonical_slug": "bigquery-cost-optimization",
                "first_seen_date": "2026-05-08",
                "subject_themes": ["server racks", "fuel gauge"],
                "shared_identity": {"style": "isometric", "palette_id": "electric-dusk"},
                "platform_outputs": {
                    "medium": {
                        "format": "hero",
                        "generated_at": "2026-05-08",
                        "compositions": {"hero": "centered-subject",
                                         "inline_1": "rule-of-thirds-left"},
                        "prompts": {"hero": "An isometric server rack scene...",
                                    "inline_1": "Wide shot of data center..."},
                        "image_paths": {},
                        "notes": "",
                    },
                    "linkedin": None,
                    "twitter": None,
                    "instagram": None,
                    "meta": None,
                },
            },
            {
                "content_id": str(uuid.uuid4()),
                "canonical_title": "Why Your AI Strategy is Probably Wrong",
                "canonical_slug": "ai-strategy-wrong",
                "first_seen_date": "2026-04-25",
                "subject_themes": ["confused executive", "whiteboard chaos"],
                "shared_identity": {"style": "editorial", "palette_id": "bone-and-rust"},
                "platform_outputs": {
                    "medium": {
                        "format": "hero",
                        "generated_at": "2026-04-25",
                        "compositions": {"hero": "rule-of-thirds-right",
                                         "inline_1": "split-frame"},
                        "prompts": {"hero": "...", "inline_1": "..."},
                        "image_paths": {},
                        "notes": "",
                    },
                    "linkedin": {
                        "format": "cover",
                        "generated_at": "2026-04-26",
                        "compositions": {"cover": "rule-of-thirds-right"},
                        "prompts": {"cover": "..."},
                        "image_paths": {},
                        "notes": "",
                    },
                    "twitter": None, "instagram": None, "meta": None,
                },
            },
            {
                "content_id": str(uuid.uuid4()),
                "canonical_title": "Notes from Berlin Tech Week",
                "canonical_slug": "berlin-tech-week-notes",
                "first_seen_date": "2026-04-10",
                "subject_themes": ["conference floor", "name badge"],
                "shared_identity": {"style": "cinematic", "palette_id": "monochrome-noir"},
                "platform_outputs": {
                    "medium": {
                        "format": "hero",
                        "generated_at": "2026-04-10",
                        "compositions": {"hero": "silhouette"},
                        "prompts": {"hero": "..."},
                        "image_paths": {},
                        "notes": "",
                    },
                    "twitter": {
                        "format": "single",
                        "generated_at": "2026-04-10",
                        "compositions": {"single": "centered-subject"},
                        "prompts": {"single": "..."},
                        "image_paths": {},
                        "notes": "",
                    },
                    "linkedin": None, "instagram": None, "meta": None,
                },
            },
        ],
    }


@pytest.fixture
def manifest_file(tmp_path, populated_manifest):
    """A populated manifest saved to a temp file."""
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(populated_manifest, indent=2))
    return path


@pytest.fixture
def instagram_consistency_manifest():
    """Manifest with enough Instagram history to trigger consistency mode."""
    # Need at least 3 IG posts to trigger consistency
    pieces = []
    for i, (title, slug, style, palette, comp) in enumerate([
        ("IG Post One", "ig-post-one", "cinematic", "monochrome-noir", "centered-subject"),
        ("IG Post Two", "ig-post-two", "cinematic", "monochrome-noir", "rule-of-thirds-left"),
        ("IG Post Three", "ig-post-three", "cinematic", "monochrome-noir", "negative-space-dominant"),
        ("IG Post Four", "ig-post-four", "cinematic", "monochrome-noir", "frame-within-frame"),
    ]):
        pieces.append({
            "content_id": str(uuid.uuid4()),
            "canonical_title": title,
            "canonical_slug": slug,
            "first_seen_date": f"2026-04-{20 - i:02d}",
            "subject_themes": [f"theme-{i}"],
            "shared_identity": {"style": style, "palette_id": palette},
            "platform_outputs": {
                "instagram": {
                    "format": "feed",
                    "generated_at": f"2026-04-{20 - i:02d}",
                    "compositions": {"feed": comp},
                    "prompts": {"feed": "..."},
                    "image_paths": {},
                    "notes": "",
                },
                "medium": None, "linkedin": None, "twitter": None, "meta": None,
            },
        })
    return {
        "schema_version": 2,
        "blog_owner": "",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-04-20T00:00:00Z",
        "content_pieces": pieces,
    }
