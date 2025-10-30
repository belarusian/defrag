"""
Auto-fix missing physical links in documentation.

Inserts code references based on semantic matches.
"""

import os
import re
from typing import List, Optional, Tuple

from .semantic import SemanticIndex


def find_section_in_markdown(content: str, section_name: str) -> Optional[Tuple[int, int]]:
    """
    Find line range for a markdown section.

    Args:
        content: Full markdown content
        section_name: Section header text (without #)

    Returns:
        Tuple of (start_line, end_line) or None if not found
        Lines are 0-indexed
    """
    lines = content.split("\n")
    section_start = None
    section_level = None

    for i, line in enumerate(lines):
        # Check for markdown header
        match = re.match(r"^(#+)\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            header_text = match.group(2).strip()

            if header_text.lower() == section_name.lower():
                section_start = i
                section_level = level
                continue

            # If we found our section and now hit same/higher level header, section ends
            if section_start is not None and level <= section_level:
                return (section_start, i - 1)

    # If we found section but no end, it goes to EOF
    if section_start is not None:
        return (section_start, len(lines) - 1)

    return None


def insert_code_reference(
    content: str, section_name: str, code_ref: str, reasoning: str = None
) -> Tuple[str, bool]:
    """
    Insert code reference into markdown section.

    Args:
        content: Full markdown content
        section_name: Section to insert into
        code_ref: Code reference (e.g., file.py:123-456)
        reasoning: Optional explanation

    Returns:
        Tuple of (modified_content, success)
    """
    section_range = find_section_in_markdown(content, section_name)
    if not section_range:
        return content, False

    start_line, end_line = section_range
    lines = content.split("\n")

    # Find a good insertion point (before next header or at end of section)
    # Look for existing "See:" or "Reference:" lines to group with
    insert_at = end_line

    for i in range(start_line + 1, end_line + 1):
        line = lines[i].strip()
        # If we find existing references, insert near them
        if line.startswith("See:") or line.startswith("Reference:") or line.startswith("Code:"):
            insert_at = i + 1
            break
        # If we hit another header, insert before it
        if line.startswith("#"):
            insert_at = i
            break

    # Build reference line
    if reasoning:
        ref_line = f"See `{code_ref}` - {reasoning}"
    else:
        ref_line = f"See `{code_ref}`"

    # Insert with proper spacing
    lines.insert(insert_at, "")
    lines.insert(insert_at + 1, ref_line)

    return "\n".join(lines), True


def fix_document_references(
    doc_path: str,
    semantic_index: SemanticIndex,
    root_dir: str = ".",
    dry_run: bool = False,
    verbose: bool = False,
) -> List[str]:
    """
    Auto-fix missing physical references in a document.

    Args:
        doc_path: Path to documentation file
        semantic_index: Semantic index with matches
        root_dir: Root directory
        dry_run: If True, don't write changes
        verbose: Print changes

    Returns:
        List of changes made
    """
    full_path = os.path.join(root_dir, doc_path)

    if not os.path.exists(full_path):
        if verbose:
            print(f"Error: Document not found: {doc_path}")
        return []

    # Get all matches for this doc
    matches = semantic_index.get_matches_for_doc(doc_path)

    # Filter for high confidence matches without valid physical links
    fixable = [
        m
        for m in matches
        if m.confidence >= 0.7 and not m.physical_link_valid and m.suggested_link
    ]

    if not fixable:
        if verbose:
            print(f"No fixable matches for {doc_path}")
        return []

    # Read current content
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    changes = []
    modified_content = content

    for match in fixable:
        doc_concept = semantic_index.get_concept(match.doc_concept_id)
        code_concept = semantic_index.get_concept(match.code_concept_id)

        if not doc_concept or not code_concept:
            continue

        # Try to insert reference
        new_content, success = insert_code_reference(
            modified_content, doc_concept.location, match.suggested_link, match.reasoning
        )

        if success:
            modified_content = new_content
            change_desc = (
                f"Added reference in '{doc_concept.location}': {match.suggested_link} "
                f"(confidence: {match.confidence:.2f})"
            )
            changes.append(change_desc)

            if verbose:
                print(f"  + {change_desc}")

    # Write changes if not dry run
    if changes and not dry_run:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(modified_content)

        if verbose:
            print(f"\nWrote {len(changes)} changes to {doc_path}")

    elif changes and dry_run:
        if verbose:
            print(f"\n[DRY RUN] Would write {len(changes)} changes to {doc_path}")

    return changes


def fix_all_documents(
    semantic_index: SemanticIndex,
    root_dir: str = ".",
    dry_run: bool = False,
    min_confidence: float = 0.7,
    verbose: bool = False,
) -> dict:
    """
    Auto-fix all documents with missing references.

    Args:
        semantic_index: Semantic index with matches
        root_dir: Root directory
        dry_run: If True, don't write changes
        min_confidence: Minimum confidence to auto-fix
        verbose: Print changes

    Returns:
        Dictionary with doc_path -> list of changes
    """
    # Get all docs with fixable matches
    all_changes = {}

    # Group matches by doc
    docs_with_matches = set()
    for match in semantic_index.matches:
        if match.confidence >= min_confidence and not match.physical_link_valid:
            doc_concept = semantic_index.get_concept(match.doc_concept_id)
            if doc_concept:
                docs_with_matches.add(doc_concept.source)

    if verbose:
        print(f"Found {len(docs_with_matches)} documents with fixable matches")
        print()

    for doc_path in sorted(docs_with_matches):
        if verbose:
            print(f"Fixing {doc_path}...")

        changes = fix_document_references(doc_path, semantic_index, root_dir, dry_run, verbose)

        if changes:
            all_changes[doc_path] = changes

        if verbose:
            print()

    return all_changes


def preview_fix(doc_path: str, semantic_index: SemanticIndex, root_dir: str = ".") -> str:
    """
    Preview what would be fixed in a document.

    Args:
        doc_path: Path to documentation file
        semantic_index: Semantic index with matches
        root_dir: Root directory

    Returns:
        Human-readable preview string
    """
    matches = semantic_index.get_matches_for_doc(doc_path)
    fixable = [
        m
        for m in matches
        if m.confidence >= 0.7 and not m.physical_link_valid and m.suggested_link
    ]

    if not fixable:
        return f"No fixable matches found for {doc_path}"

    lines = [f"Preview fixes for {doc_path}:", ""]

    for i, match in enumerate(fixable, 1):
        doc_concept = semantic_index.get_concept(match.doc_concept_id)
        code_concept = semantic_index.get_concept(match.code_concept_id)

        if not doc_concept or not code_concept:
            continue

        lines.append(f"{i}. Section: {doc_concept.location}")
        lines.append(f"   Reference: {match.suggested_link}")
        lines.append(f"   Confidence: {match.confidence:.2f}")
        lines.append(f"   Reasoning: {match.reasoning}")
        lines.append("")

    return "\n".join(lines)
