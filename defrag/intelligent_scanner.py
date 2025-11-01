"""
Intelligent code and documentation scanner using LLM guidance.

Instead of hardcoded patterns, the LLM decides what to scan based on
the actual directory structure and file names.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class IntelligentScanner:
    """Scanner that uses LLM to decide what files to analyze."""

    def __init__(self, llm_client, root_dir: str = "."):
        self.llm = llm_client
        self.root_dir = Path(root_dir).resolve()
        self.visited_dirs: Set[str] = set()
        self.files_to_scan: Dict[str, List[str]] = {
            "code": [],
            "documentation": [],
            "config": [],
            "other": [],
        }

    def scan(self, max_depth: int = 10, verbose: bool = False) -> Dict[str, List[str]]:
        """
        Intelligently scan directory tree using LLM guidance.

        Returns:
            Dictionary with categorized files:
            - 'code': Source code files to analyze
            - 'documentation': Documentation files to analyze
            - 'config': Configuration files (for context)
            - 'other': Other relevant files
        """
        # Start from root
        self._explore_directory(self.root_dir, depth=0, max_depth=max_depth, verbose=verbose)
        return self.files_to_scan

    def _explore_directory(self, dir_path: Path, depth: int, max_depth: int, verbose: bool):
        """Recursively explore directory using LLM guidance."""
        if depth >= max_depth:
            return

        rel_path = dir_path.relative_to(self.root_dir)
        if str(rel_path) in self.visited_dirs:
            return

        self.visited_dirs.add(str(rel_path))

        # Get directory listing
        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            return

        # Prepare directory structure for LLM
        structure = self._prepare_directory_listing(dir_path, entries)

        if verbose:
            print(f"\nExploring: {rel_path}/")

        # Ask LLM what to scan
        decisions = self._ask_llm_what_to_scan(structure, str(rel_path))

        if verbose and decisions.get("reasoning"):
            print(f"  Decision: {decisions['reasoning']}")

        # Process files
        for entry in entries:
            if entry.is_file():
                filename = entry.name
                if filename in decisions.get("scan_files", []):
                    rel_file = str(entry.relative_to(self.root_dir))
                    raw_category = decisions.get("file_categories", {}).get(filename, "other")
                    # Normalize category to lowercase and ensure it's valid
                    category = str(raw_category).lower()
                    if category not in self.files_to_scan:
                        category = "other"  # Default to "other" for unknown categories
                    self.files_to_scan[category].append(rel_file)
                    if verbose:
                        print(f"  + {rel_file} -> {category}")

        # Recursively explore subdirectories
        for entry in entries:
            if entry.is_dir():
                dir_name = entry.name
                if dir_name in decisions.get("explore_subdirs", []):
                    self._explore_directory(entry, depth + 1, max_depth, verbose)

    def _prepare_directory_listing(self, dir_path: Path, entries: List[Path]) -> Dict:
        """Prepare structured directory listing for LLM."""
        files = []
        subdirs = []

        for entry in entries:
            name = entry.name
            if entry.is_file():
                # Include file size for context
                try:
                    size = entry.stat().st_size
                    files.append({"name": name, "size": size})
                except:
                    files.append({"name": name, "size": 0})
            elif entry.is_dir():
                # Count items in subdir (without recursing)
                try:
                    item_count = len(list(entry.iterdir()))
                    subdirs.append({"name": name, "items": item_count})
                except:
                    subdirs.append({"name": name, "items": 0})

        return {
            "path": str(dir_path.relative_to(self.root_dir)),
            "files": files,
            "subdirs": subdirs,
        }

    def _ask_llm_what_to_scan(self, structure: Dict, rel_path: str) -> Dict:
        """Ask LLM to decide what to scan in this directory."""
        prompt = f"""You are analyzing a codebase to understand its structure and documentation.
I need you to decide which files to analyze and which subdirectories to explore further.

Current directory: {rel_path}/
Files in this directory:
{json.dumps(structure['files'], indent=2)}

Subdirectories:
{json.dumps(structure['subdirs'], indent=2)}

Please respond with a JSON object containing:
1. "scan_files": List of filenames to analyze from this directory
2. "explore_subdirs": List of subdirectory names to explore further
3. "file_categories": Object mapping each scan_file to its category: "code", "documentation", "config", or "other"
4. "reasoning": Brief explanation of your decisions

Rules:
- For code files: Include source files (.py, .js, .ts, .java, .go, .rs, .cpp, etc.)
- For documentation: Include .md, .rst, .txt files that seem like docs
- For config: Include important config files (setup.py, package.json, requirements.txt, etc.)
- Skip generated/compiled files (.pyc, .class, .o, etc.)
- Skip hidden files starting with . unless they're important configs
- Explore subdirs that likely contain source code or docs
- Skip subdirs that are clearly dependencies (node_modules, .venv, venv, __pycache__, etc.)
- Skip subdirs that are build artifacts (build, dist, target, out, etc.)
- Be selective but thorough - we want complete coverage of the actual project code

Respond with JSON only."""

        try:
            response = self.llm._request_json(
                prompt,
                max_tokens=1000,
                log_context=f"Scanning directory: {rel_path}",
                validator=lambda data: self._validate_scan_response(data, structure),
                schema_retry_builder=lambda parsed, issues, raw: self._build_scan_retry_prompt(
                    structure, issues, raw
                ),
            )
            return response
        except Exception as e:
            logger.warning(f"LLM failed to decide on {rel_path}: {e}")
            # Fallback to basic heuristics
            return self._fallback_heuristics(structure)

    def _validate_scan_response(self, data: any, structure: Dict) -> Tuple[Dict, List[Dict]]:
        """Validate LLM's scanning decision response."""
        issues = []
        if not isinstance(data, dict):
            return {}, [{"index": 0, "error": "response is not an object"}]

        # Validate scan_files
        scan_files = data.get("scan_files", [])
        if not isinstance(scan_files, list):
            issues.append({"index": 0, "error": "scan_files is not a list"})
            scan_files = []

        # Check files exist
        valid_files = {f["name"] for f in structure["files"]}
        validated_scan_files = []
        for f in scan_files:
            if isinstance(f, str) and f in valid_files:
                validated_scan_files.append(f)

        # Validate explore_subdirs
        explore_subdirs = data.get("explore_subdirs", [])
        if not isinstance(explore_subdirs, list):
            issues.append({"index": 0, "error": "explore_subdirs is not a list"})
            explore_subdirs = []

        # Check subdirs exist
        valid_subdirs = {d["name"] for d in structure["subdirs"]}
        validated_subdirs = []
        for d in explore_subdirs:
            if isinstance(d, str) and d in valid_subdirs:
                validated_subdirs.append(d)

        # Validate file_categories
        file_categories = data.get("file_categories", {})
        if not isinstance(file_categories, dict):
            file_categories = {}

        normalized = {
            "scan_files": validated_scan_files,
            "explore_subdirs": validated_subdirs,
            "file_categories": file_categories,
            "reasoning": data.get("reasoning", ""),
        }

        return normalized, issues

    @staticmethod
    def _build_scan_retry_prompt(structure: Dict, issues: List[Dict], original_raw: str) -> str:
        """Build retry prompt for scan decisions."""
        issues_text = "\n".join(f"- {issue['error']}" for issue in issues)
        return f"""Your scanning decision response was invalid.

Issues found:
{issues_text}

Original response:
{original_raw[:500]}

Directory structure for reference:
Files: {[f['name'] for f in structure['files']]}
Subdirs: {[d['name'] for d in structure['subdirs']]}

Please respond with a valid JSON object containing:
- "scan_files": list of filenames to scan
- "explore_subdirs": list of subdirectory names to explore
- "file_categories": object mapping filenames to categories
- "reasoning": explanation

JSON only."""

    def _fallback_heuristics(self, structure: Dict) -> Dict:
        """Fallback to simple heuristics if LLM fails."""
        scan_files = []
        file_categories = {}

        # Common code extensions
        code_exts = {".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".h", ".rb", ".php"}
        doc_exts = {".md", ".rst", ".txt"}
        config_names = {"setup.py", "package.json", "requirements.txt", "Dockerfile", "Makefile"}

        for file_info in structure["files"]:
            name = file_info["name"]
            ext = Path(name).suffix

            if ext in code_exts:
                scan_files.append(name)
                file_categories[name] = "code"
            elif ext in doc_exts:
                scan_files.append(name)
                file_categories[name] = "documentation"
            elif name in config_names:
                scan_files.append(name)
                file_categories[name] = "config"

        # Explore subdirs that don't look like dependencies
        exclude_dirs = {
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".git",
            "build",
            "dist",
            ".pytest_cache",
            ".tox",
            ".eggs",
        }

        explore_subdirs = []
        for subdir_info in structure["subdirs"]:
            name = subdir_info["name"]
            if name not in exclude_dirs and not name.startswith("."):
                explore_subdirs.append(name)

        return {
            "scan_files": scan_files,
            "explore_subdirs": explore_subdirs,
            "file_categories": file_categories,
            "reasoning": "Fallback heuristics used",
        }


def scan_intelligently(
    llm_client, root_dir: str = ".", verbose: bool = False
) -> Dict[str, List[str]]:
    """
    Convenience function to scan a directory tree intelligently.

    Args:
        llm_client: LLM client instance
        root_dir: Root directory to scan
        verbose: Print progress

    Returns:
        Dictionary with categorized files
    """
    scanner = IntelligentScanner(llm_client, root_dir)
    return scanner.scan(verbose=verbose)
