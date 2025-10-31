"""
Test intelligent file discovery using LLM guidance.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from defrag.intelligent_scanner import IntelligentScanner


def test_intelligent_scanner_basic_structure():
    """Test that intelligent scanner correctly handles directory structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a typical project structure
        Path(tmpdir, "README.md").write_text("# Project")
        Path(tmpdir, "setup.py").write_text("setup()")

        # Source code
        src = Path(tmpdir, "src")
        src.mkdir()
        Path(src, "__init__.py").write_text("")
        Path(src, "main.py").write_text("def main(): pass")
        Path(src, "utils.py").write_text("def util(): pass")

        # Tests
        tests = Path(tmpdir, "tests")
        tests.mkdir()
        Path(tests, "test_main.py").write_text("def test(): pass")

        # Docs
        docs = Path(tmpdir, "docs")
        docs.mkdir()
        Path(docs, "guide.md").write_text("# Guide")

        # Dependencies (should be skipped)
        venv = Path(tmpdir, ".venv")
        venv.mkdir()
        Path(venv, "skip.py").write_text("# Should not scan")

        # Create mock LLM client
        mock_llm = Mock()

        # Define mock responses for each directory
        def mock_request_json(prompt, max_tokens, log_context, validator, schema_retry_builder):
            # Parse which directory we're being asked about
            if "Current directory: ./" in prompt or "Current directory: /" in prompt:
                # Root directory
                return {
                    "scan_files": ["README.md", "setup.py"],
                    "explore_subdirs": ["src", "tests", "docs"],
                    "file_categories": {
                        "README.md": "documentation",
                        "setup.py": "config"
                    },
                    "reasoning": "Scanning project files, exploring source dirs"
                }
            elif "Current directory: src/" in prompt:
                return {
                    "scan_files": ["__init__.py", "main.py", "utils.py"],
                    "explore_subdirs": [],
                    "file_categories": {
                        "__init__.py": "code",
                        "main.py": "code",
                        "utils.py": "code"
                    },
                    "reasoning": "Python source files"
                }
            elif "Current directory: tests/" in prompt:
                return {
                    "scan_files": ["test_main.py"],
                    "explore_subdirs": [],
                    "file_categories": {
                        "test_main.py": "code"
                    },
                    "reasoning": "Test files"
                }
            elif "Current directory: docs/" in prompt:
                return {
                    "scan_files": ["guide.md"],
                    "explore_subdirs": [],
                    "file_categories": {
                        "guide.md": "documentation"
                    },
                    "reasoning": "Documentation"
                }
            else:
                return {
                    "scan_files": [],
                    "explore_subdirs": [],
                    "file_categories": {},
                    "reasoning": "Nothing to scan"
                }

        mock_llm._request_json.side_effect = mock_request_json

        # Run scanner
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(verbose=False)

        # Check results
        assert "README.md" in results["documentation"]
        assert "docs/guide.md" in results["documentation"]
        assert "setup.py" in results["config"]
        assert "src/__init__.py" in results["code"]
        assert "src/main.py" in results["code"]
        assert "src/utils.py" in results["code"]
        assert "tests/test_main.py" in results["code"]

        # Should not include .venv files
        assert not any(".venv" in f for category in results.values() for f in category)


def test_intelligent_scanner_fallback():
    """Test that scanner falls back to heuristics when LLM fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files
        Path(tmpdir, "main.py").write_text("main")
        Path(tmpdir, "README.md").write_text("readme")
        Path(tmpdir, "data.txt").write_text("data")

        # Mock LLM that always fails
        mock_llm = Mock()
        mock_llm._request_json.side_effect = Exception("LLM error")

        # Run scanner - should fall back to heuristics
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(verbose=False)

        # Should still categorize files using fallback
        assert "main.py" in results["code"]
        assert "README.md" in results["documentation"]


def test_intelligent_scanner_handles_deep_nesting():
    """Test that scanner respects max_depth."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create deeply nested structure
        current = Path(tmpdir)
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir()
            Path(current, f"file{i}.py").write_text(f"# Level {i}")

        # Mock LLM that always explores subdirs
        mock_llm = Mock()

        def always_explore(prompt, max_tokens, log_context, validator, schema_retry_builder):
            return {
                "scan_files": [],
                "explore_subdirs": [f"level{i}" for i in range(10)],
                "file_categories": {},
                "reasoning": "Exploring"
            }

        mock_llm._request_json.side_effect = always_explore

        # Run with max_depth=3
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(max_depth=3, verbose=False)

        # Should only go 3 levels deep
        assert len(scanner.visited_dirs) <= 4  # root + 3 levels


def test_intelligent_scanner_real_project_simulation():
    """Test scanner on a simulated real project structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create realistic project
        # Root files
        Path(tmpdir, "README.md").write_text("# My Project")
        Path(tmpdir, "LICENSE").write_text("MIT")
        Path(tmpdir, ".gitignore").write_text("*.pyc")
        Path(tmpdir, "setup.py").write_text("setup()")
        Path(tmpdir, "requirements.txt").write_text("pytest")

        # Package
        pkg = Path(tmpdir, "mypackage")
        pkg.mkdir()
        Path(pkg, "__init__.py").write_text('__version__ = "1.0"')
        Path(pkg, "core.py").write_text("class Core: pass")
        Path(pkg, "api.py").write_text("def api(): pass")

        # Subpackage
        sub = pkg / "submodule"
        sub.mkdir()
        Path(sub, "__init__.py").write_text("")
        Path(sub, "worker.py").write_text("def work(): pass")

        # Tests
        tests = Path(tmpdir, "tests")
        tests.mkdir()
        Path(tests, "conftest.py").write_text("fixtures")
        Path(tests, "test_core.py").write_text("tests")

        # Docs
        docs = Path(tmpdir, "docs")
        docs.mkdir()
        Path(docs, "index.md").write_text("# Docs")
        Path(docs, "api.md").write_text("# API")

        # Build artifacts (should skip)
        build = Path(tmpdir, "build")
        build.mkdir()
        Path(build, "lib.a").write_text("binary")

        # Mock intelligent LLM
        mock_llm = Mock()

        def intelligent_response(prompt, max_tokens, log_context, validator, schema_retry_builder):
            # Simulate intelligent decisions based on directory
            if ".gitignore" in prompt:
                # Root - scan important files, explore packages
                return {
                    "scan_files": ["README.md", "setup.py", "requirements.txt"],
                    "explore_subdirs": ["mypackage", "tests", "docs"],
                    "file_categories": {
                        "README.md": "documentation",
                        "setup.py": "config",
                        "requirements.txt": "config"
                    },
                    "reasoning": "Main project files and directories"
                }
            elif "mypackage" in log_context and "submodule" in prompt:
                # Package directory
                return {
                    "scan_files": ["__init__.py", "core.py", "api.py"],
                    "explore_subdirs": ["submodule"],
                    "file_categories": {
                        "__init__.py": "code",
                        "core.py": "code",
                        "api.py": "code"
                    },
                    "reasoning": "Python package files"
                }
            elif "submodule" in log_context:
                # Submodule
                return {
                    "scan_files": ["__init__.py", "worker.py"],
                    "explore_subdirs": [],
                    "file_categories": {
                        "__init__.py": "code",
                        "worker.py": "code"
                    },
                    "reasoning": "Submodule files"
                }
            elif "tests" in log_context:
                # Tests
                return {
                    "scan_files": ["conftest.py", "test_core.py"],
                    "explore_subdirs": [],
                    "file_categories": {
                        "conftest.py": "code",
                        "test_core.py": "code"
                    },
                    "reasoning": "Test files"
                }
            elif "docs" in log_context:
                # Documentation
                return {
                    "scan_files": ["index.md", "api.md"],
                    "explore_subdirs": [],
                    "file_categories": {
                        "index.md": "documentation",
                        "api.md": "documentation"
                    },
                    "reasoning": "Documentation files"
                }
            else:
                return {
                    "scan_files": [],
                    "explore_subdirs": [],
                    "file_categories": {},
                    "reasoning": "Nothing relevant"
                }

        mock_llm._request_json.side_effect = intelligent_response

        # Run scanner
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(verbose=False)

        # Verify categorization
        assert len(results["code"]) >= 5  # All .py files
        assert len(results["documentation"]) >= 3  # .md files
        assert len(results["config"]) >= 2  # setup.py, requirements.txt

        # Should not include build artifacts
        assert not any("build/" in f for category in results.values() for f in category)