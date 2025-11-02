"""Integration test for crash and resume workflow."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from defrag.analyzer import SemanticAnalyzer
from defrag.semantic import SemanticIndex


def test_full_crash_resume_workflow():
    """
    Simulate a complete crash and resume scenario.

    Workflow:
    1. Start analysis with 3 docs and 2 code files
    2. Process 2 docs, 1 code file, then "crash" (simulate by stopping early)
    3. Save partial index
    4. Resume from partial index
    5. Verify only remaining files are processed
    6. Verify final index is complete
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create test files
        (tmp_path / "doc1.md").write_text("# Doc 1\nContent")
        (tmp_path / "doc2.md").write_text("# Doc 2\nContent")
        (tmp_path / "doc3.md").write_text("# Doc 3\nContent")
        (tmp_path / "code1.py").write_text("def func1(): pass")
        (tmp_path / "code2.py").write_text("def func2(): pass")

        # === FIRST RUN: Process partial data then "crash" ===
        mock_llm1 = MagicMock()

        # Mock doc concept extraction
        def doc_concept_side_effect(section, content):
            if "Doc 1" in section:
                return {"description": "Doc 1 description", "keywords": ["doc1"]}
            elif "Doc 2" in section:
                return {"description": "Doc 2 description", "keywords": ["doc2"]}
            else:
                raise RuntimeError("Simulated crash before processing doc3")

        mock_llm1.extract_doc_concept.side_effect = doc_concept_side_effect

        # Mock code concept extraction
        mock_llm1.extract_code_concept.return_value = {
            "description": "Function description",
            "keywords": ["func"],
        }

        analyzer1 = SemanticAnalyzer(llm_client=mock_llm1, root_dir=str(tmp_path))

        # Process first 2 docs successfully
        try:
            analyzer1.analyze_documentation(["doc1.md", "doc2.md", "doc3.md"], verbose=False)
        except RuntimeError:
            # Simulated crash - this is expected
            pass

        # Process first code file
        analyzer1.analyze_python_file("code1.py", verbose=False)

        # Verify partial state
        assert len(analyzer1.index.concepts) == 3  # 2 docs + 1 code
        doc_concepts_1 = analyzer1.index.get_doc_concepts()
        code_concepts_1 = analyzer1.index.get_code_concepts()
        assert len(doc_concepts_1) == 2  # Only doc1 and doc2
        assert len(code_concepts_1) == 1  # Only code1

        # Save partial index (simulating what happens before crash)
        index_path = tmp_path / "semantic_index.json"
        analyzer1.index.save(str(index_path))

        # === SECOND RUN: Resume and complete ===
        mock_llm2 = MagicMock()

        # Mock for remaining doc
        mock_llm2.extract_doc_concept.return_value = {
            "description": "Doc 3 description",
            "keywords": ["doc3"],
        }

        # Mock for remaining code
        mock_llm2.extract_code_concept.return_value = {
            "description": "Func2 description",
            "keywords": ["func2"],
        }

        # Mock matching
        mock_llm2.match_concepts.return_value = [
            {"doc_index": 0, "confidence": 0.85, "reasoning": "Test match"}
        ]

        # Resume from partial index
        analyzer2 = SemanticAnalyzer(
            llm_client=mock_llm2,
            root_dir=str(tmp_path),
            resume_from=str(index_path),
        )

        # Verify resumed state
        assert len(analyzer2.index.concepts) == 3  # Loaded from index

        # Process all docs (should skip doc1 and doc2)
        analyzer2.analyze_documentation(["doc1.md", "doc2.md", "doc3.md"], verbose=False)

        # Should have processed only doc3
        assert mock_llm2.extract_doc_concept.call_count == 1

        # Process all code (should skip code1.py)
        analyzer2.analyze_python_file("code1.py", verbose=False)
        analyzer2.analyze_python_file("code2.py", verbose=False)

        # Should have processed only code2
        assert mock_llm2.extract_code_concept.call_count == 1

        # Verify final state
        assert len(analyzer2.index.concepts) == 5  # 3 docs + 2 code
        doc_concepts_2 = analyzer2.index.get_doc_concepts()
        code_concepts_2 = analyzer2.index.get_code_concepts()
        assert len(doc_concepts_2) == 3
        assert len(code_concepts_2) == 2

        # Run matching
        analyzer2.match_all_concepts(verbose=False)

        # Should match 2 code concepts to docs (skipping already matched)
        # code1 was from first run, code2 is new
        assert mock_llm2.match_concepts.call_count == 2

        # Validate
        analyzer2.validate_with_physical_links(verbose=False)

        # All matches should be validated
        assert all(m.validated for m in analyzer2.index.matches)


def test_resume_with_file_modification_between_runs():
    """
    Test that files modified between runs are reprocessed.

    Workflow:
    1. Process file
    2. Save index
    3. Modify file
    4. Resume - should detect change and reprocess
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        doc_path = tmp_path / "doc.md"
        doc_path.write_text("# Original\nOriginal content")

        # First run
        mock_llm1 = MagicMock()
        mock_llm1.extract_doc_concept.return_value = {
            "description": "Original description",
            "keywords": ["original"],
        }

        analyzer1 = SemanticAnalyzer(llm_client=mock_llm1, root_dir=str(tmp_path))
        analyzer1.analyze_documentation(["doc.md"], verbose=False)

        assert mock_llm1.extract_doc_concept.call_count == 1
        original_concept_id = list(analyzer1.index.concepts.keys())[0]

        # Save
        index_path = tmp_path / "index.json"
        analyzer1.index.save(str(index_path))

        # Modify file
        doc_path.write_text("# Modified\nNew content here")

        # Resume
        mock_llm2 = MagicMock()
        mock_llm2.extract_doc_concept.return_value = {
            "description": "New description",
            "keywords": ["new"],
        }

        analyzer2 = SemanticAnalyzer(
            llm_client=mock_llm2,
            root_dir=str(tmp_path),
            resume_from=str(index_path),
        )

        # Should have loaded 1 concept
        assert len(analyzer2.index.concepts) == 1

        # Process (should detect change)
        analyzer2.analyze_documentation(["doc.md"], verbose=False)

        # Should have reprocessed (file changed)
        assert mock_llm2.extract_doc_concept.call_count == 1

        # Old concept should be gone, new one present
        assert original_concept_id not in analyzer2.index.concepts
        new_concept = list(analyzer2.index.concepts.values())[0]
        assert new_concept.description == "New description"
        assert new_concept.keywords == ["new"]


def test_resume_preserves_matches_and_validation():
    """
    Test that matches and validation state are preserved across resume.

    Workflow:
    1. Process docs and code
    2. Match concepts
    3. Validate matches
    4. Save
    5. Resume
    6. Verify matches and validation preserved
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        (tmp_path / "doc.md").write_text("# Feature\nDescription")
        (tmp_path / "code.py").write_text("def feature(): pass")

        # First run - complete analysis
        mock_llm1 = MagicMock()
        mock_llm1.extract_doc_concept.return_value = {
            "description": "Feature description",
            "keywords": ["feature"],
        }
        mock_llm1.extract_code_concept.return_value = {
            "description": "Feature implementation",
            "keywords": ["feature"],
        }
        mock_llm1.match_concepts.return_value = [
            {"doc_index": 0, "confidence": 0.90, "reasoning": "Both about feature"}
        ]

        analyzer1 = SemanticAnalyzer(llm_client=mock_llm1, root_dir=str(tmp_path))
        analyzer1.analyze_documentation(["doc.md"], verbose=False)
        analyzer1.analyze_python_file("code.py", verbose=False)
        analyzer1.match_all_concepts(verbose=False)
        analyzer1.validate_with_physical_links(verbose=False)

        # Verify state before save
        assert len(analyzer1.index.matches) == 1
        match = analyzer1.index.matches[0]
        assert match.confidence == 0.90
        assert match.validated is True

        # Save
        index_path = tmp_path / "index.json"
        analyzer1.index.save(str(index_path))

        # Resume
        analyzer2 = SemanticAnalyzer(
            llm_client=MagicMock(),
            root_dir=str(tmp_path),
            resume_from=str(index_path),
        )

        # Verify matches preserved
        assert len(analyzer2.index.matches) == 1
        resumed_match = analyzer2.index.matches[0]
        assert resumed_match.confidence == 0.90
        assert resumed_match.reasoning == "Both about feature"
        assert resumed_match.validated is True

        # Process again (should skip everything)
        analyzer2.analyze_documentation(["doc.md"], verbose=False)
        analyzer2.analyze_python_file("code.py", verbose=False)
        analyzer2.match_all_concepts(verbose=False)
        analyzer2.validate_with_physical_links(verbose=False)

        # State should be unchanged
        assert len(analyzer2.index.matches) == 1


def test_resume_after_multiple_crashes():
    """
    Test that resume works correctly after multiple crash/resume cycles.

    Simulates: crash -> resume -> crash -> resume
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        index_path = tmp_path / "index.json"

        # Create files
        for i in range(1, 6):
            (tmp_path / f"doc{i}.md").write_text(f"# Doc {i}\nContent")

        # Cycle 1: Process 2 docs
        mock_llm1 = MagicMock()
        mock_llm1.extract_doc_concept.return_value = {"description": "Desc", "keywords": ["k"]}

        analyzer1 = SemanticAnalyzer(llm_client=mock_llm1, root_dir=str(tmp_path))
        analyzer1.analyze_documentation(["doc1.md", "doc2.md"], verbose=False)
        analyzer1.index.save(str(index_path))

        assert len(analyzer1.index.concepts) == 2

        # Cycle 2: Resume and process 2 more
        mock_llm2 = MagicMock()
        mock_llm2.extract_doc_concept.return_value = {"description": "Desc", "keywords": ["k"]}

        analyzer2 = SemanticAnalyzer(
            llm_client=mock_llm2,
            root_dir=str(tmp_path),
            resume_from=str(index_path),
        )
        analyzer2.analyze_documentation(["doc1.md", "doc2.md", "doc3.md", "doc4.md"], verbose=False)
        analyzer2.index.save(str(index_path))

        # Should have 4 concepts now (2 old + 2 new)
        assert len(analyzer2.index.concepts) == 4
        # Should only process 2 new docs
        assert mock_llm2.extract_doc_concept.call_count == 2

        # Cycle 3: Resume and process final doc
        mock_llm3 = MagicMock()
        mock_llm3.extract_doc_concept.return_value = {"description": "Desc", "keywords": ["k"]}

        analyzer3 = SemanticAnalyzer(
            llm_client=mock_llm3,
            root_dir=str(tmp_path),
            resume_from=str(index_path),
        )
        analyzer3.analyze_documentation(
            ["doc1.md", "doc2.md", "doc3.md", "doc4.md", "doc5.md"],
            verbose=False,
        )

        # Should have all 5 concepts
        assert len(analyzer3.index.concepts) == 5
        # Should only process 1 new doc
        assert mock_llm3.extract_doc_concept.call_count == 1
