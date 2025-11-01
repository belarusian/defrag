"""
Unit tests for document and code scanning functions.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock


from defrag.scanner import scan_documentation
from defrag.intelligent_scanner import IntelligentScanner


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


def test_intelligent_scanner_with_mocked_llm():
    """Unit test: IntelligentScanner with mocked LLM responses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test structure
        Path(tmpdir, "main.py").write_text("def main(): pass")
        src = Path(tmpdir, "src")
        src.mkdir()
        Path(src, "utils.py").write_text("def util(): pass")

        # Mock LLM that returns predictable responses
        mock_llm = Mock()

        def mock_request_json(prompt, max_tokens, log_context, validator, schema_retry_builder):
            # Simulate intelligent decision based on directory
            if "src" in log_context:
                response = {
                    "scan_files": ["utils.py"],
                    "explore_subdirs": [],
                    "file_categories": {"utils.py": "code"},
                    "reasoning": "Python source file",
                }
            else:
                response = {
                    "scan_files": ["main.py"],
                    "explore_subdirs": ["src"],
                    "file_categories": {"main.py": "code"},
                    "reasoning": "Root Python file",
                }

            # Run through validator to mimic real behavior
            validated, issues = validator(response)
            return validated if not issues else response

        mock_llm._request_json.side_effect = mock_request_json

        # Run scanner
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(verbose=False)

        # Verify results
        assert "main.py" in results["code"]
        assert "src/utils.py" in results["code"]
        assert len(results["code"]) == 2


def test_intelligent_scanner_fallback_on_llm_failure():
    """Test that scanner uses fallback heuristics when LLM fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files
        Path(tmpdir, "script.py").write_text("print('hello')")
        Path(tmpdir, "README.md").write_text("# Docs")
        Path(tmpdir, "data.xyz").write_text("unknown")

        # Mock LLM that always fails
        mock_llm = Mock()
        mock_llm._request_json.side_effect = Exception("LLM error")

        # Run scanner - should use fallback
        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(verbose=False)

        # Fallback should categorize by extension
        assert "script.py" in results["code"]
        assert "README.md" in results["documentation"]
        # data.xyz won't be scanned by fallback (unknown extension)
        assert "data.xyz" not in results["other"]


def test_intelligent_scanner_handles_mixed_case_categories():
    """Test that scanner normalizes category names from LLM."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "test.py").write_text("test")

        mock_llm = Mock()

        def mock_response(prompt, max_tokens, log_context, validator, schema_retry_builder):
            # Return mixed-case category
            response = {
                "scan_files": ["test.py"],
                "explore_subdirs": [],
                "file_categories": {"test.py": "Code"},  # Wrong case!
                "reasoning": "test",
            }
            validated, _ = validator(response)
            return validated

        mock_llm._request_json.side_effect = mock_response

        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(verbose=False)

        # Should normalize "Code" to "code"
        assert "test.py" in results["code"]
        assert "test.py" not in results.get("Code", [])


def test_intelligent_scanner_handles_invalid_categories():
    """Test that scanner defaults unknown categories to 'other'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "weird.file").write_text("content")

        mock_llm = Mock()

        def mock_response(prompt, max_tokens, log_context, validator, schema_retry_builder):
            response = {
                "scan_files": ["weird.file"],
                "explore_subdirs": [],
                "file_categories": {"weird.file": "random-category"},  # Invalid!
                "reasoning": "test",
            }
            validated, _ = validator(response)
            return validated

        mock_llm._request_json.side_effect = mock_response

        scanner = IntelligentScanner(mock_llm, tmpdir)
        results = scanner.scan(verbose=False)

        # Should put unknown category in "other"
        assert "weird.file" in results["other"]
