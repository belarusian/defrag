"""
LLM client for semantic analysis.

Abstracts LLM API calls for concept extraction and matching.
"""

import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with LLM for semantic analysis.

    Uses Anthropic Claude API (or can be adapted for other providers).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
        """
        Initialize LLM client.

        Args:
            api_key: Anthropic API key (or reads from ANTHROPIC_API_KEY env var)
            model: Model to use for analysis
        """
        self.api_key = (api_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()
        self.model = model

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
        return self._parse_json_with_retry(response, {
            "description": f"Documentation section: {section_name}",
            "keywords": [section_name.lower()],
        })

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
        return self._parse_json_with_retry(response, {
            "description": f"Code at {location}",
            "keywords": [location.lower()],
        })

    def match_concepts(
        self, code_concept: Dict[str, any], doc_concepts: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """
        Match a code concept to relevant documentation concepts.

        Args:
            code_concept: Code concept to match
                - description: str
                - keywords: List[str]
            doc_concepts: List of doc concepts to match against

        Returns:
            List of matches with:
            - doc_index: Index in doc_concepts list
            - confidence: 0.0 to 1.0
            - reasoning: Why they match
        """
        # Build prompt with code concept and doc options
        doc_summaries = "\n".join([f"{i}. {d['description']}" for i, d in enumerate(doc_concepts)])

        prompt = f"""Match this code concept to relevant documentation sections.

Code Concept:
{code_concept['description']}
Keywords: {', '.join(code_concept['keywords'])}

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
- If confidence < 0.7, include context_needed with:
  - file_patterns: Glob patterns for files that would help
  - keywords: Terms to search for
  - reason: What you need to verify
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
        return result if isinstance(result, list) else []

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
