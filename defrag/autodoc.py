"""
Auto-generate conceptual documentation for undocumented code.

Uses LLM to create semantic documentation that explains the "why" and conceptual
purpose of code that has no documentation, with code as leaf nodes.
"""

from pathlib import Path
from typing import List, Dict, Tuple
import logging
import re

from .semantic import Concept, SemanticIndex
from .llm import LLMClient

logger = logging.getLogger(__name__)


class ConceptualDocGenerator:
    """Generate conceptual documentation for undocumented code."""

    def __init__(self, llm_client: LLMClient, root_dir: str = "."):
        self.llm = llm_client
        self.root_dir = Path(root_dir).resolve()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to prevent path traversal and other security issues.

        Args:
            filename: The filename to sanitize

        Returns:
            A safe filename with no path components
        """
        # First, get just the base filename (remove all path components)
        # This handles both / and \ path separators
        if "/" in filename:
            filename = filename.split("/")[-1]
        if "\\" in filename:
            filename = filename.split("\\")[-1]

        # Remove any parent directory references that might remain
        filename = filename.replace("..", "")

        # Remove any home directory references
        if filename.startswith("~"):
            filename = filename[1:]

        # Remove any null bytes
        filename = filename.replace("\x00", "")

        # Remove leading/trailing dots and spaces
        filename = filename.strip(". ")

        # Replace any remaining problematic characters with underscore
        filename = re.sub(r'[<>:"|?*]', "_", filename)

        # Ensure it has a .md extension
        if not filename.endswith(".md"):
            filename = filename + ".md"

        # If filename is empty or just .md, use a default
        if filename == ".md" or not filename:
            filename = "generated-doc.md"

        return filename

    def analyze_semantic_clusters(
        self, undocumented_concepts: List[Concept]
    ) -> Dict[str, List[Concept]]:
        """
        Group undocumented concepts into semantic clusters.

        Instead of grouping by file, groups by conceptual purpose.
        Returns dict of semantic_theme -> list of related concepts.
        """
        if not undocumented_concepts:
            return {}

        # Build context for clustering
        concepts_desc = []
        for c in undocumented_concepts:
            concepts_desc.append(
                {
                    "id": c.id,
                    "location": c.location,
                    "description": c.description,
                    "keywords": c.keywords,
                    "source": c.source,
                }
            )

        prompt = f"""Analyze these undocumented code concepts and group them into semantic clusters.

Concepts:
{chr(10).join(f"- {c['location']} ({c['source']}): {c['description']}" for c in concepts_desc)}

Group these concepts by their CONCEPTUAL PURPOSE, not by file location.
For example:
- "Data persistence" might include cache, database, and storage functions
- "Request processing" might include parsing, validation, and handling
- "Configuration management" might include settings, environment, and initialization

Respond with JSON containing:
- "clusters": Object mapping semantic theme to list of concept IDs
- "rationale": Brief explanation of the clustering logic

Example response:
{{
    "clusters": {{
        "Caching Strategy": ["code:cache.py:CacheManager", "code:utils.py:clear_cache"],
        "Error Handling": ["code:errors.py:handle_error", "code:retry.py:retry_logic"]
    }},
    "rationale": "Grouped by functional purpose rather than code structure"
}}
"""

        response = self.llm._request_json(
            prompt,
            max_tokens=2000,
            log_context="Clustering undocumented concepts",
            validator=lambda data: self._validate_cluster_response(data, concepts_desc),
            schema_retry_builder=lambda parsed, issues, raw: self._build_cluster_retry_prompt(
                concepts_desc, issues, raw
            ),
        )

        # Convert IDs back to Concept objects
        id_to_concept = {c.id: c for c in undocumented_concepts}
        clusters: Dict[str, List[Concept]] = {}
        assigned_ids = set()

        for theme, concept_ids in response["clusters"].items():
            matched_concepts = [id_to_concept[cid] for cid in concept_ids if cid in id_to_concept]
            if matched_concepts:
                clusters[theme] = matched_concepts
                assigned_ids.update(c.id for c in matched_concepts)
            else:
                # Surface empty clusters so we can flag the LLM output as needing review
                clusters[f"{theme} (needs-review)"] = []

        # Capture concepts that never appeared in any cluster.
        # Instead of emitting heuristics, gather deterministic context so we can ask the model again.
        unassigned = [concept for concept in undocumented_concepts if concept.id not in assigned_ids]
        if unassigned:
            clusters["UNASSIGNED_CONCEPTS"] = unassigned

            clusters["RECLUSTERING_PROMPT"] = (
                "Some concepts were not grouped by the previous response. "
                "Please analyze the UNASSIGNED_METADATA list and return an updated JSON with "
                "'clusters' mapping semantic themes to concept IDs. "
                "Only include concepts that remain truly unclustered under UNASSIGNED_CONCEPTS."
            )

        return clusters

    def generate_conceptual_doc(
        self, semantic_theme: str, concepts: List[Concept], existing_docs: List[str] = None
    ) -> Tuple[str, str]:
        """
        Generate conceptual documentation for a semantic cluster.

        Args:
            semantic_theme: The conceptual theme (e.g., "Caching Strategy")
            concepts: List of related code concepts
            existing_docs: Optional list of existing doc files for context

        Returns:
            Tuple of (doc_content, suggested_filename)
        """
        # Build concept descriptions
        concepts_detail = []
        for c in concepts:
            detail = f"- `{c.source}:{c.location}`"
            if c.line_range:
                detail += f" (lines {c.line_range[0]}-{c.line_range[1]})"
            detail += f": {c.description}"
            concepts_detail.append(detail)

        prompt = f"""Create conceptual documentation for the following semantic theme.

Theme: {semantic_theme}

Related code implementations:
{chr(10).join(concepts_detail)}

Generate documentation that:
1. Explains the CONCEPTUAL PURPOSE - the "why" behind this functionality
2. Describes the high-level approach or strategy
3. Explains how these components work together conceptually
4. References the code implementations as leaf nodes
5. Focuses on semantic understanding, not API details

Do NOT:
- Document individual function signatures
- List parameters and return types
- Create API reference material

Instead, create semantic documentation that helps readers understand the concept,
with code references showing where the concept is implemented.

Format as Markdown.

Respond with JSON containing:
- "content": The markdown documentation
- "filename": Suggested filename (e.g., "caching-strategy.md")
- "title": Document title
"""

        response = self.llm._request_json(
            prompt,
            max_tokens=3000,
            log_context=f"Generating conceptual doc for {semantic_theme}",
            validator=lambda data: self._validate_doc_response(data),
            schema_retry_builder=lambda parsed, issues, raw: self._build_doc_retry_prompt(
                semantic_theme, concepts, issues, raw
            ),
        )

        # Build final document with proper structure
        content = f"# {response['title']}\n\n{response['content']}"

        # Add implementation references section
        if concepts:
            content += "\n\n## Implementation References\n\n"
            for c in concepts:
                ref = f"- `{c.source}:{c.location}`"
                if c.line_range:
                    ref += f" (lines {c.line_range[0]}-{c.line_range[1]})"
                content += ref + "\n"

        # Sanitize the filename to prevent security issues
        safe_filename = self.sanitize_filename(response["filename"])
        return content, safe_filename

    def _validate_cluster_response(
        self, data: any, concepts_desc: List[Dict]
    ) -> Tuple[Dict, List[Dict]]:
        """Validate clustering response."""
        issues = []
        if not isinstance(data, dict):
            return {}, [{"index": 0, "error": "response is not an object"}]

        if "clusters" not in data or not isinstance(data["clusters"], dict):
            issues.append({"index": 0, "error": "missing or invalid 'clusters' field"})

        # Validate that clusters contain valid concept IDs
        valid_ids = {c["id"] for c in concepts_desc}
        validated_clusters = {}

        for theme, ids in data.get("clusters", {}).items():
            if isinstance(ids, list):
                valid_in_cluster = [cid for cid in ids if cid in valid_ids]
                if valid_in_cluster:
                    validated_clusters[theme] = valid_in_cluster

        normalized = {
            "clusters": validated_clusters,
            "rationale": data.get("rationale", ""),
        }

        return normalized, issues

    def _build_cluster_retry_prompt(
        self, concepts_desc: List[Dict], issues: List[Dict], original_raw: str
    ) -> str:
        """Build retry prompt for clustering."""
        issues_text = "\n".join(f"- {issue['error']}" for issue in issues)
        valid_ids = [c["id"] for c in concepts_desc]

        return f"""Your clustering response was invalid.

Issues found:
{issues_text}

Valid concept IDs:
{', '.join(valid_ids[:10])}...

Please group these concepts by semantic purpose.
Respond with valid JSON containing:
- "clusters": object mapping themes to concept ID lists
- "rationale": explanation

JSON only."""

    def _validate_doc_response(self, data: any) -> Tuple[Dict, List[Dict]]:
        """Validate documentation generation response."""
        issues = []
        if not isinstance(data, dict):
            return {}, [{"index": 0, "error": "response is not an object"}]

        required = ["content", "filename", "title"]
        for field in required:
            if field not in data or not isinstance(data[field], str):
                issues.append({"index": 0, "error": f"missing or invalid '{field}' field"})

        if not data.get("content", "").strip():
            issues.append({"index": 0, "error": "documentation content is empty"})

        normalized = {
            "content": data.get("content", ""),
            "filename": data.get("filename", "concept.md"),
            "title": data.get("title", "Concept Documentation"),
        }

        return normalized, issues

    def _build_doc_retry_prompt(
        self, theme: str, concepts: List[Concept], issues: List[Dict], original_raw: str
    ) -> str:
        """Build retry prompt for doc generation."""
        issues_text = "\n".join(f"- {issue['error']}" for issue in issues)

        return f"""Your documentation generation response was invalid.

Issues found:
{issues_text}

Generate conceptual documentation for theme: {theme}
Code components: {', '.join(c.location for c in concepts[:5])}...

Respond with valid JSON containing:
- "content": markdown documentation
- "filename": suggested filename
- "title": document title

JSON only."""

    def generate_docs_for_undocumented(
        self, undocumented_concepts: List[Concept], verbose: bool = False
    ) -> Dict[str, str]:
        """
        Generate conceptual documentation for undocumented code.

        Args:
            undocumented_concepts: List of code concepts without documentation
            verbose: Print progress

        Returns:
            Dictionary mapping doc file paths to their content
        """
        if not undocumented_concepts:
            return {}

        if verbose:
            print(f"Analyzing {len(undocumented_concepts)} undocumented concepts...")

        # Cluster concepts by semantic purpose
        clusters = self.analyze_semantic_clusters(undocumented_concepts)

        if verbose:
            print(f"Identified {len(clusters)} semantic themes:")
            for theme in clusters:
                print(f"  - {theme} ({len(clusters[theme])} concepts)")

        generated_docs = {}

        # Generate conceptual doc for each cluster
        for theme, concepts in clusters.items():
            # Skip non-concept entries (metadata, prompts, placeholders)
            if not concepts or not all(isinstance(c, Concept) for c in concepts):
                if verbose:
                    print(f"  Skipping cluster '{theme}' (no concrete concepts to document)")
                continue

            if verbose:
                print(f"\nGenerating documentation for: {theme}")

            doc_content, filename = self.generate_conceptual_doc(theme, concepts)
            doc_path = f"docs/{filename}"
            generated_docs[doc_path] = doc_content

            if verbose:
                print(f"  → {doc_path}")

        return generated_docs

    def write_generated_docs(
        self,
        generated_docs: Dict[str, str],
        root_dir: str = ".",
        dry_run: bool = False,
        verbose: bool = False,
    ) -> List[str]:
        """
        Write generated documentation to files with security protections.

        Args:
            generated_docs: Dict mapping file paths to content
            root_dir: Root directory for writing files
            dry_run: If True, don't actually write files
            verbose: Print what's being written

        Returns:
            List of files written

        Raises:
            ValueError: If a file would be written outside docs/ directory
            FileExistsError: If a file already exists (unless in dry_run mode)
        """
        written_files = []
        root_path = Path(root_dir).resolve()
        docs_dir = root_path / "docs"

        for doc_path, content in generated_docs.items():
            # Ensure the path is within docs/ directory
            if not doc_path.startswith("docs/"):
                raise ValueError(
                    f"Security: Attempted to write outside docs/ directory: {doc_path}"
                )

            # Resolve the full path and check it's within our expected directory
            full_path = (root_path / doc_path).resolve()

            # Security check: ensure resolved path is within docs directory
            if not str(full_path).startswith(str(docs_dir)):
                raise ValueError(
                    f"Security: Path traversal detected. Attempted to write to: {full_path}"
                )

            # Check if file already exists
            if full_path.exists():
                if dry_run:
                    if verbose:
                        print(f"[DRY RUN] Would skip existing file: {doc_path}")
                    continue
                else:
                    # Generate an alternative filename
                    base_name = full_path.stem
                    suffix = full_path.suffix
                    counter = 1
                    while full_path.exists():
                        new_name = f"{base_name}-generated-{counter}{suffix}"
                        full_path = full_path.parent / new_name
                        doc_path = f"docs/{new_name}"
                        counter += 1
                    if verbose:
                        print(f"  File exists, using alternative name: {doc_path}")

            if verbose:
                action = "Would write" if dry_run else "Writing"
                print(f"{action} {len(content)} chars to {doc_path}")

            if not dry_run:
                # Ensure directory exists
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the conceptual documentation
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

                if verbose:
                    print(f"  Created {doc_path}")

            written_files.append(doc_path)

        return written_files


def generate_conceptual_docs_for_undocumented_code(
    semantic_index: SemanticIndex,
    llm_client: LLMClient,
    root_dir: str = ".",
    min_confidence: float = 0.5,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, str]:
    """
    Generate conceptual documentation for all undocumented code.

    This creates semantic documentation that explains the "why" and purpose,
    with code as leaf nodes, rather than API reference documentation.

    Args:
        semantic_index: The semantic index with code/doc matches
        llm_client: LLM client for generation
        root_dir: Root directory of the project
        min_confidence: Minimum confidence for considering code documented
        dry_run: Don't write files, just return what would be written
        verbose: Print progress

    Returns:
        Dict of generated documentation (path -> content)
    """
    # Find undocumented code
    code_concepts = semantic_index.get_code_concepts()
    matched_code_ids = {
            m.code_concept_id for m in semantic_index.matches if m.confidence >= min_confidence
        }
    undocumented = [
            c for c in code_concepts if isinstance(c, Concept) and c.id not in matched_code_ids
        ]

    if not undocumented:
        if verbose:
            print("No undocumented code found!")
        return {}

    if verbose:
        print(f"Found {len(undocumented)} undocumented code concepts")

    # Generate conceptual documentation
    generator = ConceptualDocGenerator(llm_client, root_dir)
    generated_docs = generator.generate_docs_for_undocumented(undocumented, verbose=verbose)

    # Write to files
    if generated_docs:
        generator.write_generated_docs(generated_docs, root_dir, dry_run, verbose)

    return generated_docs
