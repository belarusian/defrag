"""
Unit tests for semantic data models.

Tests the core data structures without LLM API calls.
"""

import pytest
from defrag.semantic import Concept, ConceptMatch, SemanticIndex


@pytest.mark.unit
class TestConcept:
    """Test Concept data model."""

    def test_concept_creation(self):
        """Test creating a Concept."""
        concept = Concept(
            id="doc:test.md:section1",
            source="test.md",
            source_type="doc",
            location="Section 1",
            description="Test section describing feature X",
            keywords=["test", "feature", "x"],
            line_range=(1, 10),
            raw_content="# Section 1\nContent here",
        )

        assert concept.id == "doc:test.md:section1"
        assert concept.source_type == "doc"
        assert len(concept.keywords) == 3

    def test_concept_serialization(self):
        """Test Concept to/from dict."""
        concept = Concept(
            id="code:main.py:function_foo",
            source="main.py",
            source_type="code",
            location="function_foo",
            description="Processes user data",
            keywords=["user", "process"],
            line_range=(15, 30),
        )

        # Serialize
        data = concept.to_dict()
        assert data["id"] == "code:main.py:function_foo"
        assert data["line_range"] == [15, 30]

        # Deserialize
        restored = Concept.from_dict(data)
        assert restored.id == concept.id
        assert restored.line_range == concept.line_range


@pytest.mark.unit
class TestConceptMatch:
    """Test ConceptMatch data model."""

    def test_match_creation(self):
        """Test creating a ConceptMatch."""
        match = ConceptMatch(
            code_concept_id="code:main.py:foo",
            doc_concept_id="doc:guide.md:usage",
            confidence=0.85,
            reasoning="Both describe user data processing",
            suggested_link="main.py:15-30",
            context_needed=None,
            iterations=1,
        )

        assert match.confidence == 0.85
        assert match.iterations == 1
        assert match.suggested_link == "main.py:15-30"

    def test_match_with_context_needed(self):
        """Test match with context_needed for refinement."""
        match = ConceptMatch(
            code_concept_id="code:main.py:bar",
            doc_concept_id="doc:guide.md:advanced",
            confidence=0.6,
            reasoning="Partial match, need more context",
            context_needed={
                "file_patterns": ["**/utils/*.py"],
                "keywords": ["helper", "utility"],
                "reason": "Need to see helper functions",
            },
            iterations=1,
        )

        assert match.confidence < 0.7
        assert match.context_needed is not None
        assert "file_patterns" in match.context_needed

    def test_match_serialization(self):
        """Test ConceptMatch to/from dict."""
        match = ConceptMatch(
            code_concept_id="code:a",
            doc_concept_id="doc:b",
            confidence=0.9,
            reasoning="Test",
            physical_link_valid=True,
            suggested_link="a.py:10",
            context_needed={"test": "data"},
            iterations=2,
        )

        data = match.to_dict()
        assert data["confidence"] == 0.9
        assert data["iterations"] == 2
        assert data["context_needed"] == {"test": "data"}

        restored = ConceptMatch.from_dict(data)
        assert restored.confidence == match.confidence
        assert restored.iterations == match.iterations
        assert restored.context_needed == match.context_needed


@pytest.mark.unit
class TestSemanticIndex:
    """Test SemanticIndex data structure."""

    def test_index_creation(self):
        """Test creating an empty index."""
        index = SemanticIndex()
        assert len(index.concepts) == 0
        assert len(index.matches) == 0

    def test_add_concept(self):
        """Test adding concepts to index."""
        index = SemanticIndex()

        concept1 = Concept(
            id="doc:test.md:s1",
            source="test.md",
            source_type="doc",
            location="s1",
            description="Test",
            keywords=[],
        )

        concept2 = Concept(
            id="code:main.py:func",
            source="main.py",
            source_type="code",
            location="func",
            description="Function",
            keywords=[],
        )

        index.add_concept(concept1)
        index.add_concept(concept2)

        assert len(index.concepts) == 2
        assert index.get_concept("doc:test.md:s1") == concept1
        assert index.get_concept("code:main.py:func") == concept2

    def test_add_match(self):
        """Test adding matches to index."""
        index = SemanticIndex()

        match = ConceptMatch(
            code_concept_id="code:a", doc_concept_id="doc:b", confidence=0.8, reasoning="Test"
        )

        index.add_match(match)
        assert len(index.matches) == 1

    def test_get_doc_concepts(self):
        """Test filtering doc concepts."""
        index = SemanticIndex()

        doc_concept = Concept(
            id="doc:test.md:s1",
            source="test.md",
            source_type="doc",
            location="s1",
            description="Doc",
            keywords=[],
        )

        code_concept = Concept(
            id="code:main.py:func",
            source="main.py",
            source_type="code",
            location="func",
            description="Code",
            keywords=[],
        )

        index.add_concept(doc_concept)
        index.add_concept(code_concept)

        doc_concepts = index.get_doc_concepts()
        assert len(doc_concepts) == 1
        assert doc_concepts[0].source_type == "doc"

    def test_get_code_concepts(self):
        """Test filtering code concepts."""
        index = SemanticIndex()

        doc_concept = Concept(
            id="doc:test.md:s1",
            source="test.md",
            source_type="doc",
            location="s1",
            description="Doc",
            keywords=[],
        )

        code_concept = Concept(
            id="code:main.py:func",
            source="main.py",
            source_type="code",
            location="func",
            description="Code",
            keywords=[],
        )

        index.add_concept(doc_concept)
        index.add_concept(code_concept)

        code_concepts = index.get_code_concepts()
        assert len(code_concepts) == 1
        assert code_concepts[0].source_type == "code"
