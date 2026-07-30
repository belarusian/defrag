"""
Semantic analyzer - orchestrates concept extraction and matching.

Uses LLM to understand code and documentation conceptually,
then matches them and validates with physical links.
"""

import ast
import os
import re
from typing import Dict, List, Optional

from .llm import LLMClient
from .refiner import IterativeRefiner
from .semantic import (
    Concept,
    ConceptMatch,
    SemanticIndex,
    compute_file_hash,
    extract_markdown_sections,
    make_concept_id,
)


class SemanticAnalyzer:
    """
    Analyzes codebase and documentation semantically.

    Workflow:
    1. Extract concepts from docs (LLM-based)
    2. Extract concepts from code (LLM-based)
    3. Match concepts (LLM-based)
    4. Validate with physical links (grounding heuristic)
    5. Generate confidence scores
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        root_dir: str = ".",
        resume_from: Optional[str] = None,
    ):
        """
        Initialize analyzer.

        Args:
            llm_client: LLM client for semantic analysis
            root_dir: Root directory of codebase
            resume_from: Path to existing index to resume from (optional)

        Raises:
            ValueError: If resume_from path exists but index is malformed
        """
        self.llm = llm_client or LLMClient(root_dir=root_dir)
        self.root_dir = root_dir

        # Resume from existing index if specified
        if resume_from and os.path.exists(resume_from):
            try:
                self.index = SemanticIndex.load(resume_from)
                print(f"Resumed from existing index: {resume_from}")
                print(
                    f"  Existing: {len(self.index.concepts)} concepts, "
                    f"{len(self.index.matches)} matches"
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to load index from {resume_from}: {e}\n"
                    "Index may be corrupted. Remove it or fix manually before resuming."
                ) from e
        else:
            self.index = SemanticIndex()

    def analyze_documentation(self, doc_paths: List[str], verbose: bool = False) -> None:
        """
        Analyze documentation files and extract concepts.

        When resuming, skips files that already have concepts in the index.

        Args:
            doc_paths: List of markdown file paths
            verbose: Print progress
        """
        for doc_path in doc_paths:
            # Compute current file hash
            current_hash = compute_file_hash(doc_path, self.root_dir)
            stored_hash = self.index.get_file_hash(doc_path)

            # Check if this file already has concepts (skip if resuming)
            existing_concepts = [
                c
                for c in self.index.concepts.values()
                if c.source_type == "doc" and c.source == doc_path
            ]

            # If file exists and hasn't changed, skip
            if existing_concepts and current_hash and current_hash == stored_hash:
                if verbose:
                    print(f"Skipping unchanged doc: {doc_path} ({len(existing_concepts)} concepts)")
                continue

            # If file changed, remove old concepts before reprocessing
            if existing_concepts and current_hash and current_hash != stored_hash:
                if verbose:
                    print(f"File changed, reprocessing: {doc_path}")
                self.index.remove_concepts_for_file(doc_path, "doc")

            if verbose:
                print(f"Analyzing doc: {doc_path}")

            sections = extract_markdown_sections(doc_path, self.root_dir)

            for section_name, content, line_start, line_end in sections:
                if not content.strip():
                    continue

                try:
                    concept_data = self.llm.extract_doc_concept(section_name, content)
                except ValueError as exc:
                    if verbose:
                        print(f"  Warning: Failed to extract concept for '{section_name}': {exc}")
                    continue

                concept = Concept(
                    id=make_concept_id(doc_path, "doc", section_name),
                    source=doc_path,
                    source_type="doc",
                    location=section_name,
                    description=concept_data["description"],
                    keywords=concept_data["keywords"],
                    line_range=(line_start, line_end),
                    raw_content=content[:500],  # Truncate for storage
                )

                self.index.add_concept(concept)

                if verbose:
                    print(f"  - {section_name}: {concept.description[:60]}...")

            # Update file hash after successful processing
            if current_hash:
                self.index.update_file_hash(doc_path, current_hash)

    def analyze_python_file(self, file_path: str, verbose: bool = False) -> None:
        """
        Analyze Python file and extract concepts.

        When resuming, skips files that already have concepts in the index.

        Args:
            file_path: Path to Python file
            verbose: Print progress
        """
        # Compute current file hash
        current_hash = compute_file_hash(file_path, self.root_dir)
        stored_hash = self.index.get_file_hash(file_path)

        # Check if this file already has concepts (skip if resuming)
        existing_concepts = [
            c
            for c in self.index.concepts.values()
            if c.source_type == "code" and c.source == file_path
        ]

        # If file exists and hasn't changed, skip
        if existing_concepts and current_hash and current_hash == stored_hash:
            if verbose:
                print(f"  Skipping unchanged: {file_path} ({len(existing_concepts)} concepts)")
            return

        # If file changed, remove old concepts before reprocessing
        if existing_concepts and current_hash and current_hash != stored_hash:
            if verbose:
                print(f"  File changed, reprocessing: {file_path}")
            self.index.remove_concepts_for_file(file_path, "code")

        full_path = os.path.join(self.root_dir, file_path)

        if not os.path.exists(full_path):
            return

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()
                tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            if verbose:
                print(f"  Warning: Could not parse {file_path}")
            return

        # Extract functions and classes
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                location = node.name
                line_start = node.lineno
                line_end = node.end_lineno or line_start

                # Get code snippet
                lines = source.split("\n")
                snippet = "\n".join(lines[line_start - 1 : min(line_end, line_start + 50)])

                try:
                    concept_data = self.llm.extract_code_concept(file_path, location, snippet)
                except ValueError as exc:
                    if verbose:
                        print(
                            f"  Warning: Failed to extract concept for {file_path}:{location}: {exc}"
                        )
                    continue

                concept = Concept(
                    id=make_concept_id(file_path, "code", location),
                    source=file_path,
                    source_type="code",
                    location=location,
                    description=concept_data["description"],
                    keywords=concept_data["keywords"],
                    line_range=(line_start, line_end),
                    raw_content=snippet[:500],
                )

                self.index.add_concept(concept)

                if verbose:
                    print(f"  - {location}: {concept.description[:60]}...")

        # Update file hash after successful processing
        if current_hash:
            self.index.update_file_hash(file_path, current_hash)

    def analyze_code_files(self, code_paths: List[str], verbose: bool = False) -> None:
        """
        Analyze code files and extract concepts.

        Args:
            code_paths: List of code file paths
            verbose: Print progress
        """
        for code_path in code_paths:
            if verbose:
                print(f"Analyzing code: {code_path}")

            if code_path.endswith(".py"):
                self.analyze_python_file(code_path, verbose)
            # Add support for other languages here (TypeScript, etc.)

    def match_all_concepts(self, verbose: bool = False, max_iterations: int = 1) -> None:
        """
        Match code concepts to documentation concepts.

        When resuming, skips code concepts that already have matches.

        Args:
            verbose: Print progress
            max_iterations: Max refinement iterations (0 to disable auto-refinement)
        """
        code_concepts = self.index.get_code_concepts()
        doc_concepts = self.index.get_doc_concepts()

        # Build set of already-matched code concept IDs
        already_matched = {m.code_concept_id for m in self.index.matches}

        if verbose:
            skipped_count = len(already_matched)
            new_count = len(code_concepts) - skipped_count
            print(
                f"\nMatching {len(code_concepts)} code concepts to {len(doc_concepts)} doc concepts "
                f"({skipped_count} already matched, {new_count} new)..."
            )

        # Prepare doc concepts for matching
        doc_concept_list = [
            {"description": c.description, "keywords": c.keywords} for c in doc_concepts
        ]

        for code_concept in code_concepts:
            # Skip if already matched (resuming)
            if code_concept.id in already_matched:
                if verbose:
                    print(
                        f"\nSkipping already-matched: {code_concept.source}:{code_concept.location}"
                    )
                continue

            if verbose:
                print(f"\nMatching: {code_concept.source}:{code_concept.location}")

            # Get matches from LLM (with automatic refinement)
            matches = self.llm.match_concepts(
                {
                    "description": code_concept.description,
                    "keywords": code_concept.keywords,
                },
                doc_concept_list,
                max_iterations=max_iterations,
            )

            for match in matches:
                doc_index = match["doc_index"]
                if doc_index < 0 or doc_index >= len(doc_concepts):
                    continue

                doc_concept = doc_concepts[doc_index]

                # Suggest physical link
                suggested_link = None
                if code_concept.line_range:
                    start, end = code_concept.line_range
                    if start == end:
                        suggested_link = f"{code_concept.source}:{start}"
                    else:
                        suggested_link = f"{code_concept.source}:{start}-{end}"

                concept_match = ConceptMatch(
                    code_concept_id=code_concept.id,
                    doc_concept_id=doc_concept.id,
                    confidence=match["confidence"],
                    reasoning=match.get("reasoning", ""),
                    suggested_link=suggested_link,
                    context_needed=match.get("context_needed"),
                    iterations=match.get("iterations", 1),
                )

                self.index.add_match(concept_match)

                if verbose:
                    print(
                        f"  Match: {doc_concept.source}:{doc_concept.location} "
                        f"(confidence: {match['confidence']:.2f})"
                    )

    def validate_with_physical_links(self, verbose: bool = False) -> None:
        """
        Validate semantic matches using physical link validator (grounding heuristic).

        When resuming, skips matches that have already been validated.
        Checks if documentation already has physical links to matched code.
        Updates match confidence based on link validity.
        """
        # Filter to only unvalidated matches
        unvalidated_matches = [m for m in self.index.matches if not m.validated]

        if verbose:
            total = len(self.index.matches)
            already_validated = total - len(unvalidated_matches)
            print(
                f"\nValidating with physical links (grounding heuristic)... "
                f"({already_validated} already validated, {len(unvalidated_matches)} new)"
            )

        for match in unvalidated_matches:
            doc_concept = self.index.get_concept(match.doc_concept_id)
            code_concept = self.index.get_concept(match.code_concept_id)

            if not doc_concept or not code_concept:
                continue

            # Read doc content and check for references to this code file
            doc_path = os.path.join(self.root_dir, doc_concept.source)
            if not os.path.exists(doc_path):
                continue

            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    doc_content = f.read()

                # Check if doc references this code file
                if code_concept.source in doc_content:
                    # Extract specific line references
                    pattern = re.compile(rf"{re.escape(code_concept.source)}:(\d+)(?:-(\d+))?")
                    refs = pattern.findall(doc_content)

                    if refs:
                        # Check if any reference is valid
                        for ref_match in refs:
                            start_line = int(ref_match[0])

                            # Check if reference is in range of code concept
                            code_start, code_end = code_concept.line_range or (0, 0)
                            if code_start <= start_line <= code_end:
                                match.physical_link_valid = True
                                if verbose:
                                    print(
                                        f"  Valid link: {doc_concept.source} -> "
                                        f"{code_concept.source}:{start_line}"
                                    )
                                break
                        else:
                            match.physical_link_valid = False
                    else:
                        # Doc mentions file but no specific line reference
                        match.physical_link_valid = None

            except (OSError, UnicodeDecodeError):
                pass

            # Mark this match as validated (even if validation failed/was inconclusive)
            match.validated = True

    def refine_low_confidence_matches(self, max_iterations: int = 3, verbose: bool = False) -> None:
        """
        Iteratively refine low-confidence matches by expanding context.

        Args:
            max_iterations: Maximum refinement iterations per match
            verbose: Print progress
        """
        if verbose:
            print("\nRefining low-confidence matches...")

        refiner = IterativeRefiner(self.llm, self.root_dir, max_iterations)
        refined_matches = refiner.refine_matches(self.index.matches, self.index, verbose)

        # Replace matches with refined versions
        self.index.matches = refined_matches

        if verbose:
            low_conf_count = sum(1 for m in self.index.matches if m.confidence < 0.7)
            print(f"\nRefinement complete. {low_conf_count} matches still below 0.7 confidence")

    def generate_report(self, min_confidence: float = 0.7) -> Dict:
        """
        Generate semantic analysis report.

        Args:
            min_confidence: Minimum confidence to consider a match valid

        Returns:
            Dictionary with:
            - total_docs: Total documentation files
            - total_code_files: Total code files analyzed
            - total_matches: Total concept matches
            - high_confidence_matches: Matches with confidence >= 0.8
            - validated_matches: Matches with valid physical links
            - unmatched_docs: GC candidates (no high-confidence semantic matches)
        """
        all_doc_files = {c.source for c in self.index.get_doc_concepts()}
        # Only count docs with high-confidence matches as "matched"
        matched_doc_files = {
            self.index.get_concept(m.doc_concept_id).source
            for m in self.index.matches
            if m.confidence >= min_confidence and self.index.get_concept(m.doc_concept_id)
        }
        unmatched_docs = all_doc_files - matched_doc_files

        high_confidence = [m for m in self.index.matches if m.confidence >= 0.8]
        validated = [m for m in self.index.matches if m.physical_link_valid is True]

        return {
            "total_docs": len(all_doc_files),
            "total_code_files": len({c.source for c in self.index.get_code_concepts()}),
            "total_concepts": len(self.index.concepts),
            "doc_concepts": len(self.index.get_doc_concepts()),
            "code_concepts": len(self.index.get_code_concepts()),
            "total_matches": len(self.index.matches),
            "high_confidence_matches": len(high_confidence),
            "validated_matches": len(validated),
            "unmatched_docs": len(unmatched_docs),
            "gc_candidates": sorted(unmatched_docs),
        }

    def find_undocumented_code(self, min_confidence: float = 0.5) -> List[Concept]:
        """
        Find code concepts that have no documentation.

        Identifies code that lacks semantic matches to documentation,
        which could benefit from auto-generated docs.

        Args:
            min_confidence: Minimum confidence to consider a match valid

        Returns:
            List of code Concept objects with no doc matches
        """
        code_concepts = self.index.get_code_concepts()

        # Get code concept IDs that have matches
        matched_code_ids = {
            m.code_concept_id for m in self.index.matches if m.confidence >= min_confidence
        }

        # Return code concepts with no matches
        undocumented = [c for c in code_concepts if c.id not in matched_code_ids]

        return undocumented
