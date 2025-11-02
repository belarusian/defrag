"""Unit tests for semantic CLI resume flows using stub clients."""

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
        target_index = 0
        for idx, doc in enumerate(doc_concepts):
            if code_keywords & {kw.lower() for kw in doc.get("keywords", [])}:
                target_index = idx
                break

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


@pytest.fixture(autouse=True)
def stub_cli_dependencies(monkeypatch):
    monkeypatch.setattr("defrag.semantic_cli.LLMClient", StubLLMClient)
    monkeypatch.setattr("defrag.semantic_cli.scan_intelligently", scan_python_files)
    StubLLMClient.instances = []


@pytest.mark.unit
def test_semantic_cli_resume_round_trip(tmp_path):
    """CLI-level resume flow should skip previously analyzed files."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "feature.md").write_text("# feature\nFeature overview.")

    code_dir = tmp_path / "src"
    code_dir.mkdir()
    (code_dir / "feature.py").write_text("def feature():\n    return 'feature'\n")

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

    cmd_semantic_analyze(args)
    assert len(StubLLMClient.instances) == 1

    # Add new files
    (docs_dir / "new_feature.md").write_text("# new_feature\nNew feature details.")
    (code_dir / "new_feature.py").write_text("def new_feature():\n    return 'new'\n")

    resume_kwargs = vars(args).copy()
    resume_kwargs["resume"] = True
    resume_args = SimpleNamespace(**resume_kwargs)
    cmd_semantic_analyze(resume_args)

    assert len(StubLLMClient.instances) == 2
    resume_client = StubLLMClient.instances[-1]
    assert resume_client.extract_doc_concept_calls == ["new_feature"]
    assert [call[0] for call in resume_client.extract_code_concept_calls] == ["src/new_feature.py"]


@pytest.mark.unit
def test_semantic_fix_resume_after_failure(monkeypatch, tmp_path):
    """Resume state ensures Step 1 is skipped and conceptual docs are generated once."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    doc_path = docs_dir / "guide.md"
    doc_path.write_text("# Intro\nDocumentation without link.\n")

    code_dir = tmp_path / "src"
    code_dir.mkdir()
    (code_dir / "module.py").write_text("def handler():\n    return True\n")
    (code_dir / "undocumented.py").write_text("def undocumented_func():\n    return 1\n")

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
    handler_concept = Concept(
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
    index.add_concept(handler_concept)
    index.add_concept(undocumented_concept)
    index.add_match(
        ConceptMatch(
            code_concept_id=handler_concept.id,
            doc_concept_id=doc_concept.id,
            confidence=0.9,
            reasoning="Doc explains handler",
            physical_link_valid=False,
            suggested_link="src/module.py:1",
        )
    )
    index.save(tmp_path / "semantic_index.json")

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

    with pytest.raises(RuntimeError):
        cmd_semantic_fix(args)

    content_after_first_run = doc_path.read_text()
    assert content_after_first_run.count("src/module.py:1") == 1

    state_path = tmp_path / ".defrag_fix_state.json"
    assert state_path.exists()

    resume_kwargs = vars(args).copy()
    resume_kwargs["resume"] = True
    resume_args = SimpleNamespace(**resume_kwargs)
    cmd_semantic_fix(resume_args)
    assert call_state["count"] == 2

    resumed_content = doc_path.read_text()
    assert resumed_content.count("src/module.py:1") == 1

    generated_doc = docs_dir / "undocumented_func.md"
    assert generated_doc.exists()
    assert not state_path.exists()
