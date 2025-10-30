"""
Validator for code references in documentation.

Checks if code references are valid and up-to-date.
"""

import os
import re
from typing import List, Tuple

from .schema import DocEntry, DocStatus
from .scanner import find_code_file, validate_line_range


def parse_code_ref(code_ref: str) -> Tuple[str, int, int]:
    """
    Parse a code reference into components.

    Args:
        code_ref: Code reference (format: path/to/file.py:123 or path/to/file.py:123-456)

    Returns:
        Tuple of (file_path, start_line, end_line)
        end_line is same as start_line if range not specified
    """
    match = re.match(r"^(.+):(\d+)(?:-(\d+))?$", code_ref)
    if not match:
        raise ValueError(f"Invalid code reference format: {code_ref}")

    file_path = match.group(1)
    start_line = int(match.group(2))
    end_line = int(match.group(3)) if match.group(3) else start_line

    return file_path, start_line, end_line


def validate_code_ref(code_ref: str, root_dir: str = ".") -> Tuple[bool, str]:
    """
    Validate a single code reference.

    Args:
        code_ref: Code reference to validate
        root_dir: Root directory

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        file_path, start_line, end_line = parse_code_ref(code_ref)
    except ValueError as e:
        return False, str(e)

    # Check if file exists
    if not find_code_file(file_path, root_dir):
        return False, f"File not found: {file_path}"

    # Check if line range is valid
    if not validate_line_range(file_path, start_line, end_line, root_dir):
        if end_line == start_line:
            return False, f"Line {start_line} out of range in {file_path}"
        else:
            return False, f"Lines {start_line}-{end_line} out of range in {file_path}"

    return True, ""


def validate_code_refs(code_refs: List[str], root_dir: str = ".") -> List[Tuple[str, bool, str]]:
    """
    Validate multiple code references.

    Args:
        code_refs: List of code references
        root_dir: Root directory

    Returns:
        List of tuples: (code_ref, is_valid, error_message)
    """
    results = []
    for ref in code_refs:
        is_valid, error = validate_code_ref(ref, root_dir)
        results.append((ref, is_valid, error))
    return results


def validate_doc(doc: DocEntry, root_dir: str = ".") -> Tuple[DocStatus, List[str]]:
    """
    Validate a documentation entry.

    Checks all code references and suggests a status.

    Args:
        doc: DocEntry to validate
        root_dir: Root directory

    Returns:
        Tuple of (suggested_status, list_of_issues)
    """
    if not doc.code_refs:
        # No code references - might be orphaned
        return DocStatus.UNCHECKED, ["No code references found"]

    results = validate_code_refs(doc.code_refs, root_dir)

    invalid_refs = [(ref, error) for ref, is_valid, error in results if not is_valid]

    if invalid_refs:
        issues = [f"{ref}: {error}" for ref, error in invalid_refs]
        return DocStatus.BAD, issues
    else:
        return DocStatus.GOOD, []


def suggest_fixes(doc: DocEntry, root_dir: str = ".") -> List[str]:
    """
    Suggest fixes for invalid code references.

    Args:
        doc: DocEntry with potentially invalid references
        root_dir: Root directory

    Returns:
        List of suggested fixes
    """
    fixes = []

    for ref in doc.code_refs:
        is_valid, error = validate_code_ref(ref, root_dir)
        if not is_valid:
            try:
                file_path, start_line, end_line = parse_code_ref(ref)

                if "not found" in error.lower():
                    fixes.append(f"Update or remove reference to missing file: {file_path}")
                elif "out of range" in error.lower():
                    fixes.append(f"Update line numbers for {file_path} (file may have changed)")
            except ValueError:
                fixes.append(f"Fix malformed code reference: {ref}")

    return fixes
