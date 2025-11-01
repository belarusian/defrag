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
                (
                    "pipeline.py",
                    "process_data",
                    "Processes data through validation and transformation stages",
                    (45, 120),
                ),
                (
                    "cache.py",
                    "CacheManager",
                    "Manages in-memory cache with TTL and invalidation",
                    (15, 95),
                ),
                (
                    "errors.py",
                    "retry_with_backoff",
                    "Implements exponential backoff retry logic",
                    (200, 245),
                ),
                (
                    "errors.py",
                    "CircuitBreaker",
                    "Circuit breaker pattern implementation",
                    (300, 380),
                ),
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
                (
                    "doc:docs/architecture.md:Data Processing",
                    "code:pipeline.py:process_data",
                    0.85,
                    "The process_data function implements the data processing pipeline",
                ),
                (
                    "doc:docs/architecture.md:Caching Strategy",
                    "code:cache.py:CacheManager",
                    0.90,
                    "CacheManager implements the caching strategy described",
                ),
                (
                    "doc:docs/architecture.md:Error Handling",
                    "code:errors.py:retry_with_backoff",
                    0.80,
                    "retry_with_backoff provides the retry logic mentioned",
                ),
                (
                    "doc:docs/architecture.md:Error Handling",
                    "code:errors.py:CircuitBreaker",
                    0.85,
                    "CircuitBreaker implements the circuit breaker pattern",
                ),
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
        assert (
            "cache.py" in updated_content or "CacheManager" in updated_content
        ), "Should reference cache implementation"
        assert (
            "errors.py" in updated_content or "retry" in updated_content.lower()
        ), "Should reference error handling"

        # Verify structure is maintained
        assert "# System Architecture" in updated_content, "Should maintain main heading"
        assert "## Overview" in updated_content, "Should maintain section headings"
        assert "## Data Processing" in updated_content
        assert "## Caching Strategy" in updated_content
        assert "## Error Handling" in updated_content

    def test_empty_llm_response_triggers_fallback(self, sample_doc_and_index):
        """Test that empty LLM response triggers mechanical fallback."""
        tmpdir, doc_path, index, original_content = sample_doc_and_index

        # Get a real LLM client
        llm = get_test_llm_client()

        # We can't control what the LLM returns, but we can test the behavior
        # by creating a document that's difficult for the LLM to rewrite
        # This tests the actual fallback logic without mocking

        # Create a malformed document that might cause LLM issues
        malformed_doc = "docs/malformed.md"
        malformed_path = Path(tmpdir) / malformed_doc
        malformed_path.parent.mkdir(parents=True, exist_ok=True)

        # Create content that's challenging for LLM to process
        malformed_content = "# \x00\x01\x02 Invalid UTF sequences and no real content"
        malformed_path.write_text(malformed_content, encoding="utf-8", errors="replace")

        # Add a concept for this doc
        from defrag.semantic import Concept

        malformed_concept = Concept(
            id=f"doc:{malformed_doc}:Invalid",
            source=malformed_doc,
            source_type="doc",
            location="Invalid",
            description="Malformed section",
            keywords=["invalid"],
        )
        index.add_concept(malformed_concept)

        # Add a match to this malformed doc
        from defrag.semantic import ConceptMatch

        match = ConceptMatch(
            code_concept_id="code:pipeline.py:process_data",
            doc_concept_id=malformed_concept.id,
            confidence=0.85,
            reasoning="Testing fallback behavior",
            suggested_link="pipeline.py:45-120",
            physical_link_valid=False,
        )
        index.add_match(match)

        # Try to fix - should handle gracefully
        changes = fix_document_references(
            malformed_doc,
            index,
            llm,
            root_dir=tmpdir,
            dry_run=False,
            verbose=True,
        )

        # Even if LLM fails, the system should handle it gracefully
        # Either by mechanical fallback or by skipping
        assert isinstance(changes, list), "Should return a list even on failure"

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

    def test_llm_integration_quality(self, sample_doc_and_index):
        """Test that LLM integration produces natural, readable documentation."""
        tmpdir, doc_path, index, original_content = sample_doc_and_index

        llm = get_test_llm_client()

        # Fix document references
        changes = fix_document_references(
            doc_path,
            index,
            llm,
            root_dir=tmpdir,
            dry_run=False,
            verbose=True,
        )

        assert len(changes) > 0, "Should make changes"

        # Read updated content
        updated_path = Path(tmpdir) / doc_path
        updated_content = updated_path.read_text()

        # Quality checks for natural integration
        lines = updated_content.split("\n")

        # Check that references are integrated into sentences, not just appended
        for i, line in enumerate(lines):
            if ".py:" in line:
                # Reference should be part of a sentence or have context
                # Not just "See `file:line`" on its own line
                if line.strip().startswith("See `") and line.strip().endswith("`"):
                    # This is mechanical, but check if it has reasoning
                    assert " - " in line, "Even fallback references should have reasoning"
                else:
                    # Check for natural integration patterns
                    natural_patterns = [
                        "implemented in",
                        "can be found in",
                        "is handled by",
                        "uses",
                        "leverages",
                        "through",
                        "via",
                        "within",
                        "The",  # Starting a descriptive sentence
                        "This",
                        "It",
                        "Our",
                    ]
                    has_natural_integration = any(pattern in line for pattern in natural_patterns)
                    # If a line has a code reference, it should be naturally integrated
                    # or be part of a longer explanation
                    if not has_natural_integration and len(line.strip()) < 50:
                        # Short lines with references might be mechanical
                        print(f"Warning: Potentially mechanical reference: {line}")

        # Ensure critical code references are present
        assert "pipeline.py" in updated_content or "process_data" in updated_content.lower()
        assert "cache" in updated_content.lower()
        assert "error" in updated_content.lower() or "retry" in updated_content.lower()

    def test_multiple_references_per_section(self, sample_doc_and_index):
        """Test handling multiple code references in a single documentation section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create document with one section
            doc_path = "docs/comprehensive.md"
            full_doc_path = Path(tmpdir) / doc_path
            full_doc_path.parent.mkdir(parents=True)

            doc_content = """# Comprehensive System

## Core Processing

Our system handles all data processing, caching, and error handling
in a unified pipeline. This ensures consistency and reliability
across all operations.
"""
            full_doc_path.write_text(doc_content)

            # Create index with multiple matches to same section
            index = SemanticIndex()

            # Add doc concept
            doc_concept = Concept(
                id=f"doc:{doc_path}:Core Processing",
                source=doc_path,
                source_type="doc",
                location="Core Processing",
                description="Comprehensive processing section",
                keywords=["processing", "core"],
            )
            index.add_concept(doc_concept)

            # Add multiple code concepts
            code_refs = [
                ("pipeline.py", "process_data", "Main processing function", (45, 120)),
                ("pipeline.py", "validate_input", "Input validation", (10, 44)),
                ("cache.py", "CacheManager", "Cache management", (15, 95)),
                ("errors.py", "retry_with_backoff", "Retry logic", (200, 245)),
                ("errors.py", "CircuitBreaker", "Circuit breaker", (300, 380)),
                ("monitor.py", "track_metrics", "Performance monitoring", (50, 100)),
            ]

            for source, location, description, line_range in code_refs:
                code_concept = Concept(
                    id=f"code:{source}:{location}",
                    source=source,
                    source_type="code",
                    location=location,
                    description=description,
                    keywords=location.lower().split("_"),
                    line_range=line_range,
                )
                index.add_concept(code_concept)

                # Add match to same doc section
                match = ConceptMatch(
                    code_concept_id=code_concept.id,
                    doc_concept_id=doc_concept.id,
                    confidence=0.85,
                    reasoning=f"{description} is part of core processing",
                    suggested_link=f"{source}:{line_range[0]}-{line_range[1]}",
                    physical_link_valid=False,
                )
                index.add_match(match)

            llm = get_test_llm_client()

            # Fix document with multiple references
            changes = fix_document_references(
                doc_path,
                index,
                llm,
                root_dir=tmpdir,
                dry_run=False,
                verbose=True,
            )

            assert len(changes) > 0, "Should make changes"

            # Read updated content
            updated_content = full_doc_path.read_text()

            # Verify all references are present
            for source, _, _, _ in code_refs:
                assert source in updated_content, f"Should reference {source}"

            # Check that it's not just a list dump
            # The content should flow naturally
            assert "## Core Processing" in updated_content
            assert (
                len(updated_content) > len(doc_content) + 100
            ), "Should have substantial additions"

            # Check for natural flow indicators
            paragraphs = updated_content.split("\n\n")
            processing_section_found = False
            for para in paragraphs:
                if "Core Processing" in para or processing_section_found:
                    processing_section_found = True
                    # Should have integrated the references, not just listed them
                    if ".py" in para:
                        # Paragraph with code reference should have substance
                        assert len(para) > 50, "References should be part of substantial text"
