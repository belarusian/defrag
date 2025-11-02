"""Tests for crash/resume scenarios using stubbed LLM clients (unit level)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from defrag.analyzer import SemanticAnalyzer
from defrag.semantic import Concept, ConceptMatch, SemanticIndex


def _make_doc_concept(doc_id):
    return Concept(
        id=f"doc:{doc_id}",
        source=doc_id.split(":")[0],
        source_type="doc",
        location="section",
        description="Doc section",
        keywords=["doc"],
    )


def _make_code_concept(code_id):
    return Concept(
        id=f"code:{code_id}",
        source=code_id.split(":")[0],
        source_type="code",
        location="func",
        description="Function",
        keywords=["code"],
    )


def _make_match(code_id, doc_id, confidence=0.8, validated=False):
    return ConceptMatch(
        code_concept_id=f"code:{code_id}",
        doc_concept_id=f"doc:{doc_id}",
        confidence=confidence,
        reasoning="test reasoning",
        physical_link_valid=True if validated else None,
        validated=validated,
    )


def test_resume_after_multiple_crashes(tmp_path):
    """Unit-level simulation of crash/resume cycles for SemanticAnalyzer."""
    index_path = tmp_path / "index.json"

    # Initial state with one doc concept and match
    index = SemanticIndex()
    index.add_concept(_make_doc_concept("docs/doc1.md:section"))
    index.add_match(_make_match("src/code1.py:func", "docs/doc1.md:section", validated=True))
    index.save(index_path)

    # First resume should load existing concepts without needing a real LLM
    analyzer = SemanticAnalyzer(llm_client=MagicMock(), root_dir=str(tmp_path), resume_from=str(index_path))
    assert len(analyzer.index.concepts) == 1
    assert analyzer.index.matches[0].validated is True

    # Add new concept and ensure subsequent save/resume persists metadata
    analyzer.index.add_concept(_make_doc_concept("docs/doc2.md:section"))
    analyzer.index.save(str(index_path))

    analyzer2 = SemanticAnalyzer(llm_client=MagicMock(), root_dir=str(tmp_path), resume_from=str(index_path))
    assert len(analyzer2.index.concepts) == 2


def test_resume_skips_already_validated_matches(tmp_path, capsys):
    """Ensure validate_with_physical_links only processes unvalidated matches."""
    index = SemanticIndex()
    index.add_concept(_make_doc_concept("docs/README.md:intro"))
    index.add_concept(_make_code_concept("src/app.py:main"))
    index.add_match(_make_match("src/app.py:main", "docs/README.md:intro", validated=True))
    index.save(tmp_path / "index.json")

    analyzer = SemanticAnalyzer(
        llm_client=MagicMock(),
        root_dir=str(tmp_path),
        resume_from=str(tmp_path / "index.json"),
    )

    analyzer.validate_with_physical_links(verbose=True)
    captured = capsys.readouterr()
    assert "already validated" in captured.out
