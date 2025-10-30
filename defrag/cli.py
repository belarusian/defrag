"""
Command-line interface for defrag tool.

Usage:
    python -m tools.defrag <command> [options]
"""

import argparse
import sys
from datetime import datetime

from .indexer import (
    build_index,
    load_index,
    save_index,
    update_doc_status,
    DEFAULT_INDEX_PATH,
)
from .schema import DocStatus
from .validator import validate_doc, suggest_fixes
from .semantic_cli import add_semantic_commands


def cmd_index(args):
    """Initialize or rebuild the documentation index."""
    print("Building documentation index...")
    index = build_index(args.root, args.index)
    save_index(index, args.index)
    print(f"Index created: {args.index}")
    print(f"Found {len(index.documents)} documentation files")


def cmd_scan(args):
    """Scan codebase and update index with code references."""
    print(f"Scanning codebase at {args.root}...")
    index = build_index(args.root, args.index)
    save_index(index, args.index)
    print(f"Index updated: {args.index}")
    print(f"Scanned {len(index.documents)} documentation files")


def cmd_validate(args):
    """Validate documentation against code."""
    index = load_index(args.index)

    if args.doc:
        # Validate specific document
        doc = index.get_doc(args.doc)
        if not doc:
            print(f"Error: Document not in index: {args.doc}")
            return 1

        status, issues = validate_doc(doc, args.root)
        print(f"\nDocument: {doc.path}")
        print(f"Current status: {doc.status.value}")
        print(f"Suggested status: {status.value}")

        if issues:
            print("\nIssues found:")
            for issue in issues:
                print(f"  - {issue}")

            if status == DocStatus.BAD:
                fixes = suggest_fixes(doc, args.root)
                if fixes:
                    print("\nSuggested fixes:")
                    for fix in fixes:
                        print(f"  - {fix}")
        else:
            print("\nNo issues found")

        if args.auto_mark:
            update_doc_status(index, doc.path, status, notes=f"Auto-validated on {datetime.now()}")
            save_index(index, args.index)
            print(f"\nStatus updated to: {status.value}")

    else:
        # Validate all documents
        print("Validating all documents...")
        bad_count = 0
        good_count = 0

        for doc in index.documents:
            status, issues = validate_doc(doc, args.root)
            if status == DocStatus.BAD:
                bad_count += 1
                print(f"\nBAD: {doc.path}")
                for issue in issues:
                    print(f"  - {issue}")
            elif status == DocStatus.GOOD:
                good_count += 1

            if args.auto_mark:
                update_doc_status(index, doc.path, status)

        print(f"\nValidation complete:")
        print(f"  Good: {good_count}")
        print(f"  Bad: {bad_count}")
        print(f"  Unchecked: {len(index.documents) - good_count - bad_count}")

        if args.auto_mark:
            save_index(index, args.index)
            print("\nIndex updated with validation results")

    return 0


def cmd_mark(args):
    """Mark documentation status manually."""
    index = load_index(args.index)

    doc = index.get_doc(args.doc)
    if not doc:
        print(f"Error: Document not in index: {args.doc}")
        return 1

    try:
        status = DocStatus(args.status)
    except ValueError:
        print(f"Error: Invalid status: {args.status}")
        print(f"Valid values: {', '.join([s.value for s in DocStatus])}")
        return 1

    fixes = args.fixes if args.fixes else []
    update_doc_status(index, args.doc, status, args.note, fixes)
    save_index(index, args.index)

    print(f"Updated {args.doc}:")
    print(f"  Status: {status.value}")
    if args.note:
        print(f"  Note: {args.note}")
    if fixes:
        print(f"  Fixes: {len(fixes)}")

    return 0


def cmd_gc(args):
    """Show or apply garbage collection."""
    index = load_index(args.index)
    candidates = index.gc_candidates()

    if not candidates:
        print("No garbage collection candidates found")
        return 0

    print(f"Found {len(candidates)} GC candidates:")
    for doc in candidates:
        print(f"  - {doc.path}")
        if doc.notes:
            print(f"    Note: {doc.notes}")

    if args.apply:
        if args.dry_run:
            print("\n[DRY RUN] Would remove these files")
        else:
            print("\nRemoving files...")
            for doc in candidates:
                try:
                    import os

                    os.remove(doc.path)
                    print(f"  Removed: {doc.path}")
                    index.documents.remove(doc)
                except OSError as e:
                    print(f"  Error removing {doc.path}: {e}")

            save_index(index, args.index)
            print("\nIndex updated")

    return 0


def cmd_report(args):
    """Generate status report."""
    index = load_index(args.index)

    if args.status:
        try:
            status_filter = DocStatus(args.status)
        except ValueError:
            print(f"Error: Invalid status: {args.status}")
            return 1

        docs = [doc for doc in index.documents if doc.status == status_filter]
        print(f"\nDocuments with status '{args.status}': {len(docs)}")

        for doc in docs:
            print(f"\n  {doc.path}")
            print(f"    Last validated: {doc.last_validated or 'Never'}")
            print(f"    Code refs: {len(doc.code_refs)}")
            if doc.notes:
                print(f"    Notes: {doc.notes}")
            if doc.fixes:
                print(f"    Fixes needed:")
                for fix in doc.fixes:
                    print(f"      - {fix}")
    else:
        # Overall report
        print("\n=== Documentation Index Report ===")
        print(f"Last updated: {index.last_updated}")
        print(f"Total documents: {len(index.documents)}")
        print(f"\nStatus breakdown:")
        print(f"  Good: {len(index.good_docs())}")
        print(f"  Bad: {len(index.bad_docs())}")
        print(
            f"  Unchecked: {len([d for d in index.documents if d.status == DocStatus.UNCHECKED])}"
        )
        print(f"\nGC candidates: {len(index.gc_candidates())}")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Defrag - Documentation Defragmentation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Common arguments (parent parser for inheritance)
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--index",
        default=DEFAULT_INDEX_PATH,
        help=f"Path to index file (default: {DEFAULT_INDEX_PATH})",
    )
    parent_parser.add_argument(
        "--root",
        default=".",
        help="Root directory (default: current directory)",
    )

    # Copy parent args to main parser for backward compatibility
    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX_PATH,
        help=f"Path to index file (default: {DEFAULT_INDEX_PATH})",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # index command
    parser_index = subparsers.add_parser("index", help="Initialize documentation index")

    # scan command
    parser_scan = subparsers.add_parser("scan", help="Scan codebase for code references")

    # validate command
    parser_validate = subparsers.add_parser("validate", help="Validate documentation")
    parser_validate.add_argument("--doc", help="Specific document to validate")
    parser_validate.add_argument(
        "--auto-mark", action="store_true", help="Automatically update status"
    )

    # mark command
    parser_mark = subparsers.add_parser("mark", help="Mark documentation status")
    parser_mark.add_argument("--doc", required=True, help="Document path")
    parser_mark.add_argument("--status", required=True, help="Status (good/bad/unchecked)")
    parser_mark.add_argument("--note", default="", help="Optional note")
    parser_mark.add_argument("--fixes", nargs="*", help="List of fixes needed")

    # gc command
    parser_gc = subparsers.add_parser("gc", help="Garbage collection")
    parser_gc.add_argument("--apply", action="store_true", help="Apply GC (remove files)")
    parser_gc.add_argument(
        "--dry-run", action="store_true", help="Dry run (show what would be removed)"
    )

    # report command
    parser_report = subparsers.add_parser("report", help="Generate status report")
    parser_report.add_argument("--status", help="Filter by status (good/bad/unchecked)")

    # Add semantic analysis commands
    semantic_commands = add_semantic_commands(subparsers, parent_parser)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    commands = {
        "index": cmd_index,
        "scan": cmd_scan,
        "validate": cmd_validate,
        "mark": cmd_mark,
        "gc": cmd_gc,
        "report": cmd_report,
    }
    # Merge semantic commands
    commands.update(semantic_commands)

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
