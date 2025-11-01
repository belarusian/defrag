"""
Unit tests for autodoc security features.

Tests filename sanitization and path traversal prevention.
"""

import tempfile
from pathlib import Path
import pytest

from defrag.autodoc import ConceptualDocGenerator
from unittest.mock import Mock


class TestAutoDocSecurity:
    """Test security features of auto-doc generation."""

    def test_sanitize_filename_removes_path_traversal(self):
        """Test that path traversal attempts are sanitized."""
        generator = ConceptualDocGenerator(Mock(), ".")

        # Test various path traversal attempts - should extract just the filename
        assert generator.sanitize_filename("../../etc/passwd") == "passwd.md"
        assert generator.sanitize_filename("../README.md") == "README.md"
        assert generator.sanitize_filename("docs/../../../README.md") == "README.md"
        assert generator.sanitize_filename("/etc/hosts") == "hosts.md"
        assert generator.sanitize_filename("\\windows\\system32\\config") == "config.md"

    def test_sanitize_filename_removes_dangerous_characters(self):
        """Test that dangerous characters are removed."""
        generator = ConceptualDocGenerator(Mock(), ".")

        assert generator.sanitize_filename("file:with:colons") == "file_with_colons.md"
        assert generator.sanitize_filename('file"with"quotes') == "file_with_quotes.md"
        assert generator.sanitize_filename("file|with|pipes") == "file_with_pipes.md"
        assert generator.sanitize_filename("file<with>brackets") == "file_with_brackets.md"
        assert generator.sanitize_filename("file?with?questions") == "file_with_questions.md"
        assert generator.sanitize_filename("file*with*asterisks") == "file_with_asterisks.md"

    def test_sanitize_filename_handles_null_bytes(self):
        """Test that null bytes are removed."""
        generator = ConceptualDocGenerator(Mock(), ".")

        assert generator.sanitize_filename("file\x00with\x00nulls") == "filewithnulls.md"

    def test_sanitize_filename_ensures_md_extension(self):
        """Test that .md extension is ensured."""
        generator = ConceptualDocGenerator(Mock(), ".")

        assert generator.sanitize_filename("readme") == "readme.md"
        assert generator.sanitize_filename("readme.txt") == "readme.txt.md"
        assert generator.sanitize_filename("readme.md") == "readme.md"

    def test_sanitize_filename_handles_empty_input(self):
        """Test that empty or invalid input gets default name."""
        generator = ConceptualDocGenerator(Mock(), ".")

        assert generator.sanitize_filename("") == "generated-doc.md"
        assert generator.sanitize_filename("...") == "generated-doc.md"
        assert generator.sanitize_filename("   ") == "generated-doc.md"
        assert generator.sanitize_filename("..") == "generated-doc.md"

    def test_write_prevents_path_traversal(self):
        """Test that write_generated_docs prevents path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConceptualDocGenerator(Mock(), tmpdir)

            # Create a docs directory
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Attempt to write outside docs directory
            generated_docs = {
                "../README.md": "Malicious content",
            }

            with pytest.raises(
                ValueError, match="Security: Attempted to write outside docs/ directory"
            ):
                generator.write_generated_docs(generated_docs, tmpdir)

    def test_write_prevents_complex_path_traversal(self):
        """Test that complex path traversal is prevented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConceptualDocGenerator(Mock(), tmpdir)

            # Create a docs directory
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Attempt complex path traversal
            generated_docs = {
                "docs/../../README.md": "Malicious content",
            }

            with pytest.raises(ValueError, match="Security: Path traversal detected"):
                generator.write_generated_docs(generated_docs, tmpdir)

    def test_write_handles_existing_files(self):
        """Test that existing files are not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConceptualDocGenerator(Mock(), tmpdir)

            # Create docs directory and existing file
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            existing_file = docs_dir / "api.md"
            existing_file.write_text("Existing important documentation")

            # Try to write to the same file
            generated_docs = {
                "docs/api.md": "Generated content",
            }

            # Should create alternative file
            written = generator.write_generated_docs(generated_docs, tmpdir, verbose=True)

            # Check that original file is unchanged
            assert existing_file.read_text() == "Existing important documentation"

            # Check that alternative file was created
            assert "docs/api-generated-1.md" in written
            alternative_file = docs_dir / "api-generated-1.md"
            assert alternative_file.exists()
            assert alternative_file.read_text() == "Generated content"

    def test_write_dry_run_skips_existing(self):
        """Test that dry run mode skips existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConceptualDocGenerator(Mock(), tmpdir)

            # Create docs directory and existing file
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            existing_file = docs_dir / "api.md"
            existing_file.write_text("Existing documentation")

            # Try to write in dry run mode
            generated_docs = {
                "docs/api.md": "Generated content",
            }

            # Should skip the file
            written = generator.write_generated_docs(
                generated_docs, tmpdir, dry_run=True, verbose=True
            )

            # Check that file is unchanged
            assert existing_file.read_text() == "Existing documentation"
            assert written == []  # Nothing written in dry run

    def test_write_creates_multiple_alternatives(self):
        """Test that multiple alternatives are created when needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConceptualDocGenerator(Mock(), tmpdir)

            # Create docs directory and existing files
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "cache.md").write_text("Original")
            (docs_dir / "cache-generated-1.md").write_text("First alternative")

            # Try to write to cache.md
            generated_docs = {
                "docs/cache.md": "New generated content",
            }

            written = generator.write_generated_docs(generated_docs, tmpdir)

            # Should create cache-generated-2.md
            assert "docs/cache-generated-2.md" in written
            alternative_file = docs_dir / "cache-generated-2.md"
            assert alternative_file.exists()
            assert alternative_file.read_text() == "New generated content"
