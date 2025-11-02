"""Test file change detection and reprocessing."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from defrag.analyzer import SemanticAnalyzer
from defrag.semantic import Concept, SemanticIndex, compute_file_hash


def test_compute_file_hash():
    """Test file hash computation."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        f.write("# Test\nContent here")
        tmp_path = f.name

    try:
        # Compute hash
        hash1 = compute_file_hash(tmp_path, root_dir="")
        assert hash1 is not None
        assert len(hash1) == 64  # SHA256 hex digest

        # Same file should have same hash
        hash2 = compute_file_hash(tmp_path, root_dir="")
        assert hash1 == hash2

        # Modified file should have different hash
        with open(tmp_path, "a") as f:
            f.write("\nMore content")

        hash3 = compute_file_hash(tmp_path, root_dir="")
        assert hash3 != hash1
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_file_hash_storage_in_metadata():
    """Test that file hashes are stored in index metadata."""
    index = SemanticIndex()

    # Store hash
    index.update_file_hash("README.md", "abc123")
    assert index.get_file_hash("README.md") == "abc123"

    # Store another
    index.update_file_hash("app.py", "def456")
    assert index.get_file_hash("app.py") == "def456"

    # Original should still be there
    assert index.get_file_hash("README.md") == "abc123"


def test_file_hash_persists_across_save_load():
    """Test that file hashes survive save/load cycle."""
    index = SemanticIndex()
    index.update_file_hash("README.md", "abc123")
    index.update_file_hash("app.py", "def456")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        loaded = SemanticIndex.load(tmp_path)
        assert loaded.get_file_hash("README.md") == "abc123"
        assert loaded.get_file_hash("app.py") == "def456"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_remove_concepts_for_file():
    """Test removing all concepts for a specific file."""
    index = SemanticIndex()

    # Add concepts for multiple files
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
    index.add_concept(
        Concept(
            id="doc:README.md:usage",
            source="README.md",
            source_type="doc",
            location="usage",
            description="Usage guide",
            keywords=["usage"],
        )
    )
    index.add_concept(
        Concept(
            id="doc:GUIDE.md:intro",
            source="GUIDE.md",
            source_type="doc",
            location="intro",
            description="Guide intro",
            keywords=["guide"],
        )
    )

    # Remove README.md concepts
    index.remove_concepts_for_file("README.md", "doc")

    # Only GUIDE.md should remain
    assert len(index.concepts) == 1
    assert "doc:GUIDE.md:intro" in index.concepts
    assert "doc:README.md:intro" not in index.concepts
    assert "doc:README.md:usage" not in index.concepts


def test_remove_concepts_removes_matches():
    """Test that removing concepts also removes their matches."""
    from defrag.semantic import ConceptMatch

    index = SemanticIndex()

    # Add code and doc concepts
    index.add_concept(
        Concept(
            id="code:app.py:main",
            source="app.py",
            source_type="code",
            location="main",
            description="Main function",
            keywords=["main"],
        )
    )
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

    # Add match
    index.add_match(
        ConceptMatch(
            code_concept_id="code:app.py:main",
            doc_concept_id="doc:README.md:intro",
            confidence=0.85,
            reasoning="Test match",
        )
    )

    assert len(index.matches) == 1

    # Remove code concepts - should also remove match
    index.remove_concepts_for_file("app.py", "code")

    assert len(index.concepts) == 1  # Only doc concept remains
    assert len(index.matches) == 0  # Match should be gone


def test_analyzer_detects_file_changes(capsys):
    """Test that analyzer detects and reprocesses changed files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "README.md"
        doc_path.write_text("# Introduction\nOriginal content")

        # First analysis
        mock_llm = MagicMock()
        mock_llm.extract_doc_concept.return_value = {
            "description": "Original description",
            "keywords": ["original"],
        }

        analyzer = SemanticAnalyzer(llm_client=mock_llm, root_dir=tmpdir)

        with patch("defrag.analyzer.extract_markdown_sections") as mock_extract:
            mock_extract.return_value = [("Introduction", "Original content", 1, 2)]
            analyzer.analyze_documentation(["README.md"], verbose=True)

        # Should have processed once
        assert mock_llm.extract_doc_concept.call_count == 1
        assert len(analyzer.index.concepts) == 1

        # Check file hash was stored
        assert analyzer.index.get_file_hash("README.md") is not None

        # Save index
        index_path = Path(tmpdir) / "index.json"
        analyzer.index.save(str(index_path))

        # Modify the file
        doc_path.write_text("# Introduction\nNew content here!")

        # Create new analyzer (resume mode)
        mock_llm2 = MagicMock()
        mock_llm2.extract_doc_concept.return_value = {
            "description": "New description",
            "keywords": ["new"],
        }

        analyzer2 = SemanticAnalyzer(
            llm_client=mock_llm2, root_dir=tmpdir, resume_from=str(index_path)
        )

        with patch("defrag.analyzer.extract_markdown_sections") as mock_extract2:
            mock_extract2.return_value = [("Introduction", "New content here!", 1, 2)]
            analyzer2.analyze_documentation(["README.md"], verbose=True)

        # Should detect change and reprocess
        assert mock_llm2.extract_doc_concept.call_count == 1

        # Check output
        captured = capsys.readouterr()
        assert "File changed, reprocessing" in captured.out


def test_analyzer_skips_unchanged_files_on_resume(capsys):
    """Test that analyzer skips files that haven't changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "README.md"
        doc_path.write_text("# Introduction\nStatic content")

        # First analysis
        mock_llm = MagicMock()
        mock_llm.extract_doc_concept.return_value = {
            "description": "Description",
            "keywords": ["test"],
        }

        analyzer = SemanticAnalyzer(llm_client=mock_llm, root_dir=tmpdir)

        with patch("defrag.analyzer.extract_markdown_sections") as mock_extract:
            mock_extract.return_value = [("Introduction", "Static content", 1, 2)]
            analyzer.analyze_documentation(["README.md"], verbose=True)

        assert mock_llm.extract_doc_concept.call_count == 1

        # Save index
        index_path = Path(tmpdir) / "index.json"
        analyzer.index.save(str(index_path))

        # Resume WITHOUT modifying file
        mock_llm2 = MagicMock()

        analyzer2 = SemanticAnalyzer(
            llm_client=mock_llm2, root_dir=tmpdir, resume_from=str(index_path)
        )

        analyzer2.analyze_documentation(["README.md"], verbose=True)

        # Should NOT have called LLM (file unchanged)
        mock_llm2.extract_doc_concept.assert_not_called()

        # Check output
        captured = capsys.readouterr()
        assert "Skipping unchanged doc" in captured.out
