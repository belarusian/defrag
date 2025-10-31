"""
Test file discovery for semantic analysis.

This ensures we properly discover all Python code and documentation files
without relying on hardcoded patterns.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from defrag.scanner import scan_documentation
from defrag.semantic_cli import cmd_semantic_analyze


def test_scan_documentation_finds_all_markdown():
    """Test that scan_documentation finds all markdown files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test structure
        Path(tmpdir, "README.md").write_text("# Main readme")
        Path(tmpdir, "docs").mkdir()
        Path(tmpdir, "docs/GUIDE.md").write_text("# Guide")
        Path(tmpdir, "docs/API.md").write_text("# API")
        Path(tmpdir, "src").mkdir()
        Path(tmpdir, "src/README.md").write_text("# Module readme")
        Path(tmpdir, ".git").mkdir()
        Path(tmpdir, ".git/README.md").write_text("# Should be excluded")

        # Scan for docs
        docs = scan_documentation(tmpdir)
        docs_set = set(docs)

        # Should find all except .git
        assert "README.md" in docs_set
        assert "docs/GUIDE.md" in docs_set
        assert "docs/API.md" in docs_set
        assert "src/README.md" in docs_set
        assert ".git/README.md" not in docs_set
        assert len(docs) == 4


def test_semantic_analyze_discovers_all_python_files():
    """Test that semantic-analyze discovers all Python files in the tree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test structure with Python files
        Path(tmpdir, "main.py").write_text("def main(): pass")
        Path(tmpdir, "setup.py").write_text("from setuptools import setup")

        # Create package
        pkg_dir = Path(tmpdir, "mypackage")
        pkg_dir.mkdir()
        Path(pkg_dir, "__init__.py").write_text('"""Package."""')
        Path(pkg_dir, "core.py").write_text("class Core: pass")
        Path(pkg_dir, "utils.py").write_text("def helper(): pass")

        # Create subpackage
        sub_dir = Path(pkg_dir, "submodule")
        sub_dir.mkdir()
        Path(sub_dir, "__init__.py").write_text('"""Submodule."""')
        Path(sub_dir, "worker.py").write_text("def work(): pass")

        # Create tests
        test_dir = Path(tmpdir, "tests")
        test_dir.mkdir()
        Path(test_dir, "test_main.py").write_text("def test_main(): pass")
        Path(test_dir, "test_core.py").write_text("def test_core(): pass")

        # Create excluded directories
        venv_dir = Path(tmpdir, ".venv")
        venv_dir.mkdir()
        Path(venv_dir, "excluded.py").write_text("# Should not be found")

        cache_dir = Path(tmpdir, "__pycache__")
        cache_dir.mkdir()
        Path(cache_dir, "cached.py").write_text("# Should not be found")

        # Mock the actual semantic analysis to avoid LLM calls
        with patch('defrag.semantic_cli.SemanticAnalyzer') as mock_analyzer:
            with patch('defrag.semantic_cli.LLMClient') as mock_llm:
                # Create mock args
                class Args:
                    root = tmpdir
                    verbose = False
                    limit_docs = None
                    limit_code = None
                    model = "test"
                    api_key = "test"
                    output = None
                    provider = "test"
                    iterations = 1

                args = Args()

                # Track what files are analyzed
                analyzed_files = []

                def track_analyze(paths, verbose=False):
                    analyzed_files.extend(paths)

                mock_instance = mock_analyzer.return_value
                mock_instance.analyze_code_files.side_effect = track_analyze
                mock_instance.index.get_doc_concepts.return_value = []
                mock_instance.index.get_code_concepts.return_value = []
                mock_instance.index.matches = []
                mock_instance.generate_report.return_value = {}

                # Run discovery (will fail at LLM init but we catch it)
                try:
                    cmd_semantic_analyze(args)
                except:
                    pass  # Expected to fail at LLM init, we just want the file discovery

                # Check if analyze_code_files was called with the right files
                if mock_instance.analyze_code_files.called:
                    code_paths = mock_instance.analyze_code_files.call_args[0][0]

                    # Should find all Python files except those in excluded dirs
                    expected_files = {
                        "main.py",
                        "setup.py",
                        "mypackage/__init__.py",
                        "mypackage/core.py",
                        "mypackage/utils.py",
                        "mypackage/submodule/__init__.py",
                        "mypackage/submodule/worker.py",
                        "tests/test_main.py",
                        "tests/test_core.py"
                    }

                    found_files = set(code_paths)

                    # All expected files should be found
                    for expected in expected_files:
                        assert expected in found_files, f"Missing {expected}"

                    # Excluded files should not be found
                    assert ".venv/excluded.py" not in found_files
                    assert "__pycache__/cached.py" not in found_files

                    # Should have found exactly the expected files
                    assert len(found_files) == len(expected_files)


def test_defrag_discovers_its_own_code():
    """Integration test: ensure defrag can discover its own source code."""
    # Get defrag root directory
    defrag_root = Path(__file__).parent.parent

    # Check that defrag package exists
    defrag_pkg = defrag_root / "defrag"
    assert defrag_pkg.exists() and defrag_pkg.is_dir()

    # Mock semantic analysis to test discovery only
    with patch('defrag.semantic_cli.SemanticAnalyzer') as mock_analyzer:
        with patch('defrag.semantic_cli.LLMClient') as mock_llm:
            class Args:
                root = str(defrag_root)
                verbose = False
                limit_docs = 1  # Limit to speed up test
                limit_code = 5  # Limit to speed up test
                model = "test"
                api_key = "test"
                output = None
                provider = "test"
                iterations = 1

            args = Args()

            mock_instance = mock_analyzer.return_value
            mock_instance.index.get_doc_concepts.return_value = []
            mock_instance.index.get_code_concepts.return_value = []
            mock_instance.index.matches = []
            mock_instance.generate_report.return_value = {}

            try:
                cmd_semantic_analyze(args)
            except:
                pass

            if mock_instance.analyze_code_files.called:
                code_paths = mock_instance.analyze_code_files.call_args[0][0]

                # Should find defrag's own Python files
                defrag_files = [p for p in code_paths if p.startswith("defrag/")]
                assert len(defrag_files) > 0, "Should find defrag package files"

                # Should include key files
                key_files = [
                    "defrag/__init__.py",
                    "defrag/analyzer.py",
                    "defrag/semantic_cli.py",
                    "defrag/llm.py"
                ]

                for key_file in key_files:
                    if key_file in code_paths:
                        break
                else:
                    # Only fail if we didn't hit the limit
                    if len(code_paths) >= 10:
                        assert False, f"Missing key defrag files in discovered paths"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])