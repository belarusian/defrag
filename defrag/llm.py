"""
LLM client for semantic analysis.

Abstracts LLM API calls for concept extraction and matching.
"""

import glob
import json
import logging
import os
import subprocess
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with LLM for semantic analysis.

    Supports multiple providers (Anthropic Claude, OpenAI).
    """

    PROVIDER_ENV_VAR = "DEFRAG_LLM_PROVIDER"
    SUPPORTED_PROVIDERS = {"anthropic", "openai"}
    MODEL_ENV_VAR = "DEFRAG_LLM_MODEL"
    DEFAULT_MODELS = {
        "anthropic": "claude-sonnet-4-5-20250929",
        "openai": "gpt-4o",
    }
    PROVIDER_KEY_ENVS = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        root_dir: str = ".",
    ):
        """
        Initialize LLM client.

        Args:
            api_key: Provider API key (or reads from provider-specific env var)
            model: Model to use for analysis (default depends on provider)
            provider: LLM provider (anthropic, openai)
            root_dir: Root directory for context expansion
        """
        provider_name = provider or os.getenv(self.PROVIDER_ENV_VAR, "anthropic")
        self.provider = provider_name.lower()

        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider '{self.provider}'. "
                f"Supported providers: {', '.join(sorted(self.SUPPORTED_PROVIDERS))}"
            )

        key_env = self.PROVIDER_KEY_ENVS[self.provider]
        self.api_key = (api_key or os.getenv(key_env, "")).strip()
        env_model = os.getenv(self.MODEL_ENV_VAR)
        self.model = (
            model
            or (env_model.strip() if env_model else None)
            or self.DEFAULT_MODELS[self.provider]
        )
        self.root_dir = root_dir

        if not self.api_key:
            raise ValueError(
                f"{key_env} not found for provider '{self.provider}'. "
                "Set environment variable or pass api_key parameter."
            )

        self.client, self._provider = self._initialize_provider()

    def _initialize_provider(self):
        """Initialize provider-specific strategy."""
        if self.provider == "anthropic":
            provider = _AnthropicProvider(self.model, self.api_key)
            return provider.client, provider

        if self.provider == "openai":
            provider = _OpenAIProvider(self.model, self.api_key)
            return provider.client, provider

        raise RuntimeError(f"Provider '{self.provider}' not implemented")

    def _send_prompt(self, prompt: str, max_tokens: int) -> str:
        """Send prompt to provider and return raw text response."""
        return self._provider.send_prompt(prompt, max_tokens)

    def generate_text(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate free-form text response from the provider."""
        log_context = "generate_text"
        logger.debug("%s - prompt: %s", log_context, self._truncate(prompt))
        response = self._send_prompt(prompt, max_tokens=max_tokens)
        logger.debug("%s - raw response: %s", log_context, self._truncate(response))
        return (response or "").strip()

    def _request_json(
        self, prompt: str, max_tokens: int, log_context: str, validator, schema_retry_builder
    ):
        """Send prompt, validate structured JSON, and retry once if needed."""
        logger.debug("%s - prompt: %s", log_context, self._truncate(prompt))
        raw = self._send_prompt(prompt, max_tokens=max_tokens)
        logger.debug("%s - raw response: %s", log_context, self._truncate(raw))
        logger.debug("%s - API call succeeded", log_context)

        try:
            parsed = self._parse_json_content(raw)
        except ValueError as parse_error:
            logger.warning(
                "%s - JSON parse failed: %s. Raw=%s",
                log_context,
                parse_error,
                self._truncate(raw),
            )
            retry_prompt = self._build_parse_retry_prompt(parse_error, raw)
            logger.debug("Retrying with parse correction prompt: %s", retry_prompt[:500])
            raw_retry = self._send_prompt(retry_prompt, max_tokens=max_tokens)
            logger.debug("Parse retry raw response: %s", raw_retry[:500])
            parsed = self._parse_json_content(raw_retry)
            raw = raw_retry

        normalized, issues = validator(parsed)

        if issues:
            logger.warning(
                "%s - response missing required fields: %s. Raw=%s",
                log_context,
                issues,
                self._truncate(raw),
            )
            retry_prompt = schema_retry_builder(parsed, issues, raw)
            logger.debug("Retrying with schema correction prompt: %s", retry_prompt[:500])
            raw_retry = self._send_prompt(retry_prompt, max_tokens=max_tokens)
            logger.debug("Schema retry raw response: %s", raw_retry[:500])
            parsed_retry = self._parse_json_content(raw_retry)
            normalized, issues = validator(parsed_retry)
            if issues:
                logger.error(
                    "%s - invalid response after retry: %s. Raw=%s",
                    log_context,
                    "; ".join(f"entry {issue['index']}: {issue['error']}" for issue in issues),
                    self._truncate(raw_retry),
                )
                raise ValueError(
                    "%s - invalid response after retry: %s"
                    % (
                        log_context,
                        "; ".join(f"entry {issue['index']}: {issue['error']}" for issue in issues),
                    )
                )

        return normalized

    @staticmethod
    def _truncate(value: Optional[str], length: int = 400) -> str:
        if not value:
            return ""
        if len(value) <= length:
            return value
        return value[:length] + "...(truncated)"

    def _parse_json_content(self, raw_text: str) -> any:
        """Parse JSON text, allowing for markdown fences."""
        text = (raw_text or "").strip()
        if not text:
            raise ValueError("empty response")

        cleaned = text
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 3:
                cleaned = parts[1]
                if "\n" in cleaned:
                    cleaned = cleaned.split("\n", 1)[1]

        cleaned = cleaned.strip()
        if not cleaned:
            raise ValueError("empty response after stripping code fences")

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON decode error: {exc}") from exc

    @staticmethod
    def _build_parse_retry_prompt(error: Exception, original_raw: str) -> str:
        """Build prompt instructing the model to return valid JSON."""
        return f"""Your previous response could not be parsed as JSON. Here's the error:

Error: {error}

Your original response was:
```
{original_raw[:1000]}
```

Please respond with valid JSON only, with no additional text or markdown."""

    def _parse_json_with_retry(self, raw_text: str, fallback: any):
        """
        Backwards compatibility helper used by tests.

        Attempts to parse JSON and returns fallback if parsing fails.
        """
        try:
            return self._parse_json_content(raw_text)
        except ValueError as exc:
            logger.warning("Failed to parse JSON response: %s", exc)
            return fallback

    def _validate_doc_response(
        self, data: any, section_name: str
    ) -> Tuple[Dict[str, any], List[Dict[str, str]]]:
        issues: List[Dict[str, str]] = []
        if not isinstance(data, dict):
            return {}, [{"index": 0, "error": "response is not an object"}]

        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            issues.append({"index": 0, "error": "description missing or empty"})

        keywords = data.get("keywords")
        normalized_keywords: List[str] = []
        if isinstance(keywords, list):
            for idx, keyword in enumerate(keywords):
                if isinstance(keyword, str) and keyword.strip():
                    normalized_keywords.append(keyword.strip())
                else:
                    issues.append({"index": idx, "error": "keyword missing or empty"})
        else:
            issues.append({"index": 0, "error": "keywords missing or not a list"})

        normalized = {
            "description": description.strip() if isinstance(description, str) else "",
            "keywords": normalized_keywords,
        }

        if not normalized_keywords:
            issues.append({"index": 0, "error": "keywords list empty"})

        return normalized, issues

    @staticmethod
    def _build_doc_retry_prompt(
        section_name: str, issues: List[Dict[str, str]], original_raw: str
    ) -> str:
        """Prompt the model to fix doc concept schema violations."""
        issues_text = (
            "\n".join(f"- {issue['error']}" for issue in issues) or "- (no details captured)"
        )
        return (
            "Your previous JSON response for the documentation section "
            f"'{section_name}' is invalid.\n"
            "Problems detected:\n"
            f"{issues_text}\n\n"
            "Original response:\n"
            "```\n"
            f"{original_raw[:1000]}\n"
            "```\n\n"
            "Please return a JSON object with:\n"
            '- "description": non-empty string summarizing the section\n'
            '- "keywords": list of non-empty strings\n\n'
            "Respond with JSON only."
        )

    def _validate_code_response(
        self, data: any, location: str
    ) -> Tuple[Dict[str, any], List[Dict[str, str]]]:
        issues: List[Dict[str, str]] = []
        if not isinstance(data, dict):
            return {}, [{"index": 0, "error": "response is not an object"}]

        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            issues.append({"index": 0, "error": "description missing or empty"})

        keywords = data.get("keywords")
        normalized_keywords: List[str] = []
        if isinstance(keywords, list):
            for idx, keyword in enumerate(keywords):
                if isinstance(keyword, str) and keyword.strip():
                    normalized_keywords.append(keyword.strip())
                else:
                    issues.append({"index": idx, "error": "keyword missing or empty"})
        else:
            issues.append({"index": 0, "error": "keywords missing or not a list"})

        normalized = {
            "description": description.strip() if isinstance(description, str) else "",
            "keywords": normalized_keywords,
        }

        if not normalized_keywords:
            issues.append({"index": 0, "error": "keywords list empty"})

        return normalized, issues

    @staticmethod
    def _build_code_retry_prompt(
        location: str, issues: List[Dict[str, str]], original_raw: str
    ) -> str:
        """Prompt the model to fix code concept schema violations."""
        issues_text = (
            "\n".join(f"- {issue['error']}" for issue in issues) or "- (no details captured)"
        )
        return (
            "Your previous JSON response for the code element "
            f"'{location}' is invalid.\n"
            "Problems detected:\n"
            f"{issues_text}\n\n"
            "Original response:\n"
            "```\n"
            f"{original_raw[:1000]}\n"
            "```\n\n"
            "Please return a JSON object with:\n"
            '- "description": non-empty string summarizing the code\n'
            '- "keywords": list of non-empty strings\n\n'
            "Respond with JSON only."
        )

    def _validate_match_response(
        self, entries: any, doc_count: int, iteration: int
    ) -> Tuple[List[Dict[str, any]], List[Dict[str, any]]]:
        if not isinstance(entries, list):
            return [], [{"index": 0, "error": "response is not a list"}]

        normalized: List[Dict[str, any]] = []
        issues: List[Dict[str, any]] = []

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                issues.append({"index": idx, "error": "entry is not an object"})
                continue

            errors = []
            doc_index = entry.get("doc_index")
            if not isinstance(doc_index, int):
                errors.append("doc_index missing or not integer")
            elif doc_index < 0 or doc_index >= doc_count:
                errors.append("doc_index out of range")

            confidence = entry.get("confidence")
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                errors.append("confidence missing or not numeric")
                confidence_value = 0.0

            reasoning = entry.get("reasoning")
            if not isinstance(reasoning, str) or not reasoning.strip():
                errors.append("reasoning missing or empty")

            if errors:
                issues.append({"index": idx, "error": ", ".join(errors)})
                continue

            normalized.append(
                {
                    "doc_index": doc_index,
                    "confidence": confidence_value,
                    "reasoning": reasoning.strip(),
                    "context_needed": entry.get("context_needed"),
                    "iterations": entry.get("iterations", iteration + 1),
                }
            )

        return normalized, issues

    @staticmethod
    def _build_match_retry_prompt(
        doc_concepts: List[Dict[str, any]], issues: List[Dict[str, any]], original_raw: str
    ) -> str:
        """Build prompt instructing the model to correct malformed match responses."""
        issues_text = (
            "\n".join(f"- Entry {issue['index']}: {issue['error']}" for issue in issues)
            or "- (no details captured)"
        )
        doc_context = (
            "\n".join(f"{idx}. {doc['description']}" for idx, doc in enumerate(doc_concepts))
            or "No documentation concepts available."
        )
        return (
            "Your previous JSON response listing matches between the code concept and documentation sections is invalid.\n"
            "Problems detected:\n"
            f"{issues_text}\n\n"
            "Original response:\n"
            "```\n"
            f"{original_raw[:1000]}\n"
            "```\n\n"
            "You must respond with a JSON array where each object includes:\n"
            '- "doc_index" (integer index into the documentation list)\n'
            '- "confidence" (numeric score between 0 and 1)\n'
            '- "reasoning" (short explanation of why they match)\n'
            '- "context_needed" (optional object)\n'
            '- "iterations" (optional integer)\n\n'
            "Documentation options for reference:\n"
            f"{doc_context}\n\n"
            "Please respond with the corrected JSON array only."
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

        return self._request_json(
            prompt,
            max_tokens=500,
            log_context=f"Extracting doc concept for section: {section_name}",
            validator=lambda data: self._validate_doc_response(data, section_name),
            schema_retry_builder=lambda parsed, issues, raw: self._build_doc_retry_prompt(
                section_name, issues, raw
            ),
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

        return self._request_json(
            prompt,
            max_tokens=500,
            log_context=f"Extracting code concept for {file_path}:{location}",
            validator=lambda data: self._validate_code_response(data, location),
            schema_retry_builder=lambda parsed, issues, raw: self._build_code_retry_prompt(
                location, issues, raw
            ),
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
        self,
        code_concept: Dict[str, any],
        doc_concepts: List[Dict[str, any]],
        max_iterations: int = 1,
        _iteration: int = 0,
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
            context_summary = "\n".join(
                [
                    f"  - {path}: {len(content)} chars"
                    for path, content in list(code_concept["additional_context"].items())[:5]
                ]
            )
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

        matches = self._request_json(
            prompt,
            max_tokens=1000,
            log_context=f"Matching code concept '{code_concept['description']}'",
            validator=lambda data: self._validate_match_response(
                data, len(doc_concepts), _iteration
            ),
            schema_retry_builder=lambda parsed, issues, original_raw: self._build_match_retry_prompt(
                doc_concepts, issues, original_raw
            ),
        )

        # Check if we should perform iterative refinement
        # Only refine if: we have iterations left, and any match needs refinement
        should_refine = _iteration < max_iterations and any(
            m.get("confidence", 1.0) < 0.7 and m.get("context_needed") for m in matches
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
                    _iteration=_iteration + 1,
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

    def _validate_matches(
        self,
        entries: List[Dict[str, any]],
        doc_count: int,
        iteration: int,
    ) -> Tuple[List[Dict[str, any]], List[Dict[str, any]]]:
        """Validate and normalize raw match entries."""
        normalized: List[Dict[str, any]] = []
        issues: List[Dict[str, any]] = []

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                issues.append({"index": idx, "error": "entry is not an object"})
                continue

            errors = []
            doc_index = entry.get("doc_index")
            if not isinstance(doc_index, int):
                errors.append("doc_index missing or not integer")
            elif doc_index < 0 or doc_index >= doc_count:
                errors.append("doc_index out of range")

            confidence = entry.get("confidence")
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                errors.append("confidence missing or not numeric")
                confidence_value = 0.0

            reasoning = entry.get("reasoning")
            if not isinstance(reasoning, str) or not reasoning.strip():
                errors.append("reasoning missing or empty")

            if errors:
                issues.append({"index": idx, "error": ", ".join(errors)})
                continue

            normalized.append(
                {
                    "doc_index": doc_index,
                    "confidence": confidence_value,
                    "reasoning": reasoning.strip(),
                    "context_needed": entry.get("context_needed"),
                    "iterations": entry.get("iterations", iteration + 1),
                }
            )

        return normalized, issues

    @staticmethod
    def _build_match_retry_prompt(
        doc_concepts: List[Dict[str, any]], issues: List[Dict[str, any]], original_raw: str
    ) -> str:
        """Build prompt instructing the model to correct malformed match responses."""
        issues_text = "\n".join(f"- Entry {issue['index']}: {issue['error']}" for issue in issues)

        doc_context = "\n".join(
            f"{idx}. {doc['description']}" for idx, doc in enumerate(doc_concepts)
        )

        return f"""Your previous JSON response listing matches between the code concept and documentation sections is invalid.
Problems detected:
{issues_text}

Original response:
{original_raw[:1000]}

You must respond with a JSON array where each object includes:
- "doc_index" (integer index into the documentation list)
- "confidence" (numeric score between 0 and 1)
- "reasoning" (short explanation of why they match)
- "context_needed" (optional object)
- "iterations" (optional integer)

Documentation options for reference:
{doc_context}

Please respond with the corrected JSON array only."""

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


class _AnthropicProvider:
    """Provider strategy for Anthropic Claude."""

    def __init__(self, model: str, api_key: str):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            ) from exc

        logger.info(f"Initializing Anthropic client with model: {model}")
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("Anthropic client initialized successfully")

    def send_prompt(self, prompt: str, max_tokens: int) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


class _OpenAIProvider:
    """Provider strategy for OpenAI models."""

    RESPONSES_MODELS_PREFIXES = ("gpt-5", "o4")

    def __init__(self, model: str, api_key: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            ) from exc

        logger.info(f"Initializing OpenAI client with model: {model}")
        self.model = model
        self.client = OpenAI(api_key=api_key)
        self._use_responses_api = model.startswith(self.RESPONSES_MODELS_PREFIXES)
        logger.info("OpenAI client initialized successfully")

    def send_prompt(self, prompt: str, max_tokens: int) -> str:
        if self._use_responses_api:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                max_output_tokens=max_tokens,
            )
            return self._extract_response_text(response)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if isinstance(content, list):
            # Responses can return structured data; join textual parts.
            return "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return content or ""

    @staticmethod
    def _extract_response_text(response) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        text_segments: List[str] = []
        output = getattr(response, "output", []) or []
        for item in output:
            content_list = getattr(item, "content", []) or []
            for chunk in content_list:
                if isinstance(chunk, dict):
                    if chunk.get("type") == "output_text":
                        text_segments.append(chunk.get("text", ""))
                else:
                    if getattr(chunk, "type", None) == "output_text":
                        text_segments.append(getattr(chunk, "text", ""))
        return "".join(text_segments)
