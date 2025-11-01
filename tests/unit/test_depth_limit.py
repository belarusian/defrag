"""
Test that intelligent scanner respects depth limits.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from defrag.intelligent_scanner import IntelligentScanner


def test_scanner_respects_depth_limit():
    """Test that scanner stops at max_depth."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple nested structure
        Path(tmpdir, "level1").mkdir()
        Path(tmpdir, "level1/level2").mkdir()
        Path(tmpdir, "level1/level2/level3").mkdir()

        # Put a file at each level
        Path(tmpdir, "root.py").write_text("# root")
        Path(tmpdir, "level1/one.py").write_text("# one")
        Path(tmpdir, "level1/level2/two.py").write_text("# two")
        Path(tmpdir, "level1/level2/level3/three.py").write_text("# three")

        # Mock LLM that always wants to go deeper
        mock_llm = Mock()

        def mock_response(prompt, max_tokens, log_context, validator, schema_retry_builder):
            # Check which directory we're in based on the prompt
            if "Current directory: level1/level2/level3/" in prompt:
                return {
                    "scan_files": ["three.py"],
                    "explore_subdirs": [],
                    "file_categories": {"three.py": "code"},
                    "reasoning": "Deepest level",
                }
            elif "Current directory: level1/level2/" in prompt:
                return {
                    "scan_files": ["two.py"],
                    "explore_subdirs": ["level3"],
                    "file_categories": {"two.py": "code"},
                    "reasoning": "Going deeper",
                }
            elif "Current directory: level1/" in prompt:
                return {
                    "scan_files": ["one.py"],
                    "explore_subdirs": ["level2"],
                    "file_categories": {"one.py": "code"},
                    "reasoning": "Going deeper",
                }
            else:  # Root - "Current directory: ./"
                return {
                    "scan_files": ["root.py"],
                    "explore_subdirs": ["level1"],
                    "file_categories": {"root.py": "code"},
                    "reasoning": "Starting scan",
                }

        mock_llm._request_json.side_effect = mock_response

        # Test with max_depth=2 (should get root and level1 only)
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(max_depth=2, verbose=False)

        code_files = results["code"]

        # Should find files at depth 0 and 1
        assert "root.py" in code_files
        assert "level1/one.py" in code_files

        # Should NOT find files at depth 2 or deeper
        assert "level1/level2/two.py" not in code_files
        assert "level1/level2/level3/three.py" not in code_files


def test_scanner_handles_deep_structure():
    """Test that scanner can handle deep structures with higher limit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create the same structure
        Path(tmpdir, "level1").mkdir()
        Path(tmpdir, "level1/level2").mkdir()
        Path(tmpdir, "level1/level2/level3").mkdir()

        Path(tmpdir, "root.py").write_text("# root")
        Path(tmpdir, "level1/one.py").write_text("# one")
        Path(tmpdir, "level1/level2/two.py").write_text("# two")
        Path(tmpdir, "level1/level2/level3/three.py").write_text("# three")

        # Same mock LLM
        mock_llm = Mock()

        def mock_response(prompt, max_tokens, log_context, validator, schema_retry_builder):
            # Check which directory we're in based on the prompt
            if "Current directory: level1/level2/level3/" in prompt:
                return {
                    "scan_files": ["three.py"],
                    "explore_subdirs": [],
                    "file_categories": {"three.py": "code"},
                    "reasoning": "Deepest level",
                }
            elif "Current directory: level1/level2/" in prompt:
                return {
                    "scan_files": ["two.py"],
                    "explore_subdirs": ["level3"],
                    "file_categories": {"two.py": "code"},
                    "reasoning": "Going deeper",
                }
            elif "Current directory: level1/" in prompt:
                return {
                    "scan_files": ["one.py"],
                    "explore_subdirs": ["level2"],
                    "file_categories": {"one.py": "code"},
                    "reasoning": "Going deeper",
                }
            else:  # Root - "Current directory: ./"
                return {
                    "scan_files": ["root.py"],
                    "explore_subdirs": ["level1"],
                    "file_categories": {"root.py": "code"},
                    "reasoning": "Starting scan",
                }

        mock_llm._request_json.side_effect = mock_response

        # Test with max_depth=10 (should get all files)
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(max_depth=10, verbose=False)

        code_files = results["code"]

        # Should find ALL files
        assert "root.py" in code_files
        assert "level1/one.py" in code_files
        assert "level1/level2/two.py" in code_files
        assert "level1/level2/level3/three.py" in code_files
