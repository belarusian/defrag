"""
Auto-fix missing physical links in documentation.

Inserts code references based on semantic matches.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .llm import LLMClient
from .semantic import Concept, SemanticIndex

LARGE_DOC_THRESHOLD = 4000
SECTION_CHUNK_CHAR_LIMIT = 1500


def _extract_headings(markdown: str) -> set:
    headings = set()
    for line in markdown.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                headings.add(title.lower())
    return headings


def _sanitize_filename(filename: str) -> str:
    name = (filename or "").strip()
    if "/" in name:
        name = name.split("/")[-1]
    if "\\" in name:
        name = name.split("\\")[-1]
    name = name.replace("..", "")
    if name.startswith("~"):
        name = name[1:]
    name = name.replace("\x00", "")
    name = name.strip(". ")
    if not name:
        name = "generated-doc.md"
    if not name.endswith(".md"):
        name = f"{name}.md"
    safe = re.sub(r'[<>:"|?*]', "_", name)
    return safe


def _split_document_into_chunks(
    content: str, max_chars: int = SECTION_CHUNK_CHAR_LIMIT
) -> List[str]:
    lines = content.split("\n")
    chunks: List[str] = []
    current: List[str] = []
    length = 0

    for line in lines:
        heading_starts_new = line.strip().startswith("#") and current and length >= max_chars
        if heading_starts_new:
            chunks.append("\n".join(current).strip("\n"))
            current = [line]
            length = len(line) + 1
            continue

        current.append(line)
        length += len(line) + 1

        if length >= max_chars:
            chunks.append("\n".join(current).strip("\n"))
            current = []
            length = 0

    if current:
        chunks.append("\n".join(current).strip("\n"))

    return [chunk for chunk in chunks if chunk]


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
        lines = cleaned.splitlines()
        if lines:
            closing_index = None
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip().startswith("```"):
                    closing_index = i
                    break

            if closing_index and closing_index > 0:
                lines = lines[1:closing_index]
                cleaned = "\n".join(lines).strip()
    return cleaned.strip()


def rewrite_document_with_llm(
    doc_path: str,
    original_content: str,
    matches_payload: List[dict],
    llm: LLMClient,
    max_tokens: int = 8000,
    verbose: bool = False,
) -> Tuple[Optional[str], Dict[str, str]]:
    """Intelligently merge references into documentation by processing sections."""

    if not matches_payload:
        return None, {}

    if len(original_content) > LARGE_DOC_THRESHOLD:
        return _rewrite_large_document(
            doc_path,
            original_content,
            matches_payload,
            llm,
            verbose=verbose,
        )

    return _rewrite_sections(
        doc_path,
        original_content,
        matches_payload,
        llm,
        verbose=verbose,
    )


def _rewrite_sections(
    doc_path: str,
    original_content: str,
    matches_payload: List[dict],
    llm: LLMClient,
    verbose: bool = False,
) -> Tuple[Optional[str], Dict[str, str]]:
    from collections import defaultdict

    sections_to_update = defaultdict(list)
    for payload in matches_payload:
        sections_to_update[payload["section"]].append(payload)

    updated_content = original_content

    for section_name, section_matches in sections_to_update.items():
        section_range = find_section_in_markdown(updated_content, section_name)
        if not section_range:
            if verbose:
                print(f"    Warning: Section '{section_name}' not found in document")
            continue

        start_line, end_line = section_range
        lines = updated_content.split("\n")
        section_lines = lines[start_line : end_line + 1]
        section_content = "\n".join(section_lines)

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
            prompt_lines.append(f"- Code: `{match['code_reference']}`")
            prompt_lines.append(f"  Purpose: {match['code_summary']}")
            prompt_lines.append(f"  Why it relates: {match['reasoning']}")
            prompt_lines.append("")

        prompt_lines.extend(
            [
                "Instructions:",
                "1. Keep the section structure and headings intact",
                "2. Integrate references naturally into sentences",
                "3. Use phrases like 'implemented in', 'as seen in', 'handled by', etc.",
                "4. Don't create bullet lists of references",
                "5. Return ONLY the updated section content",
                "",
                "Return the updated section with references woven into the text:",
            ]
        )

        prompt = "\n".join(prompt_lines)
        section_tokens = max(2000, len(section_content) // 2)

        if verbose:
            print(f"    Updating section '{section_name}' ({len(section_content)} chars)")

        try:
            response = llm.generate_text(prompt, max_tokens=section_tokens)
        except Exception as exc:
            if verbose:
                print(f"      Failed to update section: {exc}")
            continue

        if not response:
            continue

        cleaned = _clean_markdown_output(response)
        if not cleaned:
            continue

        if not _is_rewrite_safe(section_content, cleaned):
            if verbose:
                print("      Section rewrite failed safety checks; skipping")
            continue

        missing_refs = [
            match["code_reference"]
            for match in section_matches
            if match["code_reference"] not in cleaned
        ]
        if missing_refs:
            if verbose:
                print(
                    "      Section rewrite missing references: "
                    + ", ".join(missing_refs)
                    + "; skipping"
                )
            continue

        new_lines = lines[:start_line] + cleaned.split("\n") + lines[end_line + 1 :]
        updated_content = "\n".join(new_lines)

        if verbose:
            print("      Successfully updated section")

    if updated_content == original_content:
        if verbose:
            print("    No sections could be updated")
        return None, {}

    return updated_content, {}


def _rewrite_large_document(
    doc_path: str,
    original_content: str,
    matches_payload: List[dict],
    llm: LLMClient,
    verbose: bool = False,
) -> Tuple[Optional[str], Dict[str, str]]:
    chunks = _split_document_into_chunks(original_content)
    if not chunks:
        return None, {}

    total_chunks = len(chunks)
    doc_outputs = [(doc_path, [])]
    additional_docs: Dict[str, str] = {}
    current_doc_chunks: List[str] = doc_outputs[0][1]
    previous_summary = ""
    anything_changed = False

    for index, chunk_text in enumerate(chunks):
        chunk_matches = [m for m in matches_payload if m["section"].lower() in chunk_text.lower()]

        next_preview = chunks[index + 1][:300] if index + 1 < total_chunks else ""

        response = _rewrite_chunk_with_llm(
            doc_path=doc_path,
            chunk_text=chunk_text,
            chunk_index=index,
            total_chunks=total_chunks,
            matches=chunk_matches,
            previous_summary=previous_summary,
            next_preview=next_preview,
            llm=llm,
            verbose=verbose,
        )

        if not response:
            if verbose:
                print("    Chunk rewrite failed; aborting chunked rewrite")
            return None, {}

        updated_chunk = response["updated_chunk"].strip()
        if not _is_rewrite_safe(chunk_text, updated_chunk):
            if verbose:
                print("    Chunk rewrite failed safety check; aborting")
            return None, {}

        missing_refs = [
            item["code_reference"]
            for item in chunk_matches
            if item["code_reference"] not in updated_chunk
        ]
        if missing_refs:
            if verbose:
                print(
                    "    Chunk rewrite missing references: "
                    + ", ".join(missing_refs)
                    + "; aborting chunked rewrite"
                )
            return None, {}

        current_doc_chunks.append(updated_chunk)
        previous_summary = response.get("summary_for_next", "")
        anything_changed = True

        if response.get("split_after") and index < total_chunks - 1:
            new_title = response.get("new_document_title", "").strip() or "Additional Documentation"
            new_intro = response.get("new_document_intro", "").strip()
            sanitized = _sanitize_filename(new_title)
            new_path = f"docs/{sanitized}"

            if verbose:
                print(f"    Creating new document: {new_path}")

            doc_outputs[-1] = (doc_outputs[-1][0], current_doc_chunks)

            intro_chunk = f"# {new_title}\n\n{new_intro}" if new_intro else f"# {new_title}"
            new_doc_chunks: List[str] = [intro_chunk]
            doc_outputs.append((new_path, new_doc_chunks))
            current_doc_chunks = new_doc_chunks

    doc_outputs[-1] = (doc_outputs[-1][0], current_doc_chunks)

    if not anything_changed:
        return None, {}

    primary_content = "\n\n".join(doc_outputs[0][1])

    for path, chunks_out in doc_outputs[1:]:
        additional_docs[path] = "\n\n".join(chunks_out)

    return primary_content, additional_docs


def _rewrite_chunk_with_llm(
    doc_path: str,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    matches: List[dict],
    previous_summary: str,
    next_preview: str,
    llm: LLMClient,
    verbose: bool = False,
) -> Optional[Dict[str, Any]]:
    prompt_lines = [
        f"You are editing chunk {chunk_index + 1} of {total_chunks} for {doc_path}.",
        "Integrate the provided code references naturally into the text.",
        "If this chunk ends a logical section, you may propose starting a new document.",
        "Always return structured JSON as specified.",
        "",
        f"Previous chunk summary: {previous_summary or 'None'}",
        "",
        "Current chunk:",
        "```markdown",
        chunk_text,
        "```",
    ]

    if next_preview:
        prompt_lines.extend(
            [
                "",
                "Upcoming chunk preview:",
                "```markdown",
                next_preview,
                "```",
            ]
        )

    prompt_lines.append("")
    prompt_lines.append("Relevant code references:")
    if matches:
        for m in matches:
            prompt_lines.append(f"- Code: `{m['code_reference']}`")
            prompt_lines.append(f"  Summary: {m['code_summary']}")
            prompt_lines.append(f"  Reason: {m['reasoning']}")
    else:
        prompt_lines.append("- (no direct references; ensure continuity with surrounding text)")

    prompt_lines.extend(
        [
            "",
            "Respond with JSON in the form:",
            "{",
            '  "updated_chunk": "...",',
            '  "summary_for_next": "...",',
            '  "split_after": false,',
            '  "new_document_title": "",',
            '  "new_document_intro": ""',
            "}",
            "",
            "If you set split_after to true, provide a meaningful title and intro for the new document.",
        ]
    )

    prompt = "\n".join(prompt_lines)
    approx_tokens = max(2000, len(chunk_text) // 2)

    try:
        response = llm._request_json(
            prompt,
            max_tokens=approx_tokens,
            log_context=f"Chunk rewrite {chunk_index + 1}/{total_chunks}",
            validator=_validate_chunk_response,
            schema_retry_builder=_build_chunk_retry_prompt,
        )
    except Exception as exc:
        if verbose:
            print(f"    Chunk rewrite error: {exc}")
        return None

    return response


def _validate_chunk_response(data: any) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    issues: List[Dict[str, str]] = []
    if not isinstance(data, dict):
        return {}, [{"index": 0, "error": "response is not an object"}]

    updated_chunk = data.get("updated_chunk")
    if not isinstance(updated_chunk, str) or not updated_chunk.strip():
        issues.append({"index": 0, "error": "missing or empty updated_chunk"})

    normalized = {
        "updated_chunk": updated_chunk or "",
        "summary_for_next": data.get("summary_for_next", ""),
        "split_after": bool(data.get("split_after")),
        "new_document_title": (data.get("new_document_title") or "").strip(),
        "new_document_intro": (data.get("new_document_intro") or "").strip(),
    }

    if normalized["split_after"] and not normalized["new_document_title"]:
        issues.append({"index": 0, "error": "split_after true but new_document_title missing"})

    return normalized, issues


def _build_chunk_retry_prompt(
    parsed: Dict[str, Any], issues: List[Dict[str, str]], original_raw: str
) -> str:
    issues_text = "\n".join(f"- {issue['error']}" for issue in issues)
    return f"""Your JSON response for the chunk rewrite was invalid.

Issues:
{issues_text}

Please respond with valid JSON in the format:
{{
  "updated_chunk": "...",
  "summary_for_next": "...",
  "split_after": false,
  "new_document_title": "",
  "new_document_intro": ""
}}

Return only the JSON object.
"""


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

    rewritten, additional_docs = rewrite_document_with_llm(
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
                    print(f"  [DRY RUN] Would rewrite {doc_path} with {len(payloads)} reference(s)")
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(rewritten)
                if verbose:
                    print(f"  Rewrote {doc_path} with {len(payloads)} reference(s)")

            changes.append(f"Rewrote document with {len(payloads)} reference(s) integrated")
        else:
            if verbose:
                print(f"  LLM rewrite produced no changes for {doc_path}")

        if additional_docs:
            written = _write_additional_docs(additional_docs, root_dir, dry_run, verbose)
            for path in written:
                changes.append(f"Created supplemental documentation: {path}")
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
                changes.append(f"Added reference in '{item['section']}': {item['code_reference']}")

    return changes


def _write_additional_docs(
    docs: Dict[str, str],
    root_dir: str,
    dry_run: bool,
    verbose: bool,
) -> List[str]:
    written: List[str] = []
    root_path = Path(root_dir).resolve()
    docs_dir = root_path / "docs"

    for relative_path, content in docs.items():
        if not relative_path.startswith("docs/"):
            relative_path = f"docs/{relative_path}"

        full_path = (root_path / relative_path).resolve()

        if not str(full_path).startswith(str(docs_dir)):
            if verbose:
                print(f"    Skipping supplemental doc outside docs/: {relative_path}")
            continue

        if dry_run:
            if verbose:
                print(f"    [DRY RUN] Would create {relative_path}")
            written.append(relative_path)
            continue

        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        if verbose:
            print(f"    Created supplemental doc {relative_path}")
        written.append(relative_path)

    return written


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
