import tempfile
from pathlib import Path
from unittest.mock import Mock

from defrag.fixer import fix_document_references
from defrag.semantic import Concept, ConceptMatch, SemanticIndex


def build_index(doc_path: str, section: str) -> SemanticIndex:
    index = SemanticIndex()

    doc_concept = Concept(
        id=f"doc:{doc_path}:{section}",
        source=doc_path,
        source_type="doc",
        location=section,
        description="Section describing the workflow",
        keywords=["workflow"],
    )

    code_concept = Concept(
        id="code:module:function",
        source="module.py",
        source_type="code",
        location="function",
        description="Implements the workflow",
        keywords=["workflow"],
    )

    index.add_concept(doc_concept)
    index.add_concept(code_concept)

    match = ConceptMatch(
        code_concept_id=code_concept.id,
        doc_concept_id=doc_concept.id,
        confidence=0.9,
        reasoning="The function implements the documented workflow.",
        suggested_link="module.py:10-20",
    )
    index.add_match(match)

    return index


def test_fix_document_references_uses_llm_rewrite(tmp_path):
    doc_path = "docs/guide.md"
    section = "Overview"
    index = build_index(doc_path, section)

    doc_file = tmp_path / "docs" / "guide.md"
    doc_file.parent.mkdir(parents=True)
    doc_file.write_text("# Overview\n\nExisting content about the workflow.\n")

    mock_llm = Mock()
    mock_llm.generate_text.return_value = (
        "# Overview\n\nUpdated overview referencing `module.py:10-20` inline.\n"
    )

    changes = fix_document_references(
        doc_path,
        index,
        mock_llm,
        root_dir=tmp_path,
        dry_run=False,
        verbose=False,
    )

    assert changes == ["Rewrote document with 1 reference(s) integrated"]
    updated = doc_file.read_text()
    assert "Updated overview referencing" in updated
    mock_llm.generate_text.assert_called_once()


def test_fix_document_references_fallback_mechanical(tmp_path):
    doc_path = "docs/guide.md"
    section = "Overview"
    index = build_index(doc_path, section)

    doc_file = tmp_path / "docs" / "guide.md"
    doc_file.parent.mkdir(parents=True)
    doc_file.write_text("# Overview\n\nExisting content about the workflow.\n")

    mock_llm = Mock()
    mock_llm.generate_text.return_value = ""

    changes = fix_document_references(
        doc_path,
        index,
        mock_llm,
        root_dir=tmp_path,
        dry_run=False,
        verbose=False,
    )

    updated = doc_file.read_text()
    assert "See `module.py:10-20`" in updated
    assert any("Added reference" in change for change in changes)
