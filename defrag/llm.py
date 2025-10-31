"""
LLM client for semantic analysis.

Abstracts LLM API calls for concept extraction and matching.
"""

import glob
import json
import logging
import os
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with LLM for semantic analysis.

    Uses Anthropic Claude API (or can be adapted for other providers).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929", root_dir: str = "."):
        """
        Initialize LLM client.

        Args:
            api_key: Anthropic API key (or reads from ANTHROPIC_API_KEY env var)
            model: Model to use for analysis
            root_dir: Root directory for context expansion
        """
        self.api_key = (api_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()
        self.model = model
        self.root_dir = root_dir

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Set environment variable or pass api_key parameter."
            )

        try:
            import anthropic

            logger.info(f"Initializing Anthropic client with model: {self.model}")
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Anthropic client initialized successfully")
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

    def extract_doc_concept(self, section_name: str, content: str) -> Dict[str, any]:
        """
        Extract semantic concept from documentation section.

        Args:
            section_name: Name of the section
            content: Section content

        Returns:
            Dictionary with:
            - description: What this section explains
            - keywords: Key terms (list)
        """
        prompt = f"""Analyze this documentation section and extract its semantic meaning.

Section: {section_name}

Content:
{content[:2000]}

Respond with JSON only:
{{
  "description": "One-sentence description of what this section explains",
  "keywords": ["key", "terms", "list"]
}}"""

        try:
            logger.debug(f"Extracting doc concept for section: {section_name}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.debug("Doc concept extraction API call succeeded")
        except Exception as e:
            logger.error(f"Doc concept extraction API call failed: {type(e).__name__}: {e}")
            raise

        # Parse response with self-correction
        return self._parse_json_with_retry(
            response,
            {
                "description": f"Documentation section: {section_name}",
                "keywords": [section_name.lower()],
            },
        )

    def extract_code_concept(
        self, file_path: str, location: str, code_snippet: str
    ) -> Dict[str, any]:
        """
        Extract semantic concept from code.

        Args:
            file_path: Path to source file
            location: Function/class name
            code_snippet: Code to analyze

        Returns:
            Dictionary with:
            - description: What this code does conceptually
            - keywords: Key terms
        """
        prompt = f"""Analyze this code and extract its semantic meaning.

File: {file_path}
Location: {location}

Code:
{code_snippet[:2000]}

Respond with JSON only:
{{
  "description": "One-sentence description of what this code does conceptually",
  "keywords": ["key", "concepts", "list"]
}}"""

        try:
            logger.debug(f"Extracting code concept for {file_path}:{location}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.debug("Code concept extraction API call succeeded")
        except Exception as e:
            logger.error(f"Code concept extraction API call failed: {type(e).__name__}: {e}")
            raise

        # Parse response with self-correction
        return self._parse_json_with_retry(
            response,
            {
                "description": f"Code at {location}",
                "keywords": [location.lower()],
            },
        )

    def _expand_context(self, context_needed: dict, max_files: int = 5) -> Dict[str, str]:
        """
        Expand context based on LLM request.

        Args:
            context_needed: Dictionary with:
                - file_patterns: List of glob patterns
                - keywords: List of search terms
                - reason: Why this context is needed
            max_files: Maximum number of files to expand (prevents runaway expansion)

        Returns:
            Dictionary mapping file paths to relevant code snippets
        """
        expanded = {}

        # Search by file patterns
        if "file_patterns" in context_needed:
            for pattern in context_needed["file_patterns"]:
                if len(expanded) >= max_files:
                    logger.info(f"Reached max_files limit ({max_files}), stopping expansion")
                    break
                full_pattern = os.path.join(self.root_dir, pattern)
                for file_path in glob.glob(full_pattern, recursive=True):
                    if len(expanded) >= max_files:
                        break
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
                if len(expanded) >= max_files:
                    logger.info(f"Reached max_files limit ({max_files}), stopping expansion")
                    break
                try:
                    # Use ripgrep if available, fall back to grep
                    try:
                        result = subprocess.run(
                            ["rg", "-l", keyword, self.root_dir],
                            capture_output=True,
                            text=True,
                            timeout=3,  # Reduced from 5s
                        )
                        files = result.stdout.strip().split("\n")
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        result = subprocess.run(
                            ["grep", "-rl", keyword, self.root_dir],
                            capture_output=True,
                            text=True,
                            timeout=3,  # Reduced from 5s
                        )
                        files = result.stdout.strip().split("\n")

                    # Read matching files
                    for file_path in files:
                        if len(expanded) >= max_files:
                            break
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
                except (subprocess.TimeoutExpired, Exception) as e:
                    logger.warning(f"Context expansion timed out for keyword '{keyword}': {e}")
                    continue

        return expanded

    def match_concepts(
        self, code_concept: Dict[str, any], doc_concepts: List[Dict[str, any]],
        max_iterations: int = 1, _iteration: int = 0
    ) -> List[Dict[str, any]]:
        """
        Match a code concept to relevant documentation concepts.

        Automatically performs iterative refinement for low-confidence matches
        by expanding context based on LLM suggestions.

        Args:
            code_concept: Code concept to match
                - description: str
                - keywords: List[str]
                - additional_context: Optional[Dict[str, str]] - expanded context from previous iteration
            doc_concepts: List of doc concepts to match against
            max_iterations: Maximum refinement iterations (default 3)
            _iteration: Internal iteration counter (do not set manually)

        Returns:
            List of matches with:
            - doc_index: Index in doc_concepts list
            - confidence: 0.0 to 1.0
            - reasoning: Why they match
            - context_needed: Optional dict with file_patterns/keywords for refinement
            - iterations: Number of refinement iterations performed
        """
        # Build prompt with code concept and doc options
        doc_summaries = "\n".join([f"{i}. {d['description']}" for i, d in enumerate(doc_concepts)])

        # Build context section if additional context was provided
        additional_context_section = ""
        if "additional_context" in code_concept and code_concept["additional_context"]:
            context_summary = "\n".join([
                f"  - {path}: {len(content)} chars"
                for path, content in list(code_concept["additional_context"].items())[:5]
            ])
            additional_context_section = f"""

Additional Context (from previous iteration):
{context_summary}

This additional context was requested to help verify the match. Consider this information when determining confidence."""

        prompt = f"""Match this code concept to relevant documentation sections.

This analysis is used to identify orphaned documentation that should be marked for garbage collection.
Documentation with NO matches above 0.7 confidence will be flagged for removal from the codebase.
Be conservative with confidence scores - only use high confidence (>0.7) when you are certain the code
actually implements what the documentation describes.

Code Concept:
{code_concept['description']}
Keywords: {', '.join(code_concept['keywords'])}{additional_context_section}

Documentation Options:
{doc_summaries}

Respond with JSON array only:
[
  {{
    "doc_index": 0,
    "confidence": 0.95,
    "reasoning": "Why they match",
    "context_needed": {{
      "file_patterns": ["**/pattern/*.py"],
      "keywords": ["keyword1", "keyword2"],
      "reason": "Need to see X to verify"
    }}
  }}
]

Rules:
- Only include matches with confidence >= 0.5
- If confidence < 0.7, include context_needed with file patterns/keywords that would help verify the match
- Confidence > 0.7 means "this doc describes this code" (doc stays in codebase)
- Confidence < 0.7 means uncertain/weak connection (doc may be marked for garbage collection)
- Return empty array [] if no good matches
- Do not include any explanation outside the JSON"""

        try:
            logger.debug(f"Matching code concept to {len(doc_concepts)} doc concepts")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.debug("Concept matching API call succeeded")
        except Exception as e:
            logger.error(f"Concept matching failed: {type(e).__name__}: {e}")
            raise

        # Parse response with self-correction
        result = self._parse_json_with_retry(response, fallback=[])
        matches = result if isinstance(result, list) else []

        # Add iteration count to matches
        for match in matches:
            match["iterations"] = _iteration + 1

        # Check if we should perform iterative refinement
        # Only refine if: we have iterations left, and any match needs refinement
        should_refine = (
            _iteration < max_iterations and
            any(
                m.get("confidence", 1.0) < 0.7 and m.get("context_needed")
                for m in matches
            )
        )

        if not should_refine:
            return matches

        # Perform iterative refinement for low-confidence matches
        refined_matches = []
        for match in matches:
            # Only refine low-confidence matches with context_needed
            if match.get("confidence", 1.0) < 0.7 and match.get("context_needed"):
                doc_index = match.get("doc_index")
                if doc_index is None or doc_index < 0 or doc_index >= len(doc_concepts):
                    refined_matches.append(match)
                    continue

                logger.info(
                    f"Refining match (iteration {_iteration + 2}): "
                    f"confidence={match.get('confidence', 0):.2f}, "
                    f"reason={match.get('context_needed', {}).get('reason', 'Unknown')}"
                )

                # Expand context
                expanded = self._expand_context(match["context_needed"])

                if not expanded:
                    logger.info("No additional context found, keeping original match")
                    refined_matches.append(match)
                    continue

                logger.info(f"Found {len(expanded)} additional files for context")

                # Build enriched code concept
                enriched_code_concept = {
                    "description": code_concept["description"],
                    "keywords": code_concept["keywords"],
                    "additional_context": expanded,
                }

                # Re-match with enriched context (single doc concept)
                refined = self.match_concepts(
                    enriched_code_concept,
                    [doc_concepts[doc_index]],
                    max_iterations=max_iterations,
                    _iteration=_iteration + 1
                )

                if refined and len(refined) > 0:
                    # Update doc_index to original value (it will be 0 in refined result)
                    refined[0]["doc_index"] = doc_index
                    refined_matches.append(refined[0])
                else:
                    # Keep original match if refinement didn't return anything
                    refined_matches.append(match)
            else:
                # Keep high-confidence matches as-is
                refined_matches.append(match)

        return refined_matches

    def batch_extract_doc_concepts(self, sections: List[tuple]) -> List[Dict[str, any]]:
        """
        Extract concepts from multiple doc sections (batched for efficiency).

        Args:
            sections: List of (section_name, content) tuples

        Returns:
            List of concept dictionaries
        """
        concepts = []
        for section_name, content in sections:
            concept = self.extract_doc_concept(section_name, content)
            concepts.append(concept)
        return concepts

    def _parse_json_with_retry(self, response, fallback):
        """
        Parse JSON from LLM response with self-correction retry.

        Args:
            response: Anthropic API response object
            fallback: Value to return if parsing fails after retry

        Returns:
            Parsed JSON object or fallback value
        """
        text = response.content[0].text.strip()

        # Simple, deterministic parsing logic
        def parse_json(content: str):
            """Clean parser: strip markdown code blocks and parse JSON."""
            cleaned = content.strip()
            if cleaned.startswith("```"):
                # Extract content between first pair of ``` markers
                parts = cleaned.split("```")
                if len(parts) >= 3:
                    cleaned = parts[1]
                    # Remove language identifier if present
                    if "\n" in cleaned:
                        cleaned = cleaned.split("\n", 1)[1]
            return json.loads(cleaned.strip())

        # First attempt
        try:
            result = parse_json(text)
            logger.debug("JSON parsed successfully on first attempt")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")

            # Ask LLM to fix its own response
            retry_prompt = f"""Your previous response could not be parsed as JSON. Here's the error:

Error: {e}

Here's the parser code that's trying to read your response:
```python
def parse_json(content: str):
    cleaned = content.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1]
            if "\\n" in cleaned:
                cleaned = cleaned.split("\\n", 1)[1]
    return json.loads(cleaned.strip())
```

Your original response was:
```
{text[:500]}
```

Please provide ONLY valid JSON with no additional text, explanations, or markdown formatting."""

            try:
                logger.debug("Requesting LLM to fix JSON formatting")
                retry_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": retry_prompt}],
                )
                retry_text = retry_response.content[0].text.strip()
                result = parse_json(retry_text)
                logger.info("JSON parsed successfully after retry")
                return result
            except Exception as retry_error:
                logger.error(f"Retry also failed: {retry_error}. Using fallback.")
                return fallback
