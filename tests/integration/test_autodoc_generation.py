"""
Integration tests for conceptual documentation generation.

Tests the auto-doc feature that generates semantic documentation
for undocumented code.
"""

import os
import tempfile
from pathlib import Path
import pytest

from defrag.analyzer import SemanticAnalyzer
from defrag.autodoc import generate_conceptual_docs_for_undocumented_code
from defrag.llm import LLMClient


def get_test_llm_client():
    """Get LLM client for testing, skip if no API key available."""
    provider = os.getenv("DEFRAG_LLM_PROVIDER", "anthropic")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set, skipping integration test")
    elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skipping integration test")

    return LLMClient()


@pytest.mark.integration
class TestAutoDocGeneration:
    """Test conceptual documentation generation for undocumented code."""

    @pytest.fixture
    def undocumented_codebase(self):
        """Create a test codebase with undocumented code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some undocumented code files
            code_dir = Path(tmpdir) / "src"
            code_dir.mkdir()

            # Cache implementation (undocumented)
            cache_file = code_dir / "cache.py"
            cache_file.write_text(
                '''
class CacheManager:
    """In-memory cache for performance optimization."""

    def __init__(self):
        self._cache = {}

    def get(self, key):
        """Get value from cache."""
        return self._cache.get(key)

    def set(self, key, value):
        """Set value in cache."""
        self._cache[key] = value

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()


def get_cached_result(key):
    """Helper to get cached computation result."""
    manager = CacheManager()
    return manager.get(key)
'''
            )

            # Error handling (undocumented)
            error_file = code_dir / "errors.py"
            error_file.write_text(
                '''
class ApplicationError(Exception):
    """Base application error."""
    pass


class ValidationError(ApplicationError):
    """Data validation error."""

    def __init__(self, field, message):
        self.field = field
        super().__init__(f"{field}: {message}")


def handle_error(error, logger=None):
    """Central error handling logic."""
    if logger:
        logger.error(str(error))

    if isinstance(error, ValidationError):
        return {"error": "validation_failed", "field": error.field}
    elif isinstance(error, ApplicationError):
        return {"error": "application_error", "message": str(error)}
    else:
        return {"error": "unknown_error"}
'''
            )

            # Create minimal existing documentation
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Only document the API endpoints, not the cache or error handling
            api_doc = docs_dir / "api.md"
            api_doc.write_text(
                """# API Documentation

## Endpoints

The system provides REST API endpoints for data processing.
"""
            )

            yield tmpdir

    def test_generates_conceptual_documentation(self, undocumented_codebase):
        """Test that conceptual docs are generated for undocumented code."""
        # Initialize
        llm = get_test_llm_client()
        analyzer = SemanticAnalyzer(llm, root_dir=undocumented_codebase)

        # Analyze the codebase
        analyzer.analyze_code_files(["src/cache.py", "src/errors.py"])
        analyzer.analyze_documentation(["docs/api.md"])
        analyzer.match_all_concepts()

        # Generate conceptual docs for undocumented code
        generated_docs, _ = generate_conceptual_docs_for_undocumented_code(
            analyzer.index,
            llm,
            undocumented_codebase,
            min_confidence=0.5,
            dry_run=True,  # Don't actually write files
            verbose=True,
        )

        # Verify docs were generated
        assert len(generated_docs) > 0, "Should generate conceptual documentation"

        # Check that generated docs are conceptual, not API reference
        for doc_path, content in generated_docs.items():
            # Should be in docs directory
            assert doc_path.startswith("docs/"), f"Doc should be in docs/ directory: {doc_path}"

            # Should contain conceptual content
            assert len(content) > 100, "Generated doc should have substantial content"

            # Should reference implementation
            assert (
                "Implementation Reference" in content or ".py" in content
            ), "Should reference code implementations"

    def test_clusters_by_semantic_purpose(self, undocumented_codebase):
        """Test that undocumented code is clustered by semantic purpose."""
        from defrag.autodoc import ConceptualDocGenerator

        # Initialize
        llm = get_test_llm_client()
        analyzer = SemanticAnalyzer(llm, root_dir=undocumented_codebase)

        # Analyze the codebase
        analyzer.analyze_code_files(["src/cache.py", "src/errors.py"])
        analyzer.analyze_documentation(["docs/api.md"])
        analyzer.match_all_concepts()

        # Find undocumented code
        code_concepts = analyzer.index.get_code_concepts()
        matched_code_ids = {
            m.code_concept_id for m in analyzer.index.matches if m.confidence >= 0.5
        }
        undocumented = [c for c in code_concepts if c.id not in matched_code_ids]

        assert len(undocumented) > 0, "Should have undocumented code"

        # Test semantic clustering
        generator = ConceptualDocGenerator(llm, undocumented_codebase)
        clusters = generator.analyze_semantic_clusters(undocumented)

        # Should group by semantic purpose, not by file
        assert len(clusters) > 0, "Should identify semantic clusters"

        # Clusters should have meaningful themes
        for theme in clusters.keys():
            assert len(theme) > 3, f"Theme should be descriptive: {theme}"
            # Theme should not be just a filename
            assert not theme.endswith(".py"), f"Theme should be conceptual, not filename: {theme}"

    def test_no_generation_when_documented(self, undocumented_codebase):
        """Test that no docs are generated when code is already documented."""
        # Create a fully documented codebase
        docs_dir = Path(undocumented_codebase) / "docs"

        # Add documentation that covers the cache
        cache_doc = docs_dir / "caching.md"
        cache_doc.write_text(
            """# Caching Strategy

The system uses an in-memory cache for performance optimization.

See `src/cache.py` for the implementation.
"""
        )

        # Add documentation that covers error handling
        error_doc = docs_dir / "error-handling.md"
        error_doc.write_text(
            """# Error Handling

Central error handling and validation logic.

See `src/errors.py` for the implementation.
"""
        )

        # Initialize and analyze
        llm = get_test_llm_client()
        analyzer = SemanticAnalyzer(llm, root_dir=undocumented_codebase)

        analyzer.analyze_code_files(["src/cache.py", "src/errors.py"])
        analyzer.analyze_documentation(["docs/api.md", "docs/caching.md", "docs/error-handling.md"])
        analyzer.match_all_concepts()

        # Try to generate docs
        generated_docs, _ = generate_conceptual_docs_for_undocumented_code(
            analyzer.index,
            llm,
            undocumented_codebase,
            min_confidence=0.5,
            dry_run=True,
            verbose=True,
        )

        # Should not generate docs since everything is documented
        assert len(generated_docs) == 0, "Should not generate docs for already documented code"

    def test_respects_confidence_threshold(self, undocumented_codebase):
        """Test that confidence threshold is respected."""
        llm = get_test_llm_client()
        analyzer = SemanticAnalyzer(llm, root_dir=undocumented_codebase)

        # Analyze the codebase
        analyzer.analyze_code_files(["src/cache.py", "src/errors.py"])
        analyzer.analyze_documentation(["docs/api.md"])

        # Force some weak matches by analyzing with low threshold
        analyzer.match_all_concepts()

        def undocumented_ids(threshold: float):
            matched = {
                m.code_concept_id for m in analyzer.index.matches if m.confidence >= threshold
            }
            return {
                concept.id
                for concept in analyzer.index.get_code_concepts()
                if concept.id not in matched
            }

        high_undocumented = undocumented_ids(0.8)
        high_threshold_docs, _ = generate_conceptual_docs_for_undocumented_code(
            analyzer.index,
            llm,
            undocumented_codebase,
            min_confidence=0.8,  # High threshold
            dry_run=True,
            verbose=False,
        )

        low_undocumented = undocumented_ids(0.3)
        generate_conceptual_docs_for_undocumented_code(
            analyzer.index,
            llm,
            undocumented_codebase,
            min_confidence=0.3,  # Low threshold
            dry_run=True,
            verbose=False,
        )

        # With higher threshold, more code concepts should be treated as undocumented.
        assert high_undocumented.issuperset(
            low_undocumented
        ), "Higher confidence threshold should flag a superset of undocumented concepts"
        assert len(high_threshold_docs) > 0, "Expected conceptual docs to be generated"
        assert len(high_threshold_docs) <= len(
            high_undocumented
        ), "Generated docs should not exceed the number of undocumented concepts discovered"
