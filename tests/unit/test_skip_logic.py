"""Test skip logic for resume functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from defrag.analyzer import SemanticAnalyzer
from defrag.semantic import Concept, ConceptMatch, SemanticIndex


def test_skip_already_processed_docs(capsys):
    """Test that analyzer skips docs that already have concepts."""
    # Create index with existing doc concepts
    index = SemanticIndex()
    index.add_concept(
        Concept(
            id="doc:README.md:intro",
            source="README.md",
            source_type="doc",
            location="intro",
            description="Introduction section",
            keywords=["intro"],
        )
    )
    # Add file hash to simulate it was processed
    index.update_file_hash("README.md", "dummy_hash_123")

    # Save and reload to simulate resume
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        # Create analyzer with mock LLM (should not be called for skipped docs)
        mock_llm = MagicMock()
        analyzer = SemanticAnalyzer(llm_client=mock_llm, resume_from=tmp_path)

        # Try to analyze the same doc (should skip)
        with patch("defrag.analyzer.extract_markdown_sections") as mock_extract:
            with patch("defrag.analyzer.compute_file_hash") as mock_hash:
                mock_extract.return_value = [("intro", "Content", 1, 10)]
                mock_hash.return_value = "dummy_hash_123"  # Same hash = unchanged file

                analyzer.analyze_documentation(["README.md"], verbose=True)

                # Should NOT have called LLM since doc was already processed
                mock_llm.extract_doc_concept.assert_not_called()

                # Check output
                captured = capsys.readouterr()
                assert "Skipping unchanged doc: README.md" in captured.out
                assert "1 concepts" in captured.out
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_skip_already_processed_code():
    """Test that analyzer skips code files that already have concepts."""
    index = SemanticIndex()
    index.add_concept(
        Concept(
            id="code:app.py:main",
            source="app.py",
            source_type="code",
            location="main",
            description="Main function",
            keywords=["main"],
            line_range=(10, 20),
        )
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        mock_llm = MagicMock()
        analyzer = SemanticAnalyzer(llm_client=mock_llm, resume_from=tmp_path)

        # Try to analyze the same file (should skip)
        analyzer.analyze_python_file("app.py", verbose=True)

        # Should NOT have called LLM
        mock_llm.extract_code_concept.assert_not_called()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_skip_already_matched_concepts(capsys):
    """Test that matcher skips code concepts that already have matches."""
    index = SemanticIndex()

    # Add code and doc concepts
    code_concept = Concept(
        id="code:app.py:main",
        source="app.py",
        source_type="code",
        location="main",
        description="Main function",
        keywords=["main"],
    )
    doc_concept = Concept(
        id="doc:README.md:intro",
        source="README.md",
        source_type="doc",
        location="intro",
        description="Introduction",
        keywords=["intro"],
    )
    index.add_concept(code_concept)
    index.add_concept(doc_concept)

    # Add existing match
    index.add_match(
        ConceptMatch(
            code_concept_id="code:app.py:main",
            doc_concept_id="doc:README.md:intro",
            confidence=0.85,
            reasoning="Already matched",
        )
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        mock_llm = MagicMock()
        analyzer = SemanticAnalyzer(llm_client=mock_llm, resume_from=tmp_path)

        # Try to match concepts (should skip already-matched)
        analyzer.match_all_concepts(verbose=True)

        # Should NOT have called LLM for matching
        mock_llm.match_concepts.assert_not_called()

        # Check output
        captured = capsys.readouterr()
        assert "1 already matched" in captured.out
        assert "0 new" in captured.out
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_skip_already_validated_matches(capsys):
    """Test that validator skips matches that are already validated."""
    index = SemanticIndex()

    # Add concepts
    index.add_concept(
        Concept(
            id="code:app.py:main",
            source="app.py",
            source_type="code",
            location="main",
            description="Main function",
            keywords=["main"],
            line_range=(10, 20),
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

    # Add match that's already validated
    validated_match = ConceptMatch(
        code_concept_id="code:app.py:main",
        doc_concept_id="doc:README.md:intro",
        confidence=0.85,
        reasoning="Test match",
        validated=True,  # Already validated
        physical_link_valid=True,
    )
    index.add_match(validated_match)

    # Add match that's not validated
    unvalidated_match = ConceptMatch(
        code_concept_id="code:app.py:helper",
        doc_concept_id="doc:README.md:features",
        confidence=0.75,
        reasoning="New match",
        validated=False,  # Not yet validated
    )
    index.add_match(unvalidated_match)

    # Add the concepts for the unvalidated match
    index.add_concept(
        Concept(
            id="code:app.py:helper",
            source="app.py",
            source_type="code",
            location="helper",
            description="Helper function",
            keywords=["helper"],
            line_range=(30, 40),
        )
    )
    index.add_concept(
        Concept(
            id="doc:README.md:features",
            source="README.md",
            source_type="doc",
            location="features",
            description="Features section",
            keywords=["features"],
        )
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        analyzer = SemanticAnalyzer(llm_client=None, resume_from=tmp_path)

        # Run validation
        analyzer.validate_with_physical_links(verbose=True)

        # Check that only unvalidated match was processed
        validated_count = sum(1 for m in analyzer.index.matches if m.validated)
        assert validated_count == 2  # Both should now be validated

        # Check output
        captured = capsys.readouterr()
        assert "1 already validated" in captured.out
        assert "1 new" in captured.out
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_processes_new_docs_after_resume():
    """Test that analyzer processes new docs even after resuming."""
    index = SemanticIndex()
    index.add_concept(
        Concept(
            id="doc:OLD.md:section",
            source="OLD.md",
            source_type="doc",
            location="section",
            description="Old doc",
            keywords=["old"],
        )
    )
    # Add file hash for old doc
    index.update_file_hash("OLD.md", "old_hash_123")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        index.save(tmp_path)

        mock_llm = MagicMock()
        mock_llm.extract_doc_concept.return_value = {
            "description": "New doc section",
            "keywords": ["new"],
        }

        analyzer = SemanticAnalyzer(llm_client=mock_llm, resume_from=tmp_path)

        # Analyze both old and new docs
        with patch("defrag.analyzer.extract_markdown_sections") as mock_extract:
            with patch("defrag.analyzer.compute_file_hash") as mock_hash:
                def extract_side_effect(path, root):
                    if "NEW.md" in path:
                        return [("section", "New content", 1, 10)]
                    return [("section", "Old content", 1, 10)]

                def hash_side_effect(path, root):
                    if "NEW.md" in path:
                        return "new_hash_456"  # New file
                    return "old_hash_123"  # Same hash as before

                mock_extract.side_effect = extract_side_effect
                mock_hash.side_effect = hash_side_effect

                analyzer.analyze_documentation(["OLD.md", "NEW.md"], verbose=False)

                # Should only call LLM for NEW.md
                assert mock_llm.extract_doc_concept.call_count == 1

                # Should have both concepts
                assert len(analyzer.index.concepts) == 2
                assert "doc:OLD.md:section" in analyzer.index.concepts
                assert "doc:NEW.md:section" in analyzer.index.concepts
    finally:
        Path(tmp_path).unlink(missing_ok=True)
