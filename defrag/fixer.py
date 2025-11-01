"""
Auto-fix missing physical links in documentation.

Inserts code references based on semantic matches.
"""

import os
import re
from typing import List, Optional, Tuple

from .llm import LLMClient
from .semantic import Concept, SemanticIndex


def _extract_headings(markdown: str) -> set:
    headings = set()
    for line in markdown.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                headings.add(title.lower())
    return headings


def _is_rewrite_safe(original: str, rewritten: str) -> bool:
    orig_text = original.strip()
    new_text = rewritten.strip()

    if not new_text:
        return False

    orig_len = len(orig_text)
    new_len = len(new_text)

    if orig_len > 0:
        min_required = max(50, int(orig_len * 0.7))
        if new_len < min_required:
            return False

    orig_headings = _extract_headings(orig_text)
    new_headings = _extract_headings(new_text)

    if orig_headings and not orig_headings.issubset(new_headings):
        return False

    return True


def _clean_markdown_output(text: str) -> str:
    """Strip surrounding code fences and whitespace from LLM output."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```", 2)
        if len(parts) >= 2:
            cleaned = parts[1]
            if "\n" in cleaned:
                cleaned = cleaned.split("\n", 1)[1]
    return cleaned.strip()


def rewrite_document_with_llm(
    doc_path: str,
    original_content: str,
    matches_payload: List[dict],
    llm: LLMClient,
    max_tokens: int = 8000,
    verbose: bool = False,
) -> Optional[str]:
    """Intelligently merge references into documentation by processing sections."""

    if not matches_payload:
        return None

    # Group matches by section
    from collections import defaultdict
    sections_to_update = defaultdict(list)
    for payload in matches_payload:
        sections_to_update[payload['section']].append(payload)

    # Process each section that needs updates
    updated_content = original_content

    for section_name, section_matches in sections_to_update.items():
        # Find the section in the document
        section_range = find_section_in_markdown(updated_content, section_name)
        if not section_range:
            if verbose:
                print(f"    Warning: Section '{section_name}' not found in document")
            continue

        start_line, end_line = section_range
        lines = updated_content.split("\n")

        # Extract just this section
        section_lines = lines[start_line:end_line + 1]
        section_content = "\n".join(section_lines)

        # Skip if section is too small to meaningfully update
        if len(section_content.strip()) < 50:
            continue

        # Build focused prompt for just this section
        prompt_lines = [
            "You are integrating code references into a documentation section.",
            "Add the references naturally within the existing text.",
            "DO NOT just append references at the end.",
            "Weave them into the narrative where they make sense.",
            "",
            f"Section name: {section_name}",
            "",
            "Current section content:",
            "```markdown",
            section_content,
            "```",
            "",
            "Code references to integrate into this section:",
        ]

        for match in section_matches:
            prompt_lines.append(
                f"- Code: `{match['code_reference']}`"
            )
            prompt_lines.append(
                f"  Purpose: {match['code_summary']}"
            )
            prompt_lines.append(
                f"  Why it relates: {match['reasoning']}"
            )
            prompt_lines.append("")

        prompt_lines.extend([
            "Instructions:",
            "1. Keep the section structure and headings intact",
            "2. Integrate references naturally into sentences",
            "3. Use phrases like 'implemented in', 'as seen in', 'handled by', etc.",
            "4. Don't create bullet lists of references",
            "5. Return ONLY the updated section content",
            "",
            "Return the updated section with references woven into the text:"
        ])

        prompt = "\n".join(prompt_lines)

        # Calculate tokens needed for this section
        section_tokens = max(2000, len(section_content) // 2)  # More conservative estimate

        if verbose:
            print(f"    Updating section '{section_name}' ({len(section_content)} chars)")

        try:
            response = llm.generate_text(prompt, max_tokens=section_tokens)
            if not response:
                if verbose:
                    print(f"      LLM returned empty response for section")
                continue

            cleaned = _clean_markdown_output(response)
            if not cleaned:
                continue

            # Verify the section wasn't truncated
            if len(cleaned) < len(section_content) * 0.5:
                if verbose:
                    print(f"      Section response too short, skipping")
                continue

            # Replace the section in the document
            new_lines = lines[:start_line] + cleaned.split("\n") + lines[end_line + 1:]
            updated_content = "\n".join(new_lines)

            if verbose:
                print(f"      Successfully updated section")

        except Exception as exc:
            if verbose:
                print(f"      Failed to update section: {exc}")
            continue

    # If no sections were updated, return None to trigger fallback
    if updated_content == original_content:
        if verbose:
            print(f"    No sections could be updated")
        return None

    return updated_content


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
    llm_client: LLMClient,
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
        m for m in matches if m.confidence >= 0.7 and not m.physical_link_valid and m.suggested_link
    ]

    if not fixable:
        if verbose:
            print(f"No fixable matches for {doc_path}")
        return []

    # Read current content
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    payloads = []
    for match in fixable:
        doc_concept = semantic_index.get_concept(match.doc_concept_id)
        code_concept = semantic_index.get_concept(match.code_concept_id)

        if not doc_concept or not code_concept:
            continue

        if not isinstance(doc_concept, Concept) or not isinstance(code_concept, Concept):
            continue

        payloads.append(
            {
                "section": doc_concept.location,
                "code_reference": match.suggested_link,
                "reasoning": match.reasoning or "",
                "code_summary": code_concept.description,
                "confidence": match.confidence,
            }
        )

    if not payloads:
        if verbose:
            print(f"  Skipping {doc_path}: no usable match data")
        return []

    rewritten = rewrite_document_with_llm(
        doc_path=doc_path,
        original_content=content,
        matches_payload=payloads,
        llm=llm_client,
        verbose=verbose,
    )

    changes: List[str] = []

    if rewritten:
        if rewritten != content:
            if dry_run:
                if verbose:
                    print(
                        f"  [DRY RUN] Would rewrite {doc_path} with {len(payloads)} reference(s)"
                    )
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(rewritten)
                if verbose:
                    print(f"  Rewrote {doc_path} with {len(payloads)} reference(s)")

            changes.append(
                f"Rewrote document with {len(payloads)} reference(s) integrated"
            )
        else:
            if verbose:
                print(f"  LLM rewrite produced no changes for {doc_path}")
    else:
        if verbose:
            print(f"  Falling back to mechanical insertion for {doc_path}")

        modified_content = content
        fallback_changes = []
        for item in payloads:
            modified_content, success = insert_code_reference(
                modified_content,
                item["section"],
                item["code_reference"],
                item["reasoning"],
            )
            if success:
                fallback_changes.append(item)

        if fallback_changes:
            if dry_run:
                if verbose:
                    print(
                        f"    [DRY RUN] Would add {len(fallback_changes)} reference(s) mechanically"
                    )
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)
            for item in fallback_changes:
                changes.append(
                    f"Added reference in '{item['section']}': {item['code_reference']}"
                )

    return changes


def fix_all_documents(
    semantic_index: SemanticIndex,
    llm_client: LLMClient,
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

        changes = fix_document_references(
            doc_path,
            semantic_index,
            llm_client,
            root_dir=root_dir,
            dry_run=dry_run,
            verbose=verbose,
        )

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
        m for m in matches if m.confidence >= 0.7 and not m.physical_link_valid and m.suggested_link
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
