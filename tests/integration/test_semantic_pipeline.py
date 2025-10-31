"""
Integration tests for semantic analysis pipeline.

Tests the full end-to-end workflow with real LLM API calls.
Requires ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

from defrag.analyzer import SemanticAnalyzer


@pytest.fixture
def fixture_codebase():
    """Create temporary directory with fixture codebase."""
    fixture_src = Path(__file__).parent.parent / "fixtures"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Copy fixtures
        shutil.copytree(fixture_src / "docs", tmpdir / "docs")
        shutil.copy(fixture_src / "sample_code.py", tmpdir / "sample_code.py")

        yield tmpdir


@pytest.mark.integration
class TestSemanticPipeline:
    """Integration tests using real LLM API."""

    def test_doc_to_code_matching(self, fixture_codebase):
        """
        Test that documentation sections correctly match to code implementations.

        Expected behavior:
        - USER_GUIDE.md "User Engagement Scoring" → calculate_user_score()
        - USER_GUIDE.md "Payment Processing" → process_payment()
        """
        analyzer = SemanticAnalyzer(root_dir=str(fixture_codebase))

        # Analyze docs
        doc_paths = ["docs/USER_GUIDE.md", "docs/LEGACY.md"]
        analyzer.analyze_documentation(doc_paths, verbose=False)

        # Analyze code
        code_paths = ["sample_code.py"]
        analyzer.analyze_code_files(code_paths, verbose=False)

        # Match concepts (disable auto-refinement for faster tests)
        analyzer.match_all_concepts(verbose=False, max_iterations=0)

        # Verify we found matches
        assert len(analyzer.index.matches) > 0, "Should find semantic matches"

        # Check for expected matches
        high_conf_matches = [m for m in analyzer.index.matches if m.confidence >= 0.7]
        assert (
            len(high_conf_matches) >= 2
        ), "Should find at least 2 high-confidence matches (scoring + payment)"

        # Verify matches are between USER_GUIDE and sample_code
        for match in high_conf_matches:
            doc_concept = analyzer.index.get_concept(match.doc_concept_id)
            code_concept = analyzer.index.get_concept(match.code_concept_id)

            assert (
                doc_concept.source == "docs/USER_GUIDE.md"
            ), f"Doc match should be from USER_GUIDE, got {doc_concept.source}"
            assert (
                code_concept.source == "sample_code.py"
            ), f"Code match should be from sample_code, got {code_concept.source}"

            # Should suggest physical links
            assert (
                match.suggested_link is not None
            ), "High confidence match should suggest physical link"
            assert "sample_code.py:" in match.suggested_link

    def test_orphaned_doc_detection(self, fixture_codebase):
        """
        Test that docs with no matching code are identified as GC candidates.

        Expected behavior:
        - LEGACY.md describes deprecated features with no implementation
        - Should have no semantic matches
        - Should be flagged for GC
        """
        analyzer = SemanticAnalyzer(root_dir=str(fixture_codebase))

        # Analyze all docs
        doc_paths = ["docs/USER_GUIDE.md", "docs/LEGACY.md"]
        analyzer.analyze_documentation(doc_paths, verbose=False)

        # Analyze code
        code_paths = ["sample_code.py"]
        analyzer.analyze_code_files(code_paths, verbose=False)

        # Match concepts (disable auto-refinement for faster tests)
        analyzer.match_all_concepts(verbose=False, max_iterations=0)

        # Generate report
        report = analyzer.generate_report()

        # LEGACY.md should have no matches (GC candidate)
        legacy_concepts = [
            c for c in analyzer.index.get_doc_concepts() if c.source == "docs/LEGACY.md"
        ]

        legacy_matches = [
            m for m in analyzer.index.matches if m.doc_concept_id in [c.id for c in legacy_concepts]
        ]

        # Legacy doc should either have no matches or only low-confidence ones
        high_conf_legacy = [m for m in legacy_matches if m.confidence >= 0.7]
        assert (
            len(high_conf_legacy) == 0
        ), "LEGACY.md should not have high-confidence matches (orphaned doc)"

        # Verify GC candidates are reported
        assert report["unmatched_docs"] > 0, "Should identify orphaned docs as GC candidates"

    def test_undocumented_code_detection(self, fixture_codebase):
        """
        Test that code without documentation is identified.

        Expected behavior:
        - CacheManager class has no documentation
        - Should be detected as undocumented code
        - Could trigger auto-doc generation
        """
        analyzer = SemanticAnalyzer(root_dir=str(fixture_codebase))

        # Analyze docs
        doc_paths = ["docs/USER_GUIDE.md", "docs/LEGACY.md"]
        analyzer.analyze_documentation(doc_paths, verbose=False)

        # Analyze code
        code_paths = ["sample_code.py"]
        analyzer.analyze_code_files(code_paths, verbose=False)

        # Match concepts (disable auto-refinement for faster tests)
        analyzer.match_all_concepts(verbose=False, max_iterations=0)

        # Find code concepts with no documentation
        undocumented = analyzer.find_undocumented_code()

        assert len(undocumented) > 0, "Should find undocumented code (CacheManager)"

        # Verify CacheManager is in undocumented list
        cache_manager_concepts = [
            c
            for c in undocumented
            if "CacheManager" in c.location or "cache" in c.description.lower()
        ]

        assert len(cache_manager_concepts) > 0, "CacheManager should be detected as undocumented"

    def test_iterative_refinement(self, fixture_codebase):
        """
        Test that iterative refinement improves low-confidence matches.

        Expected behavior:
        - Initial matches may be low confidence
        - Refinement expands context
        - Confidence improves or stays similar
        - Iterations tracked in match data
        """
        analyzer = SemanticAnalyzer(root_dir=str(fixture_codebase))

        # Analyze
        doc_paths = ["docs/USER_GUIDE.md"]
        analyzer.analyze_documentation(doc_paths, verbose=False)

        code_paths = ["sample_code.py"]
        analyzer.analyze_code_files(code_paths, verbose=False)

        # Enable auto-refinement for this test (max 1 refinement iteration)
        analyzer.match_all_concepts(verbose=False, max_iterations=1)

        # Check that refinement happened automatically during matching
        # All matches should have iteration tracking
        for match in analyzer.index.matches:
            assert match.iterations >= 1, "Match should track iterations"

            # If a match is still low confidence, it should either:
            # 1. Have no context_needed (LLM decided it can't be improved)
            # 2. Have exhausted max_iterations
            if match.confidence < 0.7:
                # Either no context was needed, or refinement was attempted
                assert (
                    match.context_needed is None or match.iterations > 1
                ), "Low confidence match should have no context_needed or multiple iterations"

        # Note: We don't strictly require refined matches (iterations > 1) since the LLM
        # might be confident on first try, but if there are any, they should show iteration tracking

    def test_physical_link_validation(self, fixture_codebase):
        """
        Test that physical links are validated as grounding heuristic.

        Expected behavior:
        - Semantic matches suggest links
        - Physical validator checks if links exist in doc
        - Confidence adjusted based on validation
        """
        analyzer = SemanticAnalyzer(root_dir=str(fixture_codebase))

        # Manually add a physical link to USER_GUIDE.md
        user_guide = fixture_codebase / "docs" / "USER_GUIDE.md"
        content = user_guide.read_text()

        # Add reference to payment function (lines 44-73)
        modified = content.replace(
            "Invalid amounts", "See `sample_code.py:44-73` for implementation.\n\nInvalid amounts"
        )
        user_guide.write_text(modified)

        # Run analysis
        doc_paths = ["docs/USER_GUIDE.md"]
        analyzer.analyze_documentation(doc_paths, verbose=False)

        code_paths = ["sample_code.py"]
        analyzer.analyze_code_files(code_paths, verbose=False)

        analyzer.match_all_concepts(verbose=False)
        analyzer.validate_with_physical_links(verbose=False)

        # Check that physical link was detected
        validated_matches = [m for m in analyzer.index.matches if m.physical_link_valid is True]

        assert len(validated_matches) > 0, "Should detect existing physical link in documentation"
