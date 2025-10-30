"""
Data models for defrag index.

Defines the structure of the documentation index and entry schema.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class DocStatus(Enum):
    """Documentation status after validation."""

    GOOD = "good"  # Accurate, references valid code
    BAD = "bad"  # Outdated, references invalid/changed code
    UNCHECKED = "unchecked"  # Not yet validated


@dataclass
class DocEntry:
    """Single documentation file entry in the index."""

    path: str
    status: DocStatus = DocStatus.UNCHECKED
    last_validated: Optional[datetime] = None
    code_refs: List[str] = field(default_factory=list)
    notes: str = ""
    fixes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "path": self.path,
            "status": self.status.value,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "code_refs": self.code_refs,
            "notes": self.notes,
            "fixes": self.fixes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocEntry":
        """Create DocEntry from dictionary."""
        return cls(
            path=data["path"],
            status=DocStatus(data.get("status", "unchecked")),
            last_validated=(
                datetime.fromisoformat(data["last_validated"])
                if data.get("last_validated")
                else None
            ),
            code_refs=data.get("code_refs", []),
            notes=data.get("notes", ""),
            fixes=data.get("fixes", []),
        )


@dataclass
class DefragIndex:
    """Complete documentation index."""

    version: str = "1.0"
    last_updated: datetime = field(default_factory=datetime.now)
    documents: List[DocEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
            "documents": [doc.to_dict() for doc in self.documents],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DefragIndex":
        """Create DefragIndex from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            last_updated=(
                datetime.fromisoformat(data["last_updated"])
                if data.get("last_updated")
                else datetime.now()
            ),
            documents=[DocEntry.from_dict(doc) for doc in data.get("documents", [])],
        )

    def get_doc(self, path: str) -> Optional[DocEntry]:
        """Find document entry by path."""
        for doc in self.documents:
            if doc.path == path:
                return doc
        return None

    def add_or_update(self, doc: DocEntry) -> None:
        """Add new document or update existing one."""
        existing = self.get_doc(doc.path)
        if existing:
            self.documents.remove(existing)
        self.documents.append(doc)

    def gc_candidates(self) -> List[DocEntry]:
        """Get documents that are GC candidates (unchecked and no code refs)."""
        return [
            doc for doc in self.documents if doc.status == DocStatus.UNCHECKED and not doc.code_refs
        ]

    def bad_docs(self) -> List[DocEntry]:
        """Get documents marked as bad (need updates)."""
        return [doc for doc in self.documents if doc.status == DocStatus.BAD]

    def good_docs(self) -> List[DocEntry]:
        """Get documents marked as good (accurate)."""
        return [doc for doc in self.documents if doc.status == DocStatus.GOOD]
