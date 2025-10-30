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
    extract_markdown_sections,
    make_concept_id,
)
from .validator import validate_code_ref


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

    def __init__(self, llm_client: Optional[LLMClient] = None, root_dir: str = "."):
        """
        Initialize analyzer.

        Args:
            llm_client: LLM client for semantic analysis
            root_dir: Root directory of codebase
        """
        self.llm = llm_client or LLMClient()
        self.root_dir = root_dir
        self.index = SemanticIndex()

    def analyze_documentation(self, doc_paths: List[str], verbose: bool = False) -> None:
        """
        Analyze documentation files and extract concepts.

        Args:
            doc_paths: List of markdown file paths
            verbose: Print progress
        """
        for doc_path in doc_paths:
            if verbose:
                print(f"Analyzing doc: {doc_path}")

            sections = extract_markdown_sections(doc_path, self.root_dir)

            for section_name, content, line_start, line_end in sections:
                if not content.strip():
                    continue

                # Extract concept using LLM
                concept_data = self.llm.extract_doc_concept(section_name, content)

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

    def analyze_python_file(self, file_path: str, verbose: bool = False) -> None:
        """
        Analyze Python file and extract concepts.

        Args:
            file_path: Path to Python file
            verbose: Print progress
        """
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

                # Extract concept using LLM
                concept_data = self.llm.extract_code_concept(file_path, location, snippet)

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

    def match_all_concepts(self, verbose: bool = False) -> None:
        """
        Match code concepts to documentation concepts.

        Args:
            verbose: Print progress
        """
        code_concepts = self.index.get_code_concepts()
        doc_concepts = self.index.get_doc_concepts()

        if verbose:
            print(f"\nMatching {len(code_concepts)} code concepts to {len(doc_concepts)} doc concepts...")

        # Prepare doc concepts for matching
        doc_concept_list = [
            {"description": c.description, "keywords": c.keywords} for c in doc_concepts
        ]

        for code_concept in code_concepts:
            if verbose:
                print(f"\nMatching: {code_concept.source}:{code_concept.location}")

            # Get matches from LLM
            matches = self.llm.match_concepts(
                {
                    "description": code_concept.description,
                    "keywords": code_concept.keywords,
                },
                doc_concept_list,
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
                    reasoning=match["reasoning"],
                    suggested_link=suggested_link,
                    context_needed=match.get("context_needed"),
                    iterations=1,
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

        Checks if documentation already has physical links to matched code.
        Updates match confidence based on link validity.
        """
        if verbose:
            print("\nValidating with physical links (grounding heuristic)...")

        for match in self.index.matches:
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
                    pattern = re.compile(
                        rf"{re.escape(code_concept.source)}:(\d+)(?:-(\d+))?"
                    )
                    refs = pattern.findall(doc_content)

                    if refs:
                        # Check if any reference is valid
                        for ref_match in refs:
                            start_line = int(ref_match[0])
                            end_line = int(ref_match[1]) if ref_match[1] else start_line

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

            except (IOError, UnicodeDecodeError):
                pass

    def refine_low_confidence_matches(
        self, max_iterations: int = 3, verbose: bool = False
    ) -> None:
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

    def generate_report(self) -> Dict:
        """
        Generate semantic analysis report.

        Returns:
            Dictionary with:
            - total_docs: Total documentation files
            - total_code_files: Total code files analyzed
            - total_matches: Total concept matches
            - high_confidence_matches: Matches with confidence >= 0.8
            - validated_matches: Matches with valid physical links
            - unmatched_docs: GC candidates (no semantic matches)
        """
        all_doc_files = {c.source for c in self.index.get_doc_concepts()}
        matched_doc_files = {
            self.index.get_concept(m.doc_concept_id).source
            for m in self.index.matches
            if self.index.get_concept(m.doc_concept_id)
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
