"""
Real integration test for intelligent file discovery.

This test actually runs the intelligent discovery with the LLM to verify
it correctly discovers and categorizes files in a project.

Requirements:
- LLM provider API key must be set (ANTHROPIC_API_KEY or OPENAI_API_KEY)
- This will make real API calls
"""

import os
import tempfile
from pathlib import Path
import json

import pytest

from defrag.llm import LLMClient
from defrag.intelligent_scanner import IntelligentScanner
from defrag.semantic_cli import cmd_semantic_analyze


@pytest.mark.integration
def test_intelligent_discovery_real_project():
    """Integration test: Intelligent scanner discovers files in a real project structure using LLM."""

    # Skip if no API key is available
    provider = os.getenv("DEFRAG_LLM_PROVIDER", "anthropic")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a realistic Python project structure
        # Root files
        Path(tmpdir, "README.md").write_text(
            """# TestProject

A test Python project for validating intelligent discovery.

## Installation
`pip install -e .`

## Usage
Import and use the main module.
"""
        )

        Path(tmpdir, "setup.py").write_text(
            """from setuptools import setup, find_packages

setup(
    name="testproject",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["requests", "pytest"],
)
"""
        )

        Path(tmpdir, "requirements.txt").write_text(
            """requests>=2.25.0
pytest>=6.0.0
black>=21.0
"""
        )

        Path(tmpdir, ".gitignore").write_text(
            """*.pyc
__pycache__/
.venv/
venv/
build/
dist/
*.egg-info/
"""
        )

        # Main package
        pkg = Path(tmpdir, "testproject")
        pkg.mkdir()

        Path(pkg, "__init__.py").write_text(
            '''"""TestProject - A sample Python package."""

__version__ = "0.1.0"
__author__ = "Test Author"

from .core import process_data
from .utils import format_output
'''
        )

        Path(pkg, "core.py").write_text(
            '''"""Core processing module."""

def process_data(data):
    """Process input data and return results.

    Args:
        data: Input data to process

    Returns:
        Processed results
    """
    return {"processed": data, "status": "success"}
'''
        )

        Path(pkg, "utils.py").write_text(
            '''"""Utility functions."""

def format_output(result):
    """Format result for display."""
    return f"Result: {result}"

def validate_input(data):
    """Validate input data."""
    return data is not None
'''
        )

        # Submodule
        handlers = pkg / "handlers"
        handlers.mkdir()

        Path(handlers, "__init__.py").write_text('"""Request handlers."""')

        Path(handlers, "http.py").write_text(
            '''"""HTTP request handler."""

def handle_request(request):
    """Handle incoming HTTP request."""
    return {"status": 200, "body": "OK"}
'''
        )

        # Config directory
        config = Path(tmpdir, "config")
        config.mkdir()

        Path(config, "settings.json").write_text(
            """{
    "debug": true,
    "port": 8080
}"""
        )

        # Tests directory
        tests = Path(tmpdir, "tests")
        tests.mkdir()

        Path(tests, "conftest.py").write_text(
            '''"""Pytest configuration."""
import pytest

@pytest.fixture
def sample_data():
    return {"test": "data"}
'''
        )

        Path(tests, "test_core.py").write_text(
            '''"""Tests for core module."""

from testproject.core import process_data

def test_process_data(sample_data):
    result = process_data(sample_data)
    assert result["status"] == "success"
'''
        )

        # Documentation
        docs = Path(tmpdir, "docs")
        docs.mkdir()

        Path(docs, "api.md").write_text(
            """# API Documentation

## Core Functions

### process_data(data)
Processes input data and returns results.

### format_output(result)
Formats results for display.
"""
        )

        Path(docs, "development.md").write_text(
            """# Development Guide

## Setup
1. Clone the repository
2. Install dependencies
3. Run tests
"""
        )

        # Build artifacts (should be skipped)
        build = Path(tmpdir, "build")
        build.mkdir()
        Path(build, "lib.so").write_text("binary")

        dist = Path(tmpdir, "dist")
        dist.mkdir()
        Path(dist, "testproject-0.1.0.whl").write_text("wheel")

        # Virtual environment (should be skipped)
        venv = Path(tmpdir, ".venv")
        venv.mkdir()
        venv_lib = venv / "lib" / "python3.9"
        venv_lib.mkdir(parents=True)
        Path(venv_lib, "some_package.py").write_text("# venv file")

        # Node modules (should be skipped even in Python project)
        node = Path(tmpdir, "node_modules")
        node.mkdir()
        Path(node, "some_package.js").write_text("// npm package")

        # Now run the intelligent scanner with real LLM
        print(f"\nRunning intelligent discovery on test project in {tmpdir}")
        print(f"Using provider: {provider}")

        llm = LLMClient()
        scanner = IntelligentScanner(llm, tmpdir)

        # Run discovery
        results = scanner.scan(verbose=True)

        # Verify results
        print("\n=== Discovery Results ===")
        for category, files in results.items():
            if files:
                print(f"\n{category}: {len(files)} files")
                for f in sorted(files)[:5]:
                    print(f"  - {f}")
                if len(files) > 5:
                    print(f"  ... and {len(files) - 5} more")

        # Assertions for code files
        code_files = results.get("code", [])
        assert "testproject/__init__.py" in code_files, "Should find package __init__"
        assert "testproject/core.py" in code_files, "Should find core module"
        assert "testproject/utils.py" in code_files, "Should find utils module"
        assert "testproject/handlers/http.py" in code_files, "Should find handler module"
        assert "tests/test_core.py" in code_files, "Should find test files"

        # Assertions for documentation
        doc_files = results.get("documentation", [])
        assert "README.md" in doc_files, "Should find README"
        assert "docs/api.md" in doc_files, "Should find API docs"
        assert "docs/development.md" in doc_files, "Should find dev guide"

        # Assertions for config files
        config_files = results.get("config", [])
        assert "setup.py" in config_files or "setup.py" in results.get(
            "other", []
        ), "Should find setup.py"
        assert "requirements.txt" in config_files or "requirements.txt" in results.get(
            "other", []
        ), "Should find requirements"

        # Should NOT find files in excluded directories
        all_files = [f for files in results.values() for f in files]
        assert not any(".venv/" in f or ".venv\\" in f for f in all_files), "Should not scan .venv"
        assert not any(
            "node_modules/" in f or "node_modules\\" in f for f in all_files
        ), "Should not scan node_modules"
        assert not any(
            "build/" in f or "build\\" in f for f in all_files
        ), "Should not scan build artifacts"
        assert not any("dist/" in f or "dist\\" in f for f in all_files), "Should not scan dist"

        print("\n✅ Intelligent discovery correctly identified project structure")
        print(f"  - Found {len(code_files)} code files")
        print(f"  - Found {len(doc_files)} documentation files")
        print("  - Correctly excluded dependency and build directories")

        # Save results for inspection
        results_file = Path(tmpdir, "discovery_results.json")
        results_file.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to: {results_file}")


@pytest.mark.integration
def test_semantic_analyze_with_intelligent_discovery():
    """Integration test: Full semantic-analyze command with intelligent discovery."""

    # Skip if no API key
    provider = os.getenv("DEFRAG_LLM_PROVIDER", "anthropic")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal project
        Path(tmpdir, "README.md").write_text(
            """# Minimal Test Project

This project tests intelligent discovery in semantic analysis.
"""
        )

        pkg = Path(tmpdir, "example")
        pkg.mkdir()

        Path(pkg, "__init__.py").write_text('"""Example package."""')

        Path(pkg, "main.py").write_text(
            '''"""Main module."""

def run():
    """Run the application."""
    print("Running")
'''
        )

        # Run semantic-analyze
        # Create args object (can't use class due to scope issues with provider variable)
        from types import SimpleNamespace

        args = SimpleNamespace(
            root=tmpdir,
            verbose=True,
            limit_docs=None,  # No limits - test full functionality
            limit_code=None,  # No limits - test full functionality
            model=None,  # Use default
            api_key=None,  # Use from env
            output="semantic_index.json",  # Explicit output path
            provider=provider,
            iterations=1,
        )

        print("\nRunning semantic-analyze with intelligent discovery")
        print(f"Root: {tmpdir}")
        print(f"Provider: {provider}")

        # Run the command
        cmd_semantic_analyze(args)

        # Check that semantic index was created
        index_path = Path(tmpdir, "semantic_index.json")
        assert index_path.exists(), "semantic_index.json should be created"

        # Load and verify index
        with open(index_path) as f:
            index = json.load(f)

        print("\n✅ Semantic analysis completed successfully")

        # Handle concepts as dictionary (concept_id -> concept_data)
        concepts = index.get("concepts", {})
        matches = index.get("matches", [])

        print(f"  - Concepts extracted: {len(concepts)}")
        print(f"  - Matches found: {len(matches)}")

        # Should have found at least some concepts
        assert len(concepts) > 0, "Should have discovered and analyzed some files"

        # Extract source files from concepts
        sources = set()
        for concept_id, concept_data in concepts.items():
            if isinstance(concept_data, dict) and "source" in concept_data:
                sources.add(concept_data["source"])

        print(f"  - Source files analyzed: {sorted(sources)}")


if __name__ == "__main__":
    # Run with pytest to get proper output
    pytest.main([__file__, "-v", "-s", "-k", "integration"])
