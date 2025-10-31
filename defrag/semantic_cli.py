"""
Semantic CLI commands for defrag tool.

Commands for LLM-based semantic analysis.
"""

import glob
import os

from .analyzer import SemanticAnalyzer
from .fixer import fix_document_references, fix_all_documents, preview_fix
from .llm import LLMClient
from .progress import ProgressTracker
from .scanner import scan_documentation
from .semantic import SemanticIndex
from .intelligent_scanner import scan_intelligently


DEFAULT_SEMANTIC_INDEX = "semantic_index.json"


def _resolve_index_path(index_arg, root_dir):
    """Resolve semantic index path - look in root_dir if using default."""
    if index_arg is None or index_arg == DEFAULT_SEMANTIC_INDEX:
        return os.path.join(root_dir, DEFAULT_SEMANTIC_INDEX)
    return index_arg


def cmd_semantic_analyze(args):
    """Run full semantic analysis on codebase and documentation."""
    print("=== Semantic Analysis ===")
    print(f"Root: {args.root}")
    provider = (args.provider or os.getenv(LLMClient.PROVIDER_ENV_VAR, "anthropic")).lower()
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

    # Initialize
    try:
        progress.log("Initializing LLM client...")
        llm = LLMClient(
            model=args.model,
            provider=provider,
            api_key=args.api_key,
            root_dir=args.root,
        )
        analyzer = SemanticAnalyzer(llm, root_dir=args.root)
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
        print(f"\nDiscovered files by category:")
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
    output_path = _resolve_index_path(args.output, args.root)
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
    """Auto-fix missing physical links in documentation."""
    index_path = _resolve_index_path(args.semantic_index, args.root)
    try:
        index = SemanticIndex.load(index_path)
    except FileNotFoundError:
        print(f"Error: Semantic index not found: {index_path}")
        print("Run 'semantic-analyze' first to build the index")
        return 1

    if args.preview:
        # Show preview without making changes
        if args.doc:
            preview = preview_fix(args.doc, index, args.root)
            print(preview)
        else:
            print("Error: --preview requires --doc")
            return 1
        return 0

    if args.doc:
        # Fix specific document
        print(f"Fixing {args.doc}...")
        if not args.apply:
            print("[DRY RUN] Use --apply to write changes\n")

        changes = fix_document_references(
            args.doc, index, args.root, dry_run=not args.apply, verbose=True
        )

        if changes:
            print(f"\n{'Applied' if args.apply else 'Would apply'} {len(changes)} fixes")
        else:
            print("\nNo fixes needed")

    else:
        # Fix all documents
        print("Fixing all documents...")
        if not args.apply:
            print("[DRY RUN] Use --apply to write changes\n")

        all_changes = fix_all_documents(
            index,
            args.root,
            dry_run=not args.apply,
            min_confidence=args.min_confidence,
            verbose=True,
        )

        total_changes = sum(len(changes) for changes in all_changes.values())
        print(
            f"\n{'Applied' if args.apply else 'Would apply'} {total_changes} fixes across {len(all_changes)} documents"
        )

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
        help="LLM provider to use (default: env DEFRAG_LLM_PROVIDER or anthropic)",
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
        help="Auto-fix missing physical links in documentation",
        parents=[parent_parser],
    )
    parser_fix.add_argument(
        "--semantic-index", default=DEFAULT_SEMANTIC_INDEX, help="Semantic index file"
    )
    parser_fix.add_argument("--doc", help="Fix specific document (default: all)")
    parser_fix.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    parser_fix.add_argument("--preview", action="store_true", help="Preview fixes without applying")
    parser_fix.add_argument(
        "--min-confidence", type=float, default=0.7, help="Minimum confidence to fix (default: 0.7)"
    )

    return {
        "semantic-analyze": cmd_semantic_analyze,
        "semantic-report": cmd_semantic_report,
        "semantic-validate": cmd_semantic_validate,
        "semantic-fix": cmd_semantic_fix,
    }
