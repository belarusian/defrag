"""
Auto-generate conceptual documentation for undocumented code.

Uses LLM to create semantic documentation that explains the "why" and conceptual
purpose of code that has no documentation, with code as leaf nodes.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
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
        self.last_generated_clusters: Dict[str, List[str]] = {}

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
        # Handle unassigned concepts with a better strategy
        unassigned = [
            concept for concept in undocumented_concepts if concept.id not in assigned_ids
        ]

        if unassigned:
            # Always use the model to find connections - zoom out until we find them
            retry_clusters = self._retry_clustering_for_unassigned(unassigned)
            clusters.update(retry_clusters)

        return clusters

    def _retry_clustering_for_unassigned(
        self, unassigned: List[Concept]
    ) -> Dict[str, List[Concept]]:
        """
        Zoom out to progressively broader abstraction levels until concepts connect.

        The key insight: everything shares a parent somewhere up the conceptual tree.
        We just need to find the right level of abstraction.

        Returns:
            Dictionary of theme -> concepts
        """
        if not unassigned:
            return {}

        # Build concept descriptions
        concepts_desc = []
        for concept in unassigned[:30]:  # Include more for better pattern recognition
            concepts_desc.append(
                {
                    "id": concept.id,
                    "source": concept.source,
                    "name": concept.location,
                    "description": concept.description,
                }
            )

        # Try multiple levels of abstraction, zooming out each time
        abstraction_levels = [
            "specific functionality (e.g., 'User Authentication', 'Cache Management', 'Error Recovery')",
            "system capabilities (e.g., 'Data Management', 'Security Features', 'Performance Optimization')",
            "architectural layers (e.g., 'Business Logic', 'Infrastructure', 'External Integrations')",
            "system aspects (e.g., 'Core Functionality', 'Supporting Utilities', 'Developer Tools')",
        ]

        for level_idx, abstraction_level in enumerate(abstraction_levels):
            prompt = f"""Group these code concepts by {abstraction_level}.

IMPORTANT: Every piece of code exists for a reason. Find the conceptual connections.
Look for patterns in what these components DO, not just their names or locations.

Concepts to cluster:
{concepts_desc}

Think about:
- What problem do these components solve?
- What system capability do they enable?
- What architectural role do they play?
- How do they contribute to the overall system?

Group them by their shared purpose at this abstraction level: {abstraction_level}

Respond with JSON:
{{
    "clusters": {{
        "meaningful_theme_name": ["concept_id1", "concept_id2"],
        ...
    }},
    "rationale": "Brief explanation of the grouping logic"
}}
"""

            try:
                response = self.llm._request_json(
                    prompt,
                    max_tokens=2000,
                    log_context=f"Clustering at abstraction level {level_idx + 1}",
                    validator=lambda data: self._validate_cluster_response(data, concepts_desc),
                    schema_retry_builder=lambda parsed, issues, raw: self._build_cluster_retry_prompt(
                        concepts_desc, issues, raw
                    ),
                )

                # Convert IDs back to concepts
                result_clusters = {}
                clustered_ids = set()

                for theme, ids in response.get("clusters", {}).items():
                    if theme and len(ids) > 0:
                        theme_concepts = [c for c in unassigned if c.id in ids]
                        if theme_concepts:
                            result_clusters[theme] = theme_concepts
                            clustered_ids.update(ids)

                # Check if we successfully clustered most concepts
                if len(clustered_ids) >= len(unassigned) * 0.7:  # 70% threshold
                    return result_clusters

                # If not enough were clustered, zoom out to next level
                continue

            except Exception:
                # Try next abstraction level
                continue

        # Final attempt: Force the model to find connections at the highest level
        return self._force_semantic_grouping(unassigned)

    def _force_semantic_grouping(self, concepts: List[Concept]) -> Dict[str, List[Concept]]:
        """
        Force the model to find semantic connections at the highest abstraction level.

        The premise: Everything in a codebase exists for a reason and connects somehow.
        We just need to zoom out far enough to see the forest.
        """
        if not concepts:
            return {}

        concepts_desc = []
        for concept in concepts:
            concepts_desc.append(
                {
                    "id": concept.id,
                    "source": concept.source,
                    "name": concept.location,
                    "description": concept.description,
                }
            )

        prompt = f"""You must group ALL these code concepts by their PURPOSE in the system.

CRITICAL: Every piece of code exists for a reason. At a high enough level, everything connects.
Think about the SYSTEM AS A WHOLE - what role does each component play?

Concepts to group:
{concepts_desc}

Instructions:
1. Consider the entire system's purpose
2. Think about how each component contributes to that purpose
3. Group by the fundamental problems they solve or capabilities they provide
4. DO NOT leave any concept ungrouped
5. DO NOT use "Unassigned" or "Miscellaneous" - find real connections

Examples of good high-level themes:
- "System Initialization and Configuration"
- "Core Business Logic"
- "Data Pipeline and Processing"
- "External System Integration"
- "Developer Experience and Tooling"
- "System Resilience and Recovery"

Remember: At the system level, everything has a purpose. Find it.

Respond with JSON (group ALL concepts):
{{
    "clusters": {{
        "System Purpose Theme": ["concept_id1", "concept_id2", ...],
        "Another System Theme": ["concept_id3", "concept_id4", ...]
    }},
    "rationale": "How these groupings reflect the system's architecture"
}}
"""

        try:
            response = self.llm._request_json(
                prompt,
                max_tokens=3000,
                log_context="Forcing semantic grouping at system level",
                validator=lambda data: self._validate_cluster_response(data, concepts_desc),
                schema_retry_builder=lambda parsed, issues, raw: self._build_cluster_retry_prompt(
                    concepts_desc, issues, raw
                ),
            )

            # Convert IDs back to concepts
            result_clusters = {}
            for theme, ids in response.get("clusters", {}).items():
                if theme and len(ids) > 0:
                    theme_concepts = [c for c in concepts if c.id in ids]
                    if theme_concepts:
                        result_clusters[theme] = theme_concepts

            # If model still didn't group everything, put remainder in a system-level bucket
            grouped_ids = set()
            for concepts_list in result_clusters.values():
                grouped_ids.update(c.id for c in concepts_list)

            ungrouped = [c for c in concepts if c.id not in grouped_ids]
            if ungrouped:
                # One more attempt with just the ungrouped ones
                if len(ungrouped) > 1:
                    result_clusters["System Infrastructure Components"] = ungrouped
                else:
                    # Single concept - add to most relevant existing cluster
                    if result_clusters:
                        first_theme = next(iter(result_clusters))
                        result_clusters[first_theme].append(ungrouped[0])
                    else:
                        result_clusters["System Components"] = ungrouped

            return result_clusters

        except Exception:
            # This should never happen, but if it does, group everything
            # under a single system-level theme
            return {"System Components": concepts}

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

        # Sanitize the theme name to avoid meta-documentation
        sanitized_theme = semantic_theme
        if "UNASSIGNED" in semantic_theme.upper() or semantic_theme.upper() == "CONCEPTS":
            # Derive a better theme name from the actual concepts
            if concepts:
                # Look at the actual functionality
                sources = [c.source for c in concepts[:3]]
                common_module = None
                if sources:
                    # Try to find common module
                    if all("/" in s for s in sources):
                        dirs = [s.rsplit("/", 1)[0] for s in sources]
                        if len(set(dirs)) == 1:
                            common_module = dirs[0].split("/")[-1]
                    if not common_module:
                        common_module = sources[0].replace(".py", "").split("/")[-1]
                    sanitized_theme = f"{common_module.title()} Functionality"
            else:
                sanitized_theme = "Core System Components"

        prompt = f"""Create conceptual documentation for the following code components.

Theme: {sanitized_theme}

Related code implementations:
{chr(10).join(concepts_detail)}

IMPORTANT: Document what these code components ACTUALLY DO, not the abstract concept of "unassigned" or "concepts".
Look at the actual functionality (e.g., validation, processing, caching, etc.) and document THAT.

Generate documentation that:
1. Explains what these specific components DO and their PURPOSE
2. Describes the actual functionality they provide
3. Explains how these components work together
4. References the code implementations as supporting evidence
5. Focuses on the real-world functionality, not meta-concepts

Do NOT:
- Write about "unassigned concepts" or documentation management
- Document individual function signatures
- List parameters and return types
- Create API reference material
- Use the word "unassigned" in your documentation

Instead, create documentation about the ACTUAL functionality these code components provide.

Format as Markdown.

Respond with JSON containing:
- "content": The markdown documentation (about actual functionality)
- "filename": Suggested filename based on actual functionality (e.g., "validation-system.md", "data-processing.md")
- "title": Document title describing the actual functionality
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

        # Use the content as provided by the model
        content = response["content"]

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

        generated_docs: Dict[str, str] = {}
        cluster_map: Dict[str, List[str]] = {}

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
            cluster_map[doc_path] = [c.id for c in concepts if isinstance(c, Concept)]

            if verbose:
                print(f"  → {doc_path}")

        self.last_generated_clusters = cluster_map
        return generated_docs

    def write_generated_docs(
        self,
        generated_docs: Dict[str, str],
        root_dir: str = ".",
        dry_run: bool = False,
        verbose: bool = False,
        tracking_map: Optional[Dict[str, List[str]]] = None,
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

            original_path = doc_path
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
                    if tracking_map is not None and original_path in tracking_map:
                        tracking_map[doc_path] = tracking_map.pop(original_path)
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
            if tracking_map is not None and original_path in tracking_map and doc_path != original_path:
                tracking_map.setdefault(doc_path, tracking_map.pop(original_path))

        return written_files


def generate_conceptual_docs_for_undocumented_code(
    semantic_index: SemanticIndex,
    llm_client: LLMClient,
    root_dir: str = ".",
    min_confidence: float = 0.5,
    dry_run: bool = False,
    verbose: bool = False,
    skip_concept_ids: Optional[Set[str]] = None,
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
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
        Tuple of:
            - Dict of generated documentation (path -> content)
            - Dict mapping doc path to concept IDs included in that doc
    """
    # Find undocumented code
    code_concepts = semantic_index.get_code_concepts()
    matched_code_ids = {
        m.code_concept_id for m in semantic_index.matches if m.confidence >= min_confidence
    }
    undocumented = [
        c for c in code_concepts if isinstance(c, Concept) and c.id not in matched_code_ids
    ]

    if skip_concept_ids:
        undocumented = [c for c in undocumented if c.id not in skip_concept_ids]

    if not undocumented:
        if verbose:
            print("No undocumented code found!")
        return {}, {}

    if verbose:
        print(f"Found {len(undocumented)} undocumented code concepts")

    # Generate conceptual documentation
    generator = ConceptualDocGenerator(llm_client, root_dir)
    generated_docs = generator.generate_docs_for_undocumented(undocumented, verbose=verbose)

    # Write to files
    if generated_docs:
        generator.write_generated_docs(
            generated_docs,
            root_dir,
            dry_run,
            verbose,
            tracking_map=generator.last_generated_clusters,
        )

    concept_map = dict(generator.last_generated_clusters)
    return generated_docs, concept_map
