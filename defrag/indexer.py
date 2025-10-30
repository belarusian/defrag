"""
Index builder and persistence.

Manages the documentation index lifecycle: creation, loading, saving.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .schema import DefragIndex, DocEntry, DocStatus
from .scanner import scan_documentation, scan_code_references


DEFAULT_INDEX_PATH = "docs_index.yaml"


def build_index(root_dir: str = ".", index_path: str = DEFAULT_INDEX_PATH) -> DefragIndex:
    """
    Build a fresh documentation index by scanning the repository.

    Args:
        root_dir: Root directory to scan
        index_path: Path to existing index (optional, for preserving status)

    Returns:
        DefragIndex with all discovered documentation
    """
    # Load existing index if present (to preserve status/notes)
    existing_index = None
    if os.path.exists(index_path):
        try:
            existing_index = load_index(index_path)
        except Exception:
            pass

    # Scan for documentation files
    doc_paths = scan_documentation(root_dir)

    # Build index entries
    index = DefragIndex(
        version="1.0",
        last_updated=datetime.now(),
        documents=[],
    )

    for doc_path in doc_paths:
        # Check if doc exists in old index
        existing_entry = existing_index.get_doc(doc_path) if existing_index else None

        if existing_entry:
            # Preserve existing entry but update code refs
            entry = existing_entry
            entry.code_refs = scan_code_references(doc_path, root_dir)
        else:
            # Create new entry
            code_refs = scan_code_references(doc_path, root_dir)
            entry = DocEntry(
                path=doc_path,
                status=DocStatus.UNCHECKED,
                last_validated=None,
                code_refs=code_refs,
                notes="",
                fixes=[],
            )

        index.documents.append(entry)

    return index


def load_index(index_path: str = DEFAULT_INDEX_PATH) -> DefragIndex:
    """
    Load documentation index from YAML file.

    Args:
        index_path: Path to index file

    Returns:
        DefragIndex

    Raises:
        FileNotFoundError: If index file doesn't exist
        ValueError: If index file is invalid
    """
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Index not found: {index_path}")

    with open(index_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty index file: {index_path}")

    return DefragIndex.from_dict(data)


def save_index(index: DefragIndex, index_path: str = DEFAULT_INDEX_PATH) -> None:
    """
    Save documentation index to YAML file.

    Args:
        index: DefragIndex to save
        index_path: Path to index file
    """
    # Update last_updated timestamp
    index.last_updated = datetime.now()

    # Ensure directory exists
    index_dir = os.path.dirname(index_path)
    if index_dir:
        Path(index_dir).mkdir(parents=True, exist_ok=True)

    # Write YAML
    with open(index_path, "w", encoding="utf-8") as f:
        yaml.dump(
            index.to_dict(),
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def update_doc_status(
    index: DefragIndex,
    doc_path: str,
    status: DocStatus,
    notes: str = "",
    fixes: list = None,
) -> None:
    """
    Update status of a document in the index.

    Args:
        index: DefragIndex to update
        doc_path: Path to documentation file
        status: New status
        notes: Optional notes about status
        fixes: Optional list of fixes needed
    """
    doc = index.get_doc(doc_path)
    if not doc:
        raise ValueError(f"Document not in index: {doc_path}")

    doc.status = status
    doc.last_validated = datetime.now()
    doc.notes = notes
    if fixes:
        doc.fixes = fixes


def add_code_ref(index: DefragIndex, doc_path: str, code_ref: str) -> None:
    """
    Add a code reference to a document.

    Args:
        index: DefragIndex to update
        doc_path: Path to documentation file
        code_ref: Code reference to add (format: path/to/file.py:line)
    """
    doc = index.get_doc(doc_path)
    if not doc:
        raise ValueError(f"Document not in index: {doc_path}")

    if code_ref not in doc.code_refs:
        doc.code_refs.append(code_ref)
