"""
Scanner for documentation files and code references.

Discovers markdown files and extracts code reference patterns.
"""

import os
import re
from pathlib import Path
from typing import List, Set


# Pattern to match code references in documentation
# Formats:
#   path/to/file.py:123
#   path/to/file.py:123-456
#   `path/to/file.py:123`
CODE_REF_PATTERN = re.compile(
    r'`?([a-zA-Z0-9_/\-\.]+\.(py|ts|js|java|go|rs|md)):(\d+)(?:-(\d+))?`?'
)


def scan_documentation(root_dir: str, exclude_dirs: Set[str] = None) -> List[str]:
    """
    Scan directory tree for markdown documentation files.

    Args:
        root_dir: Root directory to scan
        exclude_dirs: Set of directory names to exclude (default: node_modules, .git, etc.)

    Returns:
        List of relative paths to markdown files
    """
    if exclude_dirs is None:
        exclude_dirs = {
            "node_modules",
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            "cdk.out",
            "cdk.out-cdc",
            "cdk.out-neptune",
            "cdk.out.deploy",
        }

    root_path = Path(root_dir).resolve()
    md_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out excluded directories in-place
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            if filename.endswith(".md"):
                full_path = Path(dirpath) / filename
                try:
                    relative_path = full_path.relative_to(root_path)
                    md_files.append(str(relative_path))
                except ValueError:
                    # Path not relative to root (shouldn't happen)
                    pass

    return sorted(md_files)


def extract_code_refs(doc_path: str) -> List[str]:
    """
    Extract code references from a documentation file.

    Looks for patterns like:
    - path/to/file.py:123
    - path/to/file.py:123-456
    - `path/to/file.py:123`

    Args:
        doc_path: Path to documentation file

    Returns:
        List of code references (normalized format: path:line or path:start-end)
    """
    if not os.path.exists(doc_path):
        return []

    refs = []
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        for match in CODE_REF_PATTERN.finditer(content):
            file_path = match.group(1)
            start_line = match.group(3)
            end_line = match.group(4)

            if end_line:
                ref = f"{file_path}:{start_line}-{end_line}"
            else:
                ref = f"{file_path}:{start_line}"

            refs.append(ref)

    except (IOError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {doc_path}: {e}")

    return refs


def scan_code_references(doc_path: str, root_dir: str = ".") -> List[str]:
    """
    Scan a documentation file for code references and validate paths.

    Args:
        doc_path: Path to documentation file
        root_dir: Root directory for resolving relative paths

    Returns:
        List of validated code references
    """
    full_doc_path = os.path.join(root_dir, doc_path)
    refs = extract_code_refs(full_doc_path)

    # Normalize references to be relative to root_dir
    normalized = []
    for ref in refs:
        # Extract file path from reference
        parts = ref.split(":")
        if len(parts) >= 2:
            file_path = parts[0]
            line_info = ":".join(parts[1:])

            # Make path relative to root if it's absolute
            if os.path.isabs(file_path):
                try:
                    file_path = os.path.relpath(file_path, root_dir)
                except ValueError:
                    # Path not relative to root
                    pass

            normalized.append(f"{file_path}:{line_info}")
        else:
            normalized.append(ref)

    return normalized


def find_code_file(file_path: str, root_dir: str = ".") -> bool:
    """
    Check if a code file exists.

    Args:
        file_path: Relative path to code file
        root_dir: Root directory

    Returns:
        True if file exists
    """
    full_path = os.path.join(root_dir, file_path)
    return os.path.isfile(full_path)


def validate_line_range(file_path: str, start_line: int, end_line: int = None, root_dir: str = ".") -> bool:
    """
    Validate that line numbers exist in a file.

    Args:
        file_path: Relative path to code file
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (optional)
        root_dir: Root directory

    Returns:
        True if line range is valid
    """
    full_path = os.path.join(root_dir, file_path)

    if not os.path.isfile(full_path):
        return False

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)

        if start_line < 1 or start_line > total_lines:
            return False

        if end_line is not None:
            if end_line < start_line or end_line > total_lines:
                return False

        return True

    except (IOError, UnicodeDecodeError):
        return False
