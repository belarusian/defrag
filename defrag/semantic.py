"""
Semantic analysis using LLM-based understanding.

Extracts conceptual meaning from documentation and code,
enabling intelligent matching beyond physical links.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Concept:
    """A semantic concept extracted from docs or code."""

    id: str  # Unique identifier
    source: str  # File path
    source_type: str  # "doc" or "code"
    location: str  # Section name or function/class name
    description: str  # What this concept is about
    keywords: List[str] = field(default_factory=list)  # Key terms
    line_range: Optional[tuple] = None  # (start, end) for code
    raw_content: str = ""  # Original content snippet

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "source_type": self.source_type,
            "location": self.location,
            "description": self.description,
            "keywords": self.keywords,
            "line_range": list(self.line_range) if self.line_range else None,
            "raw_content": self.raw_content,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Concept":
        """Create from dictionary."""
        line_range = tuple(data["line_range"]) if data.get("line_range") else None
        return cls(
            id=data["id"],
            source=data["source"],
            source_type=data["source_type"],
            location=data["location"],
            description=data["description"],
            keywords=data.get("keywords", []),
            line_range=line_range,
            raw_content=data.get("raw_content", ""),
        )


@dataclass
class ConceptMatch:
    """A match between code and documentation concepts."""

    code_concept_id: str
    doc_concept_id: str
    confidence: float  # 0.0 to 1.0
    reasoning: str  # Why they match
    physical_link_valid: Optional[bool] = None  # Grounding heuristic
    suggested_link: Optional[str] = None  # Recommended physical reference
    context_needed: Optional[dict] = None  # What additional context LLM needs
    iterations: int = 1  # Number of analysis iterations
    validated: bool = False  # Whether physical validation has been performed

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "code_concept_id": self.code_concept_id,
            "doc_concept_id": self.doc_concept_id,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "physical_link_valid": self.physical_link_valid,
            "suggested_link": self.suggested_link,
            "context_needed": self.context_needed,
            "iterations": self.iterations,
            "validated": self.validated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConceptMatch":
        """Create from dictionary (backwards compatible)."""
        return cls(
            code_concept_id=data["code_concept_id"],
            doc_concept_id=data["doc_concept_id"],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            physical_link_valid=data.get("physical_link_valid"),
            suggested_link=data.get("suggested_link"),
            context_needed=data.get("context_needed"),
            iterations=data.get("iterations", 1),
            validated=data.get("validated", False),  # Default for old indexes
        )


@dataclass
class SemanticIndex:
    """Complete semantic index of codebase and documentation."""

    concepts: Dict[str, Concept] = field(default_factory=dict)
    matches: List[ConceptMatch] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=lambda: {"version": "1.0"})

    def add_concept(self, concept: Concept) -> None:
        """Add or update a concept."""
        self.concepts[concept.id] = concept

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get concept by ID."""
        return self.concepts.get(concept_id)

    def get_doc_concepts(self) -> List[Concept]:
        """Get all documentation concepts."""
        return [c for c in self.concepts.values() if c.source_type == "doc"]

    def get_code_concepts(self) -> List[Concept]:
        """Get all code concepts."""
        return [c for c in self.concepts.values() if c.source_type == "code"]

    def add_match(self, match: ConceptMatch) -> None:
        """Add a concept match."""
        self.matches.append(match)

    def get_matches_for_doc(self, doc_path: str) -> List[ConceptMatch]:
        """Get all matches for a documentation file."""
        doc_concept_ids = {
            c.id for c in self.concepts.values() if c.source == doc_path and c.source_type == "doc"
        }
        return [m for m in self.matches if m.doc_concept_id in doc_concept_ids]

    def get_matches_for_code(self, code_path: str) -> List[ConceptMatch]:
        """Get all matches for a code file."""
        code_concept_ids = {
            c.id
            for c in self.concepts.values()
            if c.source == code_path and c.source_type == "code"
        }
        return [m for m in self.matches if m.code_concept_id in code_concept_ids]

    def get_unmatched_docs(self) -> List[str]:
        """Get documentation files with no semantic matches (GC candidates)."""
        matched_doc_ids = {m.doc_concept_id for m in self.matches}
        unmatched = set()
        for concept in self.get_doc_concepts():
            if concept.id not in matched_doc_ids:
                unmatched.add(concept.source)
        return sorted(unmatched)

    def get_file_hash(self, filepath: str) -> Optional[str]:
        """Get stored hash for a file."""
        if "file_hashes" not in self.metadata:
            return None
        return self.metadata["file_hashes"].get(filepath)

    def update_file_hash(self, filepath: str, hash_value: str) -> None:
        """Store hash for a file."""
        if "file_hashes" not in self.metadata:
            self.metadata["file_hashes"] = {}
        self.metadata["file_hashes"][filepath] = hash_value

    def remove_concepts_for_file(self, filepath: str, source_type: str) -> None:
        """Remove all concepts for a specific file (used when file changes)."""
        # Remove concepts
        concepts_to_remove = [
            cid
            for cid, c in self.concepts.items()
            if c.source == filepath and c.source_type == source_type
        ]
        for cid in concepts_to_remove:
            del self.concepts[cid]

        # Remove matches involving those concepts
        if source_type == "code":
            self.matches = [m for m in self.matches if m.code_concept_id not in concepts_to_remove]
        else:  # doc
            self.matches = [m for m in self.matches if m.doc_concept_id not in concepts_to_remove]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "version": self.metadata.get("version", "1.0"),
            "metadata": self.metadata,
            "concepts": {cid: c.to_dict() for cid, c in self.concepts.items()},
            "matches": [m.to_dict() for m in self.matches],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SemanticIndex":
        """Create from dictionary (backwards compatible)."""
        index = cls()

        # Load metadata (backwards compatible with old indexes)
        if "metadata" in data:
            index.metadata = data["metadata"]
        elif "version" in data:
            # Old format: version at top level
            index.metadata = {"version": data["version"]}
        else:
            # Very old format: no version
            index.metadata = {"version": "1.0"}

        for cid, cdata in data.get("concepts", {}).items():
            index.concepts[cid] = Concept.from_dict(cdata)
        for mdata in data.get("matches", []):
            index.matches.append(ConceptMatch.from_dict(mdata))
        return index

    def save(self, path: str) -> None:
        """Save semantic index to JSON file atomically."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        # Atomic rename (POSIX guarantees atomicity)
        os.replace(tmp_path, path)

    @classmethod
    def load(cls, path: str) -> "SemanticIndex":
        """Load semantic index from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


def extract_markdown_sections(md_path: str, root_dir: str = ".") -> List[tuple]:
    """
    Extract sections from markdown file.

    Returns:
        List of (section_name, content, line_start, line_end) tuples
    """
    full_path = os.path.join(root_dir, md_path)
    if not os.path.exists(full_path):
        return []

    sections = []
    current_section = None
    current_content = []
    line_start = 0

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Check for markdown headers (# Header)
            if line.startswith("#"):
                # Save previous section
                if current_section:
                    sections.append(
                        (current_section, "".join(current_content).strip(), line_start, i - 1)
                    )

                # Start new section
                current_section = line.strip("#").strip()
                current_content = []
                line_start = i
            else:
                if current_section:
                    current_content.append(line)

        # Save last section
        if current_section:
            sections.append(
                (current_section, "".join(current_content).strip(), line_start, len(lines))
            )

    except (OSError, UnicodeDecodeError):
        pass

    return sections


def make_concept_id(source: str, source_type: str, location: str) -> str:
    """
    Generate unique concept ID.

    Format: {source_type}:{source}:{location}
    """
    # Normalize location (remove special chars, lowercase)
    location_safe = location.replace(" ", "_").replace("/", "_").lower()
    return f"{source_type}:{source}:{location_safe}"


def compute_file_hash(filepath: str, root_dir: str = ".") -> Optional[str]:
    """
    Compute SHA256 hash of file content.

    Args:
        filepath: Relative path to file
        root_dir: Root directory

    Returns:
        Hex digest of file hash, or None if file doesn't exist
    """
    full_path = os.path.join(root_dir, filepath)
    if not os.path.exists(full_path):
        return None

    try:
        with open(full_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None
