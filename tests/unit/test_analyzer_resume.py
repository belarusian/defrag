"""Test SemanticAnalyzer resume functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from defrag.analyzer import SemanticAnalyzer
from defrag.semantic import Concept, ConceptMatch, SemanticIndex


def test_analyzer_resumes_from_existing_index(capsys):
    """Test that analyzer can resume from an existing index."""
    # Create an existing index with some data
    index = SemanticIndex()
    index.add_concept(
        Concept(
            id="doc:README.md:intro",
            source="README.md",
            source_type="doc",
            location="intro",
            description="Introduction",
            keywords=["intro"],
        )
    )
    index.add_match(
        ConceptMatch(
            code_concept_id="code:app.py:main",
            doc_concept_id="doc:README.md:intro",
            confidence=0.85,
            reasoning="Test match",
        )
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        # Save the index
        index.save(tmp_path)

        # Resume from the index (no LLM client needed for this test)
        analyzer = SemanticAnalyzer(llm_client=MagicMock(), root_dir=".", resume_from=tmp_path)

        # Verify data was loaded
        assert len(analyzer.index.concepts) == 1
        assert len(analyzer.index.matches) == 1
        assert "doc:README.md:intro" in analyzer.index.concepts

        # Check console output
        captured = capsys.readouterr()
        assert "Resumed from existing index" in captured.out
        assert "1 concepts, 1 matches" in captured.out
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_analyzer_starts_fresh_if_no_resume_path():
    """Test that analyzer starts with empty index when not resuming."""
    analyzer = SemanticAnalyzer(llm_client=MagicMock(), root_dir=".", resume_from=None)

    assert len(analyzer.index.concepts) == 0
    assert len(analyzer.index.matches) == 0


def test_analyzer_starts_fresh_if_resume_path_nonexistent():
    """Test that analyzer starts fresh if resume path doesn't exist."""
    analyzer = SemanticAnalyzer(
        llm_client=MagicMock(), root_dir=".", resume_from="/nonexistent/path.json"
    )

    assert len(analyzer.index.concepts) == 0
    assert len(analyzer.index.matches) == 0


def test_analyzer_raises_on_malformed_index():
    """Test that analyzer raises helpful error for corrupted index."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json }")
        tmp_path = f.name

    try:
        # Should raise ValueError with helpful message
        import pytest

        with pytest.raises(ValueError, match="Failed to load index"):
            SemanticAnalyzer(llm_client=MagicMock(), root_dir=".", resume_from=tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_analyzer_preserves_metadata_on_resume():
    """Test that metadata is preserved when resuming."""
    index = SemanticIndex()
    index.metadata["custom_field"] = "test_value"
    index.metadata["file_hashes"] = {"app.py": "abc123"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        analyzer = SemanticAnalyzer(llm_client=MagicMock(), root_dir=".", resume_from=tmp_path)

        assert analyzer.index.metadata["custom_field"] == "test_value"
        assert analyzer.index.metadata["file_hashes"]["app.py"] == "abc123"
    finally:
        Path(tmp_path).unlink(missing_ok=True)
