"""
Semantic CLI commands for defrag tool.

Commands for LLM-based semantic analysis.
"""

import os
import json
from typing import List

from .analyzer import SemanticAnalyzer
from .autodoc import generate_conceptual_docs_for_undocumented_code
from .fixer import fix_all_documents
from .llm import LLMClient
from .progress import ProgressTracker
from .scanner import scan_documentation
from .semantic import SemanticIndex
from .intelligent_scanner import scan_intelligently

DEFAULT_SEMANTIC_INDEX = "semantic_index.json"


class FixResumeState:
    """Persist progress for semantic-fix so runs can resume after failure."""

    FILENAME = ".defrag_fix_state.json"

    def __init__(self, root_dir: str, enabled: bool):
        self.enabled = enabled
        self.root_dir = root_dir
        self.path = os.path.join(root_dir, self.FILENAME)
        self.docs_completed = set()
        self.code_processed = set()
        self.generated_docs = set()
        self._loaded = False

        if not enabled:
            # Starting fresh; remove any stale state
            if os.path.exists(self.path):
                try:
                    os.remove(self.path)
                except OSError:
                    pass
            return

        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError, json.JSONDecodeError):
                # Corrupt state: treat as empty but keep file for troubleshooting
                return
            self.docs_completed = set(data.get("docs_completed", []))
            self.code_processed = set(data.get("code_processed", []))
            self.generated_docs = set(data.get("generated_docs", []))
            self._loaded = True

    def save(self) -> None:
        if not self.enabled:
            return
        payload = {
            "version": 1,
            "docs_completed": sorted(self.docs_completed),
            "code_processed": sorted(self.code_processed),
            "generated_docs": sorted(self.generated_docs),
        }
        tmp_path = f"{self.path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, self.path)
        except OSError:
            # Best effort – if we can't persist, resume will restart from scratch
            pass

    def is_doc_completed(self, doc_path: str) -> bool:
        return doc_path in self.docs_completed

    def record_doc(self, doc_path: str) -> None:
        if not self.enabled:
            return
        if doc_path not in self.docs_completed:
            self.docs_completed.add(doc_path)
            self.save()

    def should_skip_concept(self, concept_id: str) -> bool:
        return concept_id in self.code_processed

    def record_concepts(self, concept_ids: List[str]) -> None:
        if not self.enabled or not concept_ids:
            return
        changed = False
        for cid in concept_ids:
            if cid not in self.code_processed:
                self.code_processed.add(cid)
                changed = True
        if changed:
            self.save()

    def record_generated_doc(self, doc_path: str) -> None:
        if not self.enabled:
            return
        if doc_path not in self.generated_docs:
            self.generated_docs.add(doc_path)
            self.save()

    def clear(self) -> None:
        if self.enabled and os.path.exists(self.path):
            try:
                os.remove(self.path)
            except OSError:
                pass
        self.docs_completed.clear()
        self.code_processed.clear()
        self.generated_docs.clear()
        self._loaded = False

    @property
    def was_loaded(self) -> bool:
        return self._loaded


def _resolve_index_path(index_arg, root_dir):
    """Resolve semantic index path - look in root_dir if using default."""
    if index_arg is None or index_arg == DEFAULT_SEMANTIC_INDEX:
        return os.path.join(root_dir, DEFAULT_SEMANTIC_INDEX)
    return index_arg


def cmd_semantic_analyze(args):
    """Run full semantic analysis on codebase and documentation."""
    print("=== Semantic Analysis ===")
    print(f"Root: {args.root}")
    provider = args.provider or os.getenv(LLMClient.PROVIDER_ENV_VAR) or "openai"
    provider = provider.lower()
    default_model = LLMClient.DEFAULT_MODELS.get(provider, "unknown")
    print(f"Provider: {provider}")
    if args.model:
        print(f"Model: {args.model}")
    else:
        print(f"Model: {default_model} (default)")
    print()

    # Initialize progress tracker
    progress = ProgressTracker(args.root)
    progress.log(f"Starting semantic analysis on {args.root}")
    progress.log(f"Using provider: {provider}")
    model_label = args.model or default_model
    progress.log(f"Using model: {model_label}")
    print(f"Progress log: {progress.log_path}")
    print()

    # Determine resume path
    output_path = _resolve_index_path(args.output, args.root)
    resume_flag = getattr(args, "resume", False)
    resume_from = output_path if resume_flag else None

    if resume_flag:
        if os.path.exists(output_path):
            print(f"Resume mode: will load existing index from {output_path}")
        else:
            print(f"Resume mode: no existing index found at {output_path}, starting fresh")
            resume_from = None

    # Initialize
    try:
        progress.log("Initializing LLM client...")
        llm = LLMClient(
            model=args.model,
            provider=provider,
            api_key=args.api_key,
            root_dir=args.root,
        )
        analyzer = SemanticAnalyzer(llm, root_dir=args.root, resume_from=resume_from)
        progress.log("LLM client ready")
    except Exception as e:
        progress.log(f"ERROR: {e}")
        print(f"Error initializing LLM client: {e}")
        key_env = LLMClient.PROVIDER_KEY_ENVS.get(provider)
        if key_env:
            print(f"\nHint: Set {key_env} environment variable or pass --api-key")
        else:
            print("\nHint: Check provider configuration and API key settings")
        return 1

    # Step 1: Analyze documentation
    progress.section("Step 1: Documentation Analysis")
    progress.log("Scanning for documentation files...")
    print("[1/4] Analyzing documentation...")
    doc_paths = scan_documentation(args.root)
    progress.log(f"Found {len(doc_paths)} documentation files")
    if args.limit_docs:
        doc_paths = doc_paths[: args.limit_docs]
        progress.log(f"Limiting to {args.limit_docs} docs for testing")
        print(f"  (limiting to {args.limit_docs} docs for testing)")

    progress.log("Extracting concepts from documentation (LLM calls)...")
    progress.update_state("analyzing_docs", total_docs=len(doc_paths))
    analyzer.analyze_documentation(doc_paths, verbose=args.verbose)
    doc_concept_count = len(analyzer.index.get_doc_concepts())
    progress.log(f"Extracted {doc_concept_count} doc concepts")
    print(f"  Extracted {doc_concept_count} doc concepts\n")

    # Step 2: Intelligently discover and analyze code
    progress.section("Step 2: Intelligent Code Discovery")
    progress.log("Using LLM to intelligently discover files...")
    print("[2/4] Discovering code files intelligently...")

    # Use intelligent scanner to discover files
    discovered_files = scan_intelligently(llm, args.root, verbose=args.verbose)

    # Get code files to analyze
    code_paths = discovered_files.get("code", [])

    # Also show what was discovered
    if args.verbose:
        print("\nDiscovered files by category:")
        for category, files in discovered_files.items():
            if files:
                print(f"  {category}: {len(files)} files")
                if len(files) <= 5:
                    for f in files:
                        print(f"    - {f}")
                else:
                    for f in files[:3]:
                        print(f"    - {f}")
                    print(f"    ... and {len(files) - 3} more")

    progress.log(f"Found {len(code_paths)} code files")
    if args.limit_code:
        code_paths = code_paths[: args.limit_code]
        progress.log(f"Limiting to {args.limit_code} files for testing")
        print(f"  (limiting to {args.limit_code} files for testing)")

    progress.log("Extracting concepts from code (LLM calls)...")
    progress.update_state("analyzing_code", total_code_files=len(code_paths))
    analyzer.analyze_code_files(code_paths, verbose=args.verbose)
    code_concept_count = len(analyzer.index.get_code_concepts())
    progress.log(f"Extracted {code_concept_count} code concepts")
    print(f"  Extracted {code_concept_count} code concepts\n")

    # Step 3: Match concepts (with automatic iterative refinement)
    progress.section("Step 3: Concept Matching")
    progress.log(
        f"Matching {code_concept_count} code concepts to {doc_concept_count} doc concepts..."
    )
    progress.log("(automatic iterative refinement enabled for low-confidence matches)")
    progress.update_state("matching_concepts")
    print("[3/4] Matching code to documentation (with automatic refinement)...")
    analyzer.match_all_concepts(verbose=args.verbose)
    match_count = len(analyzer.index.matches)
    high_conf_count = sum(1 for m in analyzer.index.matches if m.confidence >= 0.7)
    refined_count = sum(1 for m in analyzer.index.matches if m.iterations > 1)
    progress.log(
        f"Found {match_count} matches ({high_conf_count} high-confidence, {refined_count} refined)"
    )
    print(f"  Found {match_count} matches ({high_conf_count} high-confidence)\n")
    if refined_count > 0:
        print(f"  {refined_count} matches refined through context expansion\n")

    # Step 4: Validate with physical links
    progress.section("Step 4: Physical Link Validation")
    progress.log("Validating matches with physical link checker...")
    progress.update_state("validating_links")
    print("[4/4] Validating with physical links (grounding heuristic)...")
    analyzer.validate_with_physical_links(verbose=args.verbose)
    progress.log("Physical validation complete")

    # Save index to target repo
    progress.log("Saving semantic index...")
    analyzer.index.save(output_path)
    progress.log(f"Index saved to {output_path}")
    print(f"\nSemantic index saved: {output_path}")

    # Generate report
    report = analyzer.generate_report()
    progress.log(
        f"Analysis complete: {report['total_matches']} matches, {report['high_confidence_matches']} high confidence"
    )
    progress.complete()

    print("\n=== Analysis Complete ===")
    print(f"Documentation: {report['total_docs']} files, {report['doc_concepts']} concepts")
    print(f"Code: {report['total_code_files']} files, {report['code_concepts']} concepts")
    print(
        f"Matches: {report['total_matches']} total, {report['high_confidence_matches']} high confidence"
    )
    print(f"Validated: {report['validated_matches']} matches have valid physical links")
    print(f"GC candidates: {report['unmatched_docs']} docs with no semantic matches")
    print(f"\nProgress log: {progress.log_path}")

    return 0


def cmd_semantic_report(args):
    """Show semantic analysis report."""
    index_path = _resolve_index_path(args.semantic_index, args.root)
    try:
        index = SemanticIndex.load(index_path)
    except FileNotFoundError:
        print(f"Error: Semantic index not found: {index_path}")
        print("Run 'semantic-analyze' first to build the index")
        return 1

    analyzer = SemanticAnalyzer(root_dir=args.root)
    analyzer.index = index

    report = analyzer.generate_report()

    print("\n=== Semantic Analysis Report ===")
    print(f"Documentation: {report['total_docs']} files, {report['doc_concepts']} concepts")
    print(f"Code: {report['total_code_files']} files, {report['code_concepts']} concepts")
    print(f"Total concepts: {report['total_concepts']}")
    print()
    print(f"Semantic matches: {report['total_matches']}")
    print(f"  High confidence (>=0.8): {report['high_confidence_matches']}")
    print(f"  Validated by physical links: {report['validated_matches']}")
    print()
    print(f"GC candidates: {report['unmatched_docs']} docs with no matches")

    if args.show_gc and report["gc_candidates"]:
        print("\nGarbage Collection Candidates:")
        for doc in report["gc_candidates"]:
            print(f"  - {doc}")

    if args.doc:
        # Show matches for specific doc
        print(f"\n=== Matches for {args.doc} ===")
        matches = index.get_matches_for_doc(args.doc)

        if not matches:
            print("No matches found")
        else:
            for match in matches:
                code_concept = index.get_concept(match.code_concept_id)
                doc_concept = index.get_concept(match.doc_concept_id)

                if code_concept and doc_concept:
                    print(f"\n{code_concept.source}:{code_concept.location}")
                    print(f"  Confidence: {match.confidence:.2f}")
                    print(f"  Reasoning: {match.reasoning}")
                    if match.physical_link_valid is not None:
                        status = "VALID" if match.physical_link_valid else "INVALID"
                        print(f"  Physical link: {status}")
                    if match.suggested_link:
                        print(f"  Suggested: {match.suggested_link}")

    return 0


def cmd_semantic_validate(args):
    """
    Validate semantic matches against physical links.

    Shows where semantic understanding differs from physical references.
    """
    index_path = _resolve_index_path(args.semantic_index, args.root)
    try:
        index = SemanticIndex.load(index_path)
    except FileNotFoundError:
        print(f"Error: Semantic index not found: {index_path}")
        return 1

    print("=== Semantic vs Physical Validation ===\n")

    # Analyze discrepancies
    high_confidence_no_link = []
    low_confidence_has_link = []
    mismatches = []

    for match in index.matches:
        code_concept = index.get_concept(match.code_concept_id)
        doc_concept = index.get_concept(match.doc_concept_id)

        if not code_concept or not doc_concept:
            continue

        # High confidence but no valid physical link
        if match.confidence >= 0.8 and not match.physical_link_valid:
            high_confidence_no_link.append((match, code_concept, doc_concept))

        # Low confidence but has valid physical link
        if match.confidence < 0.5 and match.physical_link_valid:
            low_confidence_has_link.append((match, code_concept, doc_concept))

        # Physical link invalid but high semantic confidence
        if match.confidence >= 0.7 and match.physical_link_valid is False:
            mismatches.append((match, code_concept, doc_concept))

    # Report
    print(f"High confidence matches without physical links: {len(high_confidence_no_link)}")
    if high_confidence_no_link and args.verbose:
        print("\nSuggested physical links to add:")
        for match, code, doc in high_confidence_no_link[:10]:
            print(f"\n  {doc.source}:")
            print(f"    Add link: {match.suggested_link}")
            print(f"    Reason: {match.reasoning}")

    print(f"\nLow confidence matches with valid links: {len(low_confidence_has_link)}")
    if low_confidence_has_link and args.verbose:
        print("\nPotential semantic understanding issues:")
        for match, code, doc in low_confidence_has_link[:5]:
            print(f"\n  {doc.source} <-> {code.source}")
            print(f"    Confidence: {match.confidence:.2f}")
            print("    Physical link exists but semantic match weak")

    print(f"\nMismatches (good semantic, broken physical): {len(mismatches)}")
    if mismatches and args.verbose:
        print("\nDocs need updating (code changed):")
        for match, code, doc in mismatches[:10]:
            print(f"\n  {doc.source}:")
            print(f"    Update reference to: {match.suggested_link}")
            print(f"    Reasoning: {match.reasoning}")

    return 0


def cmd_semantic_fix(args):
    """Fix the disconnect between code and documentation."""
    index_path = _resolve_index_path(args.semantic_index, args.root)
    try:
        index = SemanticIndex.load(index_path)
    except FileNotFoundError:
        print(f"Error: Semantic index not found: {index_path}")
        print("Run 'semantic-analyze' first to build the index")
        return 1

    print("=== Fixing Documentation Disconnect ===")
    if not args.apply:
        print("[DRY RUN] Use --apply to write changes\n")

    provider = args.provider or os.getenv(LLMClient.PROVIDER_ENV_VAR) or "openai"
    provider = provider.lower()
    try:
        llm = LLMClient(
            model=args.model,
            provider=provider,
            api_key=args.api_key,
            root_dir=args.root,
        )
    except Exception as e:
        print(f"Error initializing LLM client: {e}")
        key_env = LLMClient.PROVIDER_KEY_ENVS.get(provider)
        if key_env:
            print(f"\nHint: Set {key_env} environment variable or pass --api-key")
        return 1

    resume_flag = getattr(args, "resume", False)
    resume_state = FixResumeState(args.root, True)
    if resume_flag:
        if not resume_state.was_loaded:
            print("Resume mode: no previous fix state found; starting fresh")
    elif resume_state.was_loaded:
        # Discard stale progress when starting a fresh run
        resume_state.clear()

    # Part 1: Fix existing documentation (add missing links)
    print("Step 1: Fixing missing links in existing documentation...")
    processed_docs: List[str] = []

    def _should_skip_doc(doc_path: str) -> bool:
        return resume_flag and resume_state.is_doc_completed(doc_path)

    def _record_doc_progress(doc_path: str, changes: List[str]) -> None:
        resume_state.record_doc(doc_path)
        if doc_path not in processed_docs:
            processed_docs.append(doc_path)

    all_changes = fix_all_documents(
        index,
        llm,
        root_dir=args.root,
        dry_run=not args.apply,
        min_confidence=args.min_confidence,
        verbose=False,
        skip_callback=_should_skip_doc,
        on_doc_processed=_record_doc_progress,
    )

    link_fixes = sum(len(changes) for changes in all_changes.values())
    if link_fixes:
        print(
            f"  {'Fixed' if args.apply else 'Would fix'} {link_fixes} missing links in {len(all_changes)} documents"
        )
    else:
        print("  No missing links to fix")

    if processed_docs:
        analyzer = SemanticAnalyzer(llm, root_dir=args.root)
        analyzer.index = index
        analyzer.validate_with_physical_links(verbose=False)
        index.save(index_path)

    # Part 2: Generate conceptual documentation for undocumented code
    print("\nStep 2: Generating conceptual documentation for undocumented code...")

    # Generate conceptual docs for undocumented code
    skip_concepts = resume_state.code_processed if resume_flag else None
    generated_docs, concept_map = generate_conceptual_docs_for_undocumented_code(
        index,
        llm,
        args.root,
        min_confidence=args.min_confidence,
        dry_run=not args.apply,
        verbose=False,
        skip_concept_ids=skip_concepts,
    )

    if generated_docs:
        doc_count = len(generated_docs)
        action = "Generated" if args.apply else "Would generate"
        print(f"  {action} {doc_count} conceptual documentation file(s):")
        for doc_path in sorted(generated_docs.keys()):
            print(f"    - {doc_path}")
            resume_state.record_generated_doc(doc_path)
            resume_state.record_concepts(concept_map.get(doc_path, []))
        index.save(index_path)
    else:
        print("  All code is already documented")

    # Summary
    print("\n=== Summary ===")
    if link_fixes or generated_docs:
        action = "Fixed" if args.apply else "Would fix"
        print(f"{action} documentation disconnect:")
        if link_fixes:
            print(
                f"  - {'Added' if args.apply else 'Would add'} {link_fixes} missing code references"
            )
        if generated_docs:
            print(
                f"  - {'Created' if args.apply else 'Would create'} {len(generated_docs)} conceptual documentation files"
            )
    else:
        print("Documentation and code are in sync - no fixes needed")

    resume_state.clear()

    return 0


def cmd_semantic_autodoc(args):
    """Generate conceptual documentation for undocumented code."""
    print("=== Semantic Auto-Doc ===")
    print(f"Root: {args.root}")
    provider = args.provider or os.getenv(LLMClient.PROVIDER_ENV_VAR) or "openai"
    provider = provider.lower()
    default_model = LLMClient.DEFAULT_MODELS.get(provider, "unknown")
    print(f"Provider: {provider}")
    if args.model:
        print(f"Model: {args.model}")
    else:
        print(f"Model: {default_model} (default)")
    print()

    index_path = _resolve_index_path(args.semantic_index, args.root)
    if not os.path.exists(index_path):
        print(f"Error: Semantic index not found at {index_path}")
        print("Run 'defrag semantic-analyze' first to generate the index.")
        return 1

    print(f"Loading semantic index from {index_path}...")
    try:
        index = SemanticIndex.load(index_path)
        print(f"Loaded {len(index.concepts)} concepts, {len(index.matches)} matches")
    except Exception as e:
        print(f"Error loading semantic index: {e}")
        return 1

    print("\nInitializing LLM client...")
    llm = LLMClient(
        model=args.model,
        provider=provider,
        api_key=args.api_key,
        root_dir=args.root,
    )
    print("LLM client ready")

    print("\nGenerating conceptual documentation for undocumented code...")
    generated_docs, concept_map = generate_conceptual_docs_for_undocumented_code(
        index,
        llm,
        args.root,
        min_confidence=args.min_confidence,
        dry_run=not args.apply,
        verbose=False,
    )

    if generated_docs:
        doc_count = len(generated_docs)
        action = "Generated" if args.apply else "Would generate"
        print(f"  {action} {doc_count} conceptual documentation file(s):")
        for doc_path in sorted(generated_docs.keys()):
            print(f"    - {doc_path}")
    else:
        print("  All code is already documented")

    print("\n=== Summary ===")
    if generated_docs:
        action = "Created" if args.apply else "Would create"
        print(f"{action} {len(generated_docs)} conceptual documentation files")
    else:
        print("Documentation and code are in sync - no new docs needed")

    return 0


def add_semantic_commands(subparsers, parent_parser):
    """
    Add semantic analysis commands to CLI.

    Args:
        subparsers: Subparsers object from argparse
        parent_parser: Parent parser for common args
    """
    # semantic-analyze command
    parser_analyze = subparsers.add_parser(
        "semantic-analyze",
        help="Run LLM-based semantic analysis",
        parents=[parent_parser],
    )
    parser_analyze.add_argument(
        "--provider",
        choices=sorted(LLMClient.SUPPORTED_PROVIDERS),
        help="LLM provider to use (default: env DEFRAG_LLM_PROVIDER or openai)",
    )
    parser_analyze.add_argument(
        "--model",
        help="LLM model to use (defaults per provider)",
    )
    parser_analyze.add_argument(
        "--api-key",
        help="Override API key for selected provider",
    )
    parser_analyze.add_argument(
        "--output", default=DEFAULT_SEMANTIC_INDEX, help="Output file for semantic index"
    )
    parser_analyze.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing index (skips already-processed files)",
    )
    parser_analyze.add_argument("--limit-docs", type=int, help="Limit number of docs (for testing)")
    parser_analyze.add_argument(
        "--limit-code", type=int, help="Limit number of code files (for testing)"
    )
    parser_analyze.add_argument("--verbose", action="store_true", help="Verbose output")

    # semantic-report command
    parser_report = subparsers.add_parser(
        "semantic-report",
        help="Show semantic analysis report",
        parents=[parent_parser],
    )
    parser_report.add_argument(
        "--semantic-index", default=DEFAULT_SEMANTIC_INDEX, help="Semantic index file"
    )
    parser_report.add_argument("--doc", help="Show matches for specific doc")
    parser_report.add_argument("--show-gc", action="store_true", help="Show GC candidates")

    # semantic-validate command
    parser_validate = subparsers.add_parser(
        "semantic-validate",
        help="Validate semantic matches with physical links",
        parents=[parent_parser],
    )
    parser_validate.add_argument(
        "--semantic-index", default=DEFAULT_SEMANTIC_INDEX, help="Semantic index file"
    )
    parser_validate.add_argument(
        "--verbose", action="store_true", help="Show detailed discrepancies"
    )

    # semantic-fix command
    parser_fix = subparsers.add_parser(
        "semantic-fix",
        help="Fix the disconnect between code and documentation",
        parents=[parent_parser],
    )
    parser_fix.add_argument(
        "--semantic-index", default=DEFAULT_SEMANTIC_INDEX, help="Semantic index file"
    )
    parser_fix.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    parser_fix.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Minimum confidence threshold (default: 0.7)",
    )
    parser_fix.add_argument(
        "--provider",
        choices=sorted(LLMClient.SUPPORTED_PROVIDERS),
        help="LLM provider (default: env DEFRAG_LLM_PROVIDER or openai)",
    )
    parser_fix.add_argument(
        "--model",
        help="LLM model (defaults per provider)",
    )
    parser_fix.add_argument(
        "--api-key",
        help="API key for LLM provider",
    )
    parser_fix.add_argument(
        "--resume",
        action="store_true",
        help="Resume a previous semantic-fix run (skips completed docs and generated concepts)",
    )

    # semantic-autodoc command
    parser_autodoc = subparsers.add_parser(
        "semantic-autodoc",
        help="Generate conceptual documentation for undocumented code",
        parents=[parent_parser],
    )
    parser_autodoc.add_argument(
        "--semantic-index", default=DEFAULT_SEMANTIC_INDEX, help="Semantic index file"
    )
    parser_autodoc.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    parser_autodoc.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum confidence threshold (default: 0.5)",
    )
    parser_autodoc.add_argument(
        "--provider",
        choices=sorted(LLMClient.SUPPORTED_PROVIDERS),
        help="LLM provider (default: env DEFRAG_LLM_PROVIDER or openai)",
    )
    parser_autodoc.add_argument(
        "--model",
        help="LLM model (defaults per provider)",
    )
    parser_autodoc.add_argument(
        "--api-key",
        help="API key for LLM provider",
    )

    return {
        "semantic-analyze": cmd_semantic_analyze,
        "semantic-report": cmd_semantic_report,
        "semantic-validate": cmd_semantic_validate,
        "semantic-fix": cmd_semantic_fix,
        "semantic-autodoc": cmd_semantic_autodoc,
    }
