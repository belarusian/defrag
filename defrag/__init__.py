"""
Defrag - Documentation Defragmentation Tool

Keep documentation and code in sync by tracking references,
validating accuracy, and identifying orphaned documentation.
"""

__version__ = "0.1.0"

from .indexer import build_index, load_index, save_index
from .scanner import scan_code_references, scan_documentation
from .schema import DefragIndex, DocEntry
from .validator import validate_code_refs, validate_doc

__all__ = [
    "DocEntry",
    "DefragIndex",
    "scan_documentation",
    "scan_code_references",
    "build_index",
    "load_index",
    "save_index",
    "validate_code_refs",
    "validate_doc",
]
