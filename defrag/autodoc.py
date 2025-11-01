"""
Auto-generate conceptual documentation for undocumented code.

Uses LLM to create semantic documentation that explains the "why" and conceptual
purpose of code that has no documentation, with code as leaf nodes.
"""

from pathlib import Path
from typing import List, Dict, Tuple
import logging

from .semantic import Concept, SemanticIndex
from .llm import LLMClient

logger = logging.getLogger(__name__)


class ConceptualDocGenerator:
    """Generate conceptual documentation for undocumented code."""

    def __init__(self, llm_client: LLMClient, root_dir: str = "."):
        self.llm = llm_client
        self.root_dir = Path(root_dir).resolve()

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
        clusters = {}
        for theme, concept_ids in response["clusters"].items():
            clusters[theme] = [id_to_concept[cid] for cid in concept_ids if cid in id_to_concept]

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

        return content, response["filename"]

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
        Write generated documentation to files.

        Args:
            generated_docs: Dict mapping file paths to content
            root_dir: Root directory for writing files
            dry_run: If True, don't actually write files
            verbose: Print what's being written

        Returns:
            List of files written
        """
        written_files = []
        root_path = Path(root_dir)

        for doc_path, content in generated_docs.items():
            full_path = root_path / doc_path

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
    undocumented = [c for c in code_concepts if c.id not in matched_code_ids]

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
