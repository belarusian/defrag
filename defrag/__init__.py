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
    "DefragIndex",
    "DocEntry",
    "build_index",
    "load_index",
    "save_index",
    "scan_code_references",
    "scan_documentation",
    "validate_code_refs",
    "validate_doc",
]
