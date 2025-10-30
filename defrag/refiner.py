"""
Iterative refinement for semantic analysis.

Handles expanding context and re-analyzing low-confidence matches.
"""

import glob
import os
import subprocess
from typing import Dict, List, Optional

from .semantic import Concept, ConceptMatch


class ContextExpander:
    """Expands context based on LLM suggestions."""

    def __init__(self, root_dir: str):
        """
        Initialize context expander.

        Args:
            root_dir: Root directory of codebase
        """
        self.root_dir = root_dir

    def expand_context(self, context_needed: dict) -> Dict[str, str]:
        """
        Expand context based on LLM request.

        Args:
            context_needed: Dictionary with:
                - file_patterns: List of glob patterns
                - keywords: List of search terms
                - reason: Why this context is needed

        Returns:
            Dictionary mapping file paths to relevant code snippets
        """
        expanded = {}

        # Search by file patterns
        if "file_patterns" in context_needed:
            for pattern in context_needed["file_patterns"]:
                full_pattern = os.path.join(self.root_dir, pattern)
                for file_path in glob.glob(full_pattern, recursive=True):
                    rel_path = os.path.relpath(file_path, self.root_dir)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            expanded[rel_path] = f.read()
                    except Exception:
                        continue

        # Search by keywords using grep
        if "keywords" in context_needed and context_needed["keywords"]:
            keywords = context_needed["keywords"]
            for keyword in keywords:
                try:
                    # Use ripgrep if available, fall back to grep
                    try:
                        result = subprocess.run(
                            ["rg", "-l", keyword, self.root_dir],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        files = result.stdout.strip().split("\n")
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        result = subprocess.run(
                            ["grep", "-rl", keyword, self.root_dir],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        files = result.stdout.strip().split("\n")

                    # Read matching files
                    for file_path in files:
                        if file_path and os.path.isfile(file_path):
                            rel_path = os.path.relpath(file_path, self.root_dir)
                            if rel_path not in expanded:
                                try:
                                    with open(
                                        file_path, "r", encoding="utf-8", errors="ignore"
                                    ) as f:
                                        expanded[rel_path] = f.read()
                                except Exception:
                                    continue
                except (subprocess.TimeoutExpired, Exception):
                    continue

        return expanded


class IterativeRefiner:
    """Handles iterative refinement of semantic matches."""

    def __init__(self, llm_client, root_dir: str, max_iterations: int = 3):
        """
        Initialize refiner.

        Args:
            llm_client: LLM client for analysis
            root_dir: Root directory of codebase
            max_iterations: Maximum refinement iterations
        """
        self.llm = llm_client
        self.root_dir = root_dir
        self.max_iterations = max_iterations
        self.expander = ContextExpander(root_dir)

    def refine_match(
        self,
        match: ConceptMatch,
        code_concept: Concept,
        doc_concept: Concept,
        verbose: bool = False,
    ) -> ConceptMatch:
        """
        Refine a low-confidence match by expanding context.

        Args:
            match: Initial match to refine
            code_concept: Code concept
            doc_concept: Doc concept
            verbose: Print progress

        Returns:
            Refined match with updated confidence
        """
        current_match = match
        iteration = 1

        while iteration < self.max_iterations:
            # Check if we need more context
            if not current_match.context_needed:
                break

            # Check if confidence is already high enough
            if current_match.confidence >= 0.7:
                break

            if verbose:
                print(
                    f"  Refining match (iteration {iteration + 1}): "
                    f"confidence={current_match.confidence:.2f}"
                )
                print(f"    Context needed: {current_match.context_needed.get('reason', 'Unknown')}")

            # Expand context
            expanded = self.expander.expand_context(current_match.context_needed)

            if not expanded:
                if verbose:
                    print("    No additional context found")
                break

            if verbose:
                print(f"    Found {len(expanded)} additional files")

            # Build enriched context
            enriched_code_concept = {
                "description": code_concept.description,
                "keywords": code_concept.keywords,
                "raw_content": code_concept.raw_content,
                "additional_context": expanded,
            }

            enriched_doc_concept = {
                "description": doc_concept.description,
                "keywords": doc_concept.keywords,
            }

            # Re-analyze with broader context
            matches = self.llm.match_concepts(
                enriched_code_concept, [enriched_doc_concept]
            )

            if not matches:
                break

            # Update match with new results
            new_match_data = matches[0]
            current_match = ConceptMatch(
                code_concept_id=match.code_concept_id,
                doc_concept_id=match.doc_concept_id,
                confidence=new_match_data.get("confidence", current_match.confidence),
                reasoning=new_match_data.get("reasoning", current_match.reasoning),
                physical_link_valid=current_match.physical_link_valid,
                suggested_link=new_match_data.get("suggested_link"),
                context_needed=new_match_data.get("context_needed"),
                iterations=iteration + 1,
            )

            iteration += 1

            if verbose:
                print(f"    New confidence: {current_match.confidence:.2f}")

        return current_match

    def refine_matches(
        self, matches: List[ConceptMatch], index, verbose: bool = False
    ) -> List[ConceptMatch]:
        """
        Refine all low-confidence matches.

        Args:
            matches: List of matches to potentially refine
            index: SemanticIndex with concepts
            verbose: Print progress

        Returns:
            List of refined matches
        """
        refined = []

        for match in matches:
            # Only refine low-confidence matches that need context
            if match.confidence < 0.7 and match.context_needed:
                code_concept = index.get_concept(match.code_concept_id)
                doc_concept = index.get_concept(match.doc_concept_id)

                if code_concept and doc_concept:
                    if verbose:
                        print(
                            f"\nRefining: {doc_concept.source} -> {code_concept.source}"
                        )
                    refined_match = self.refine_match(
                        match, code_concept, doc_concept, verbose
                    )
                    refined.append(refined_match)
                else:
                    refined.append(match)
            else:
                refined.append(match)

        return refined
