"""
Unit tests for deep directory scanning with configurable limits.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from defrag.intelligent_scanner import IntelligentScanner


def test_scanner_respects_max_depth():
    """Test that scanner respects max_depth parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create deep directory structure
        current = Path(tmpdir)
        paths_created = []
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir()
            file_path = current / f"file{i}.py"
            file_path.write_text(f"# Level {i}")
            paths_created.append(
                "level0/level1/level2"[: 3 * (i + 2)] + f"/file{i}.py"
                if i > 0
                else "level0/file0.py"
            )

        # Mock LLM that always explores deeper
        mock_llm = Mock()

        def always_explore(prompt, max_tokens, log_context, validator, schema_retry_builder):
            # Always scan current file and explore subdirs
            if "level9" in log_context:
                return {
                    "scan_files": ["file9.py"],
                    "explore_subdirs": [],
                    "file_categories": {"file9.py": "code"},
                    "reasoning": "Deepest level",
                }
            for i in range(9):
                if f"level{i}" in log_context:
                    return {
                        "scan_files": [f"file{i}.py"],
                        "explore_subdirs": [f"level{i+1}"],
                        "file_categories": {f"file{i}.py": "code"},
                        "reasoning": "Continue exploring",
                    }
            return {
                "scan_files": [],
                "explore_subdirs": ["level0"],
                "file_categories": {},
                "reasoning": "Start exploring",
            }

        mock_llm._request_json.side_effect = always_explore

        # Test with max_depth=3
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(max_depth=3, verbose=False)

        # Should only find files up to depth 3
        code_files = results["code"]
        assert len(code_files) == 3  # files at depth 0, 1, 2
        assert "level0/file0.py" in code_files
        assert "level0/level1/file1.py" in code_files
        assert "level0/level1/level2/file2.py" in code_files
        # Should NOT find deeper files
        assert not any("level3" in f for f in code_files)


def test_scanner_unlimited_depth():
    """Test that scanner can go unlimited depth with None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create moderately deep structure
        current = Path(tmpdir)
        for i in range(5):
            current = current / f"level{i}"
            current.mkdir()
            (current / f"file{i}.py").write_text(f"# Level {i}")

        # Mock LLM
        mock_llm = Mock()

        def explore_all(prompt, max_tokens, log_context, validator, schema_retry_builder):
            for i in range(5):
                if f"level{i}/" in log_context or f"level{i}\\" in log_context:
                    next_level = f"level{i+1}" if i < 4 else None
                    return {
                        "scan_files": [f"file{i}.py"],
                        "explore_subdirs": [next_level] if next_level else [],
                        "file_categories": {f"file{i}.py": "code"},
                        "reasoning": "Exploring",
                    }
            return {
                "scan_files": [],
                "explore_subdirs": ["level0"],
                "file_categories": {},
                "reasoning": "Start",
            }

        mock_llm._request_json.side_effect = explore_all

        # Test with unlimited depth
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(max_depth=None, verbose=False)

        # Should find all files
        code_files = results["code"]
        assert len(code_files) == 5


def test_scanner_respects_max_files():
    """Test that scanner stops when max_files is reached."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create structure with many files
        for i in range(10):
            Path(tmpdir, f"file{i}.py").write_text(f"# File {i}")

        # Mock LLM that would scan all files
        mock_llm = Mock()
        mock_llm._request_json.return_value = {
            "scan_files": [f"file{i}.py" for i in range(10)],
            "explore_subdirs": [],
            "file_categories": {f"file{i}.py": "code" for i in range(10)},
            "reasoning": "Scan all",
        }

        # Test with max_files=5
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(max_files=5, verbose=False)

        # Should stop after 5 files
        total_files = sum(len(files) for files in results.values())
        assert total_files <= 5


def test_deep_monorepo_structure():
    """Test handling of deep monorepo-style structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Java-style deep package structure
        java_path = (
            Path(tmpdir)
            / "src"
            / "main"
            / "java"
            / "com"
            / "company"
            / "product"
            / "module"
            / "submodule"
            / "component"
        )
        java_path.mkdir(parents=True)
        (java_path / "Service.java").write_text("public class Service {}")

        # Create deeply nested feature folders
        feature_path = (
            Path(tmpdir)
            / "features"
            / "auth"
            / "login"
            / "oauth"
            / "providers"
            / "google"
            / "v2"
            / "impl"
        )
        feature_path.mkdir(parents=True)
        (feature_path / "handler.py").write_text("def handle(): pass")

        # Mock LLM that navigates the structure
        mock_llm = Mock()
        visited_paths = []

        def smart_explore(prompt, max_tokens, log_context, validator, schema_retry_builder):
            visited_paths.append(log_context)

            # Navigate based on current location
            if "Service.java" in prompt:
                return {
                    "scan_files": ["Service.java"],
                    "explore_subdirs": [],
                    "file_categories": {"Service.java": "code"},
                    "reasoning": "Java service",
                }
            elif "handler.py" in prompt:
                return {
                    "scan_files": ["handler.py"],
                    "explore_subdirs": [],
                    "file_categories": {"handler.py": "code"},
                    "reasoning": "Python handler",
                }

            # Navigate directories
            if "src" in prompt and "main" not in prompt:
                return {
                    "scan_files": [],
                    "explore_subdirs": ["main"],
                    "file_categories": {},
                    "reasoning": "Java structure",
                }
            elif "main" in prompt and "java" not in prompt:
                return {
                    "scan_files": [],
                    "explore_subdirs": ["java"],
                    "file_categories": {},
                    "reasoning": "Java source",
                }
            elif "java" in prompt and "com" not in prompt:
                return {
                    "scan_files": [],
                    "explore_subdirs": ["com"],
                    "file_categories": {},
                    "reasoning": "Package root",
                }
            elif "features" in prompt and "auth" not in prompt:
                return {
                    "scan_files": [],
                    "explore_subdirs": ["auth"],
                    "file_categories": {},
                    "reasoning": "Features",
                }

            # Continue exploring subdirs intelligently
            subdirs = []
            if "com" in prompt:
                subdirs = ["company"]
            elif "company" in prompt:
                subdirs = ["product"]
            elif "product" in prompt:
                subdirs = ["module"]
            elif "module" in prompt and "submodule" not in prompt:
                subdirs = ["submodule"]
            elif "submodule" in prompt:
                subdirs = ["component"]
            elif "auth" in prompt and "login" not in prompt:
                subdirs = ["login"]
            elif "login" in prompt:
                subdirs = ["oauth"]
            elif "oauth" in prompt:
                subdirs = ["providers"]
            elif "providers" in prompt:
                subdirs = ["google"]
            elif "google" in prompt:
                subdirs = ["v2"]
            elif "v2" in prompt:
                subdirs = ["impl"]
            elif "/" not in prompt:  # Root
                subdirs = ["src", "features"]

            return {
                "scan_files": [],
                "explore_subdirs": subdirs,
                "file_categories": {},
                "reasoning": "Exploring structure",
            }

        mock_llm._request_json.side_effect = smart_explore

        # Test with high depth limit
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(max_depth=50, verbose=False)

        # Should find both deeply nested files
        code_files = results["code"]
        assert any("Service.java" in f for f in code_files), "Should find deep Java file"
        assert any("handler.py" in f for f in code_files), "Should find deep Python file"
