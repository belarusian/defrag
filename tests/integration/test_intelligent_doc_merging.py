"""
Integration tests for intelligent document merging with LLM.

Tests the LLM-powered document rewriting that naturally weaves
code references into documentation.
"""

import os
import tempfile
from pathlib import Path
import pytest

from defrag.fixer import fix_document_references
from defrag.llm import LLMClient
from defrag.semantic import Concept, ConceptMatch, SemanticIndex


def get_test_llm_client():
    """Get LLM client for testing, skip if no API key available."""
    provider = os.getenv("DEFRAG_LLM_PROVIDER", "anthropic")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set, skipping integration test")
    elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skipping integration test")

    return LLMClient()


@pytest.mark.integration
class TestIntelligentDocMerging:
    """Test the LLM-powered intelligent document merging."""

    @pytest.fixture
    def sample_doc_and_index(self):
        """Create a sample document and semantic index with matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a sample documentation file
            doc_path = "docs/architecture.md"
            full_doc_path = Path(tmpdir) / doc_path
            full_doc_path.parent.mkdir(parents=True)

            doc_content = """# System Architecture

## Overview

Our system processes data through a multi-stage pipeline that ensures
reliability and performance. The architecture is designed to be modular
and scalable.

## Data Processing

The data processing component handles incoming requests and transforms
them according to business rules. It includes validation, transformation,
and persistence layers.

## Caching Strategy

We use an in-memory cache to improve response times for frequently
accessed data. The cache is automatically invalidated when underlying
data changes.

## Error Handling

The system implements comprehensive error handling with retry logic
and circuit breakers to ensure resilience.
"""
            full_doc_path.write_text(doc_content)

            # Create semantic index with matches
            index = SemanticIndex()

            # Add documentation concepts
            doc_concepts = [
                ("Overview", "System architecture overview"),
                ("Data Processing", "Data processing pipeline description"),
                ("Caching Strategy", "Caching implementation approach"),
                ("Error Handling", "Error handling and resilience"),
            ]

            for location, description in doc_concepts:
                concept = Concept(
                    id=f"doc:{doc_path}:{location}",
                    source=doc_path,
                    source_type="doc",
                    location=location,
                    description=description,
                    keywords=location.lower().split(),
                )
                index.add_concept(concept)

            # Add code concepts
            code_concepts = [
                ("pipeline.py", "process_data", "Processes data through validation and transformation stages", (45, 120)),
                ("cache.py", "CacheManager", "Manages in-memory cache with TTL and invalidation", (15, 95)),
                ("errors.py", "retry_with_backoff", "Implements exponential backoff retry logic", (200, 245)),
                ("errors.py", "CircuitBreaker", "Circuit breaker pattern implementation", (300, 380)),
            ]

            for source, location, description, line_range in code_concepts:
                concept = Concept(
                    id=f"code:{source}:{location}",
                    source=source,
                    source_type="code",
                    location=location,
                    description=description,
                    keywords=location.lower().split("_"),
                    line_range=line_range,
                )
                index.add_concept(concept)

            # Add matches between code and docs
            matches = [
                ("doc:docs/architecture.md:Data Processing", "code:pipeline.py:process_data", 0.85,
                 "The process_data function implements the data processing pipeline"),
                ("doc:docs/architecture.md:Caching Strategy", "code:cache.py:CacheManager", 0.90,
                 "CacheManager implements the caching strategy described"),
                ("doc:docs/architecture.md:Error Handling", "code:errors.py:retry_with_backoff", 0.80,
                 "retry_with_backoff provides the retry logic mentioned"),
                ("doc:docs/architecture.md:Error Handling", "code:errors.py:CircuitBreaker", 0.85,
                 "CircuitBreaker implements the circuit breaker pattern"),
            ]

            for doc_id, code_id, confidence, reasoning in matches:
                match = ConceptMatch(
                    code_concept_id=code_id,
                    doc_concept_id=doc_id,
                    confidence=confidence,
                    reasoning=reasoning,
                    suggested_link=f"{code_id.split(':')[1]}:{code_concepts[[c[1] for c in code_concepts].index(code_id.split(':')[2])][3][0]}-{code_concepts[[c[1] for c in code_concepts].index(code_id.split(':')[2])][3][1]}",
                    physical_link_valid=False,  # No existing references
                )
                index.add_match(match)

            yield tmpdir, doc_path, index, doc_content

    def test_llm_rewrites_document_naturally(self, sample_doc_and_index):
        """Test that LLM naturally integrates references into the document."""
        tmpdir, doc_path, index, original_content = sample_doc_and_index

        # Get LLM client
        llm = get_test_llm_client()

        # Fix document references using LLM rewriting
        changes = fix_document_references(
            doc_path,
            index,
            llm,
            root_dir=tmpdir,
            dry_run=False,
            verbose=True,
        )

        # Verify changes were made
        assert len(changes) > 0, "Should have made changes to the document"
        assert "Rewrote document" in changes[0], "Should use LLM rewrite, not mechanical insertion"

        # Read the updated document
        updated_path = Path(tmpdir) / doc_path
        updated_content = updated_path.read_text()

        # Verify the content changed
        assert updated_content != original_content, "Document should be modified"

        # Verify references are integrated naturally
        # Should NOT have mechanical "See `file:line`" on separate lines
        mechanical_pattern = r"^\s*See `.*:\d+(-\d+)?`\s*-"
        import re
        mechanical_matches = re.findall(mechanical_pattern, updated_content, re.MULTILINE)
        assert len(mechanical_matches) == 0, "Should not have mechanical reference insertions"

        # Verify the references ARE present in some form
        assert "pipeline.py" in updated_content, "Should reference pipeline.py"
        assert "cache.py" in updated_content or "CacheManager" in updated_content, "Should reference cache implementation"
        assert "errors.py" in updated_content or "retry" in updated_content.lower(), "Should reference error handling"

        # Verify structure is maintained
        assert "# System Architecture" in updated_content, "Should maintain main heading"
        assert "## Overview" in updated_content, "Should maintain section headings"
        assert "## Data Processing" in updated_content
        assert "## Caching Strategy" in updated_content
        assert "## Error Handling" in updated_content

    def test_fallback_to_mechanical_on_llm_failure(self, sample_doc_and_index):
        """Test that mechanical insertion is used as fallback when LLM fails."""
        tmpdir, doc_path, index, original_content = sample_doc_and_index

        # Create a mock LLM that fails
        class FailingLLM:
            def generate_text(self, prompt, max_tokens=None):
                raise Exception("LLM service unavailable")

            def _request_json(self, *args, **kwargs):
                raise Exception("LLM service unavailable")

        failing_llm = FailingLLM()

        # Fix document references - should fall back to mechanical
        changes = fix_document_references(
            doc_path,
            index,
            failing_llm,
            root_dir=tmpdir,
            dry_run=False,
            verbose=True,
        )

        # Should still make changes via mechanical fallback
        assert len(changes) > 0, "Should fall back to mechanical insertion"

        # Read the updated document
        updated_path = Path(tmpdir) / doc_path
        updated_content = updated_path.read_text()

        # Should have mechanical insertions
        assert "See `pipeline.py:45-120`" in updated_content, "Should have mechanical references"

    def test_preserves_document_when_no_matches(self, sample_doc_and_index):
        """Test that documents are unchanged when there are no matches to add."""
        tmpdir, doc_path, index, original_content = sample_doc_and_index

        # Create a new doc with no matches
        unmatched_doc = "docs/unrelated.md"
        unmatched_path = Path(tmpdir) / unmatched_doc
        unmatched_content = """# Unrelated Document

This document has no semantic matches in the index.
"""
        unmatched_path.write_text(unmatched_content)

        llm = get_test_llm_client()

        # Try to fix references (should find nothing to fix)
        changes = fix_document_references(
            unmatched_doc,
            index,
            llm,
            root_dir=tmpdir,
            dry_run=False,
            verbose=True,
        )

        # Should make no changes
        assert len(changes) == 0, "Should make no changes when no matches"

        # Content should be unchanged
        final_content = unmatched_path.read_text()
        assert final_content == unmatched_content, "Content should remain unchanged"

    def test_dry_run_does_not_modify(self, sample_doc_and_index):
        """Test that dry run mode doesn't actually modify files."""
        tmpdir, doc_path, index, original_content = sample_doc_and_index

        llm = get_test_llm_client()

        # Fix in dry run mode
        changes = fix_document_references(
            doc_path,
            index,
            llm,
            root_dir=tmpdir,
            dry_run=True,
            verbose=True,
        )

        # Should report changes
        assert len(changes) > 0, "Should report intended changes"

        # But file should be unchanged
        actual_content = (Path(tmpdir) / doc_path).read_text()
        assert actual_content == original_content, "Dry run should not modify file"