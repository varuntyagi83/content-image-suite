"""
visual_engine
=============

Shared library for the content-image-suite. Used by the orchestrator
and by all platform-specific image generator skills.

Main exports:
    - constants: ALL_STYLES, ALL_PALETTES, ALL_COMPOSITIONS, etc.
    - platforms: PlatformConfig registry, get_platform()
    - rotation: compute_rotation(), compute_shared_identity()
    - manifest_io: load_manifest(), save_manifest(), upsert_*()
    - prompt_builder: build_prompt()
    - fal_client_wrapper: generate_image(), GenerationError

Platform skills should import via the engine's CLI or by adding the
scripts/ directory to sys.path.
"""

__version__ = "1.0.0"
