import json
import os
from types import SimpleNamespace

import pytest

from defrag.semantic import Concept, ConceptMatch, SemanticIndex
from defrag.semantic_cli import cmd_semantic_analyze, cmd_semantic_fix


class StubLLMClient:
    SUPPORTED_PROVIDERS = {"anthropic"}
    DEFAULT_MODELS = {"anthropic": "stub-model"}
    PROVIDER_ENV_VAR = "DEFRAG_LLM_PROVIDER"
    PROVIDER_KEY_ENVS = {"anthropic": "ANTHROPIC_API_KEY"}

    instances = []

    def __init__(self, model=None, provider="anthropic", api_key=None, root_dir="."):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.root_dir = root_dir
        self.extract_doc_concept_calls = []
        self.extract_code_concept_calls = []
        self.match_concepts_calls = []
        StubLLMClient.instances.append(self)

    def extract_doc_concept(self, section_name, content):
        self.extract_doc_concept_calls.append(section_name)
        return {
            "description": f"{section_name} documentation",
            "keywords": [section_name.lower()],
        }

    def extract_code_concept(self, file_path, location, snippet):
        self.extract_code_concept_calls.append((file_path, location))
        return {
            "description": f"{location} implementation",
            "keywords": [location.lower()],
        }

    def match_concepts(self, code_concept, doc_concepts, max_iterations=1):
        self.match_concepts_calls.append(code_concept)
        if not doc_concepts:
            return []

        code_keywords = {kw.lower() for kw in code_concept.get("keywords", [])}
        target_index = None
        for idx, doc in enumerate(doc_concepts):
            doc_keywords = {kw.lower() for kw in doc.get("keywords", [])}
            if code_keywords & doc_keywords:
                target_index = idx
                break

        if target_index is None:
            target_index = 0

        return [
            {
                "doc_index": target_index,
                "confidence": 0.9,
                "reasoning": "stub keyword match",
            }
        ]


def scan_python_files(llm, root_dir, verbose=False):
    """Simple stand-in for intelligent discovery that finds *.py files."""
    code_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if name.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(dirpath, name), root_dir)
                code_files.append(rel_path)
    return {"code": sorted(code_files)}


@pytest.mark.integration
def test_semantic_cli_resume_round_trip(monkeypatch, tmp_path):
    """End-to-end CLI resume flow that skips unchanged files and processes new ones."""

    # Create initial doc and code files
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    doc1 = docs_dir / "feature.md"
    doc1.write_text("# feature\nFeature overview.")

    code_dir = tmp_path / "src"
    code_dir.mkdir()
    code1 = code_dir / "feature.py"
    code1.write_text(
        "def feature():\n"
        "    return 'feature'\n"
    )

    # Patch LLM client and intelligent scanner
    monkeypatch.setattr("defrag.semantic_cli.LLMClient", StubLLMClient)
    monkeypatch.setattr("defrag.semantic_cli.scan_intelligently", scan_python_files)

    # First run - build index from scratch
    StubLLMClient.instances = []
    args = SimpleNamespace(
        root=str(tmp_path),
        verbose=False,
        limit_docs=None,
        limit_code=None,
        model=None,
        api_key=None,
        output="semantic_index.json",
        provider="anthropic",
        resume=False,
    )

    result = cmd_semantic_analyze(args)
    assert result == 0
    assert len(StubLLMClient.instances) == 1
    first_client = StubLLMClient.instances[0]
    assert first_client.extract_doc_concept_calls == ["feature"]
    assert [call[0] for call in first_client.extract_code_concept_calls] == ["src/feature.py"]
    assert len(first_client.match_concepts_calls) == 1

    index_path = tmp_path / "semantic_index.json"
    assert index_path.exists()
    index = SemanticIndex.load(str(index_path))
    assert len(index.get_doc_concepts()) == 1
    assert len(index.get_code_concepts()) == 1

    # Add new doc and code before resuming
    doc2 = docs_dir / "new_feature.md"
    doc2.write_text("# new_feature\nNew feature details.")
    code2 = code_dir / "new_feature.py"
    code2.write_text(
        "def new_feature():\n"
        "    return 'new'\n"
    )

    # Second run - resume should skip existing files and process new ones
    StubLLMClient.instances = []
    resume_args = SimpleNamespace(
        root=str(tmp_path),
        verbose=False,
        limit_docs=None,
        limit_code=None,
        model=None,
        api_key=None,
        output="semantic_index.json",
        provider="anthropic",
        resume=True,
    )

    result = cmd_semantic_analyze(resume_args)
    assert result == 0
    assert len(StubLLMClient.instances) == 1
    resume_client = StubLLMClient.instances[0]
    # Only the new doc and code should trigger LLM extraction
    assert resume_client.extract_doc_concept_calls == ["new_feature"]
    assert [call[0] for call in resume_client.extract_code_concept_calls] == ["src/new_feature.py"]
    assert len(resume_client.match_concepts_calls) == 1

    # Final index combines old + new concepts without duplication
    final_index = SemanticIndex.load(str(index_path))
    assert len(final_index.get_doc_concepts()) == 2
    assert len(final_index.get_code_concepts()) == 2
    assert len(final_index.matches) == 2
    assert all(match.validated for match in final_index.matches)


@pytest.mark.integration
def test_semantic_fix_resume_after_failure(monkeypatch, tmp_path):
    """Ensure semantic-fix can resume after a crash and skips completed work."""

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    doc_path = docs_dir / "guide.md"
    doc_path.write_text("# Intro\nDocumentation without link.\n")

    code_dir = tmp_path / "src"
    code_dir.mkdir()
    code_path = code_dir / "module.py"
    code_path.write_text(
        "def handler():\n"
        "    return True\n"
    )
    extra_code_path = code_dir / "undocumented.py"
    extra_code_path.write_text(
        "def undocumented_func():\n"
        "    return 1\n"
    )

    # Build a semantic index with one match missing a physical link
    index = SemanticIndex()
    doc_concept = Concept(
        id="doc:docs/guide.md:intro",
        source="docs/guide.md",
        source_type="doc",
        location="Intro",
        description="Intro section",
        keywords=["intro"],
        line_range=(1, 2),
        raw_content="Intro content",
    )
    code_concept = Concept(
        id="code:src/module.py:handler",
        source="src/module.py",
        source_type="code",
        location="handler",
        description="Handler implementation",
        keywords=["handler"],
        line_range=(1, 2),
        raw_content="def handler(): return True",
    )
    undocumented_concept = Concept(
        id="code:src/undocumented.py:undocumented_func",
        source="src/undocumented.py",
        source_type="code",
        location="undocumented_func",
        description="Undocumented function",
        keywords=["undocumented"],
        line_range=(1, 2),
        raw_content="def undocumented_func(): return 1",
    )
    index.add_concept(doc_concept)
    index.add_concept(code_concept)
    index.add_concept(undocumented_concept)
    index.add_match(
        ConceptMatch(
            code_concept_id=code_concept.id,
            doc_concept_id=doc_concept.id,
            confidence=0.9,
            reasoning="Doc explains handler",
            physical_link_valid=False,
            suggested_link="src/module.py:1",
        )
    )
    index_path = tmp_path / "semantic_index.json"
    index.save(str(index_path))

    # Patch dependencies to avoid real LLM calls
    monkeypatch.setattr("defrag.semantic_cli.LLMClient", StubLLMClient)
    monkeypatch.setattr(
        "defrag.fixer.rewrite_document_with_llm",
        lambda **kwargs: (None, {}),
    )

    call_state = {"count": 0}

    def fake_generate_docs(self, undocumented_concepts, verbose=False):
        call_state["count"] += 1
        self.last_generated_clusters = {}
        if call_state["count"] == 1:
            raise RuntimeError("Simulated LLM failure")
        docs = {}
        for concept in undocumented_concepts:
            doc_name = f"{concept.location}.md"
            doc_path = f"docs/{doc_name}"
            docs[doc_path] = f"# {concept.location}\nGenerated documentation."
            self.last_generated_clusters[doc_path] = [concept.id]
        return docs

    monkeypatch.setattr(
        "defrag.autodoc.ConceptualDocGenerator.generate_docs_for_undocumented",
        fake_generate_docs,
    )

    args = SimpleNamespace(
        root=str(tmp_path),
        semantic_index="semantic_index.json",
        apply=True,
        min_confidence=0.7,
        provider="anthropic",
        model=None,
        api_key=None,
        resume=False,
    )

    # First run crashes during conceptual doc generation
    with pytest.raises(RuntimeError):
        cmd_semantic_fix(args)

    # Step 1 should have added the reference exactly once
    content_after_first_run = doc_path.read_text()
    assert content_after_first_run.count("src/module.py:1") == 1

    # Progress state should exist and record the completed document
    state_path = tmp_path / ".defrag_fix_state.json"
    assert state_path.exists()
    state_data = json.loads(state_path.read_text())
    assert "docs/guide.md" in state_data["docs_completed"]
    assert state_data["code_processed"] == []

    # The semantic index should reflect validated links
    updated_index = SemanticIndex.load(str(index_path))
    assert updated_index.matches[0].physical_link_valid is True
    assert updated_index.matches[0].validated is True

    # Resume run should skip Step 1 and finish conceptual doc generation
    resume_args = SimpleNamespace(
        root=str(tmp_path),
        semantic_index="semantic_index.json",
        apply=True,
        min_confidence=0.7,
        provider="anthropic",
        model=None,
        api_key=None,
        resume=True,
    )

    result = cmd_semantic_fix(resume_args)
    assert result == 0
    assert call_state["count"] == 2

    # Reference is not duplicated
    resumed_content = doc_path.read_text()
    assert resumed_content.count("src/module.py:1") == 1

    # Conceptual documentation created on resume
    generated_doc = docs_dir / "undocumented_func.md"
    assert generated_doc.exists()

    # Progress state cleared after success
    assert not state_path.exists()
