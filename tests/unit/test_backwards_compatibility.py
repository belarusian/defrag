"""Test backwards compatibility with old index formats."""

import json
import tempfile
from pathlib import Path

from defrag.semantic import ConceptMatch, SemanticIndex


def test_load_old_index_without_validated_field():
    """Test that old indexes without 'validated' field load correctly."""
    # Simulate old index format (no validated field in matches)
    old_index_data = {
        "concepts": {
            "doc:README.md:intro": {
                "id": "doc:README.md:intro",
                "source": "README.md",
                "source_type": "doc",
                "location": "intro",
                "description": "Introduction section",
                "keywords": ["intro", "overview"],
                "line_range": [1, 10],
                "raw_content": "# Introduction\n...",
            }
        },
        "matches": [
            {
                "code_concept_id": "code:app.py:main",
                "doc_concept_id": "doc:README.md:intro",
                "confidence": 0.85,
                "reasoning": "Matches conceptually",
                "physical_link_valid": True,
                "suggested_link": "app.py:10-20",
                "iterations": 1,
                # NOTE: No 'validated' field - this is old format
            }
        ],
    }

    # Write old index to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(old_index_data, f)
        tmp_path = f.name

    try:
        # Load old index
        index = SemanticIndex.load(tmp_path)

        # Verify it loaded correctly
        assert len(index.matches) == 1
        match = index.matches[0]
        assert match.code_concept_id == "code:app.py:main"
        assert match.confidence == 0.85
        assert match.validated is False  # Should default to False
    finally:
        Path(tmp_path).unlink()


def test_load_old_index_without_metadata():
    """Test that old indexes without metadata load correctly."""
    old_index_data = {
        "concepts": {},
        "matches": [],
        # NOTE: No 'metadata' or 'version' field
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(old_index_data, f)
        tmp_path = f.name

    try:
        index = SemanticIndex.load(tmp_path)

        # Should have default metadata
        assert "version" in index.metadata
        assert index.metadata["version"] == "1.0"
    finally:
        Path(tmp_path).unlink()


def test_load_old_index_with_top_level_version():
    """Test that old indexes with version at top level load correctly."""
    old_index_data = {
        "version": "0.9",  # Old format: version at top level
        "concepts": {},
        "matches": [],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(old_index_data, f)
        tmp_path = f.name

    try:
        index = SemanticIndex.load(tmp_path)

        # Should migrate version to metadata
        assert index.metadata["version"] == "0.9"
    finally:
        Path(tmp_path).unlink()


def test_new_index_saves_with_metadata():
    """Test that new indexes save with metadata."""
    index = SemanticIndex()
    index.metadata["custom_field"] = "test_value"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        # Load and verify metadata persisted
        loaded = SemanticIndex.load(tmp_path)
        assert loaded.metadata["version"] == "1.0"
        assert loaded.metadata["custom_field"] == "test_value"
    finally:
        Path(tmp_path).unlink()


def test_atomic_save_creates_no_tmp_file():
    """Test that atomic save cleans up temporary file."""
    index = SemanticIndex()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        # Verify main file exists
        assert Path(tmp_path).exists()

        # Verify .tmp file was cleaned up
        assert not Path(f"{tmp_path}.tmp").exists()
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        Path(f"{tmp_path}.tmp").unlink(missing_ok=True)


def test_validated_field_roundtrip():
    """Test that validated field is preserved through save/load."""
    index = SemanticIndex()

    # Add match with validated=True
    match = ConceptMatch(
        code_concept_id="code:app.py:func",
        doc_concept_id="doc:README.md:section",
        confidence=0.9,
        reasoning="Test",
        validated=True,
    )
    index.add_match(match)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)
        loaded = SemanticIndex.load(tmp_path)

        assert len(loaded.matches) == 1
        assert loaded.matches[0].validated is True
    finally:
        Path(tmp_path).unlink()
