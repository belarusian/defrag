#!/usr/bin/env python
"""
Demo: Analyzing IceGraph documentation with defrag.

This demo shows how to use defrag to analyze a real project's documentation.
We'll use the IceGraph (TriSparkLakeHouse) project as an example.

Usage:
    python examples/icegraph_demo.py --icegraph-path /path/to/TriSparkLakeHouse
"""

import argparse
import os
import sys
from typing import Optional

# Add parent dir to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from defrag.analyzer import SemanticAnalyzer
from defrag.llm import LLMClient
from defrag.scanner import scan_documentation


def run_demo(
    icegraph_path: str,
    limit_docs: int = 5,
    limit_code: int = 10,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """
    Run defrag analysis on IceGraph project.

    Args:
        icegraph_path: Path to IceGraph repository
        limit_docs: Limit number of docs to analyze (for demo speed)
        limit_code: Limit number of code files to analyze
    """
    print("=" * 60)
    print("DEFRAG DEMO: Analyzing IceGraph Documentation")
    print("=" * 60)
    print()

    if not os.path.exists(icegraph_path):
        print(f"Error: Path not found: {icegraph_path}")
        return 1

    print(f"Project: {icegraph_path}")
    print(f"Limits: {limit_docs} docs, {limit_code} code files")
    print()

    provider_name = (provider or os.getenv(LLMClient.PROVIDER_ENV_VAR, "anthropic")).lower()
    if provider_name not in LLMClient.SUPPORTED_PROVIDERS:
        valid = ", ".join(sorted(LLMClient.SUPPORTED_PROVIDERS))
        print(f"Error: Unsupported provider '{provider_name}'. Choose from: {valid}")
        return 1
    key_env = LLMClient.PROVIDER_KEY_ENVS.get(provider_name)
    resolved_api_key = api_key or (os.getenv(key_env) if key_env else None)

    # Check for API key
    if not resolved_api_key:
        env_hint = key_env or "provider API key"
        print(f"Warning: {env_hint} not set for provider '{provider_name}'")
        print("Set it to run semantic analysis:")
        if key_env:
            print(f"  export {key_env}=your_key_here")
        print()
        print("Running physical validation only...")
        print()

        # Just show what docs exist
        docs = scan_documentation(icegraph_path)
        print(f"Found {len(docs)} documentation files:")
        for doc in docs[:10]:
            print(f"  - {doc}")
        if len(docs) > 10:
            print(f"  ... and {len(docs) - 10} more")
        return 0

    # Initialize analyzer
    print("[1/4] Initializing LLM client...")
    try:
        llm = LLMClient(provider=provider_name, model=model, api_key=resolved_api_key)
        analyzer = SemanticAnalyzer(llm, root_dir=icegraph_path)
        provider_label = {
            "anthropic": "Anthropic Claude",
            "openai": "OpenAI",
        }.get(provider_name, provider_name.title())
        print(f"  Connected to {provider_label} API")
    except Exception as e:
        print(f"  Error: {e}")
        return 1

    print()

    # Analyze documentation
    print("[2/4] Analyzing documentation...")
    doc_paths = scan_documentation(icegraph_path)
    print(f"  Found {len(doc_paths)} total docs")

    if limit_docs:
        # Prioritize interesting docs
        priority_patterns = ["FAQ", "ARCHITECTURE", "README", "contracts/"]
        priority_docs = [d for d in doc_paths if any(p in d for p in priority_patterns)]
        other_docs = [d for d in doc_paths if d not in priority_docs]
        doc_paths = (priority_docs + other_docs)[:limit_docs]
        print(f"  Analyzing {len(doc_paths)} docs (limited for demo)")

    analyzer.analyze_documentation(doc_paths, verbose=False)
    print(f"  Extracted {len(analyzer.index.get_doc_concepts())} concepts")
    print()

    # Analyze code
    print("[3/4] Analyzing code...")
    import glob

    code_paths = []
    for pattern in ["ingest/**/*.py", "tools/defrag/**/*.py"]:
        full_pattern = os.path.join(icegraph_path, pattern)
        code_paths.extend(
            [os.path.relpath(p, icegraph_path) for p in glob.glob(full_pattern, recursive=True)]
        )

    if limit_code:
        code_paths = code_paths[:limit_code]
        print(f"  Analyzing {len(code_paths)} files (limited for demo)")

    analyzer.analyze_code_files(code_paths, verbose=False)
    print(f"  Extracted {len(analyzer.index.get_code_concepts())} concepts")
    print()

    # Match concepts
    print("[4/4] Matching concepts...")
    analyzer.match_all_concepts(verbose=False)
    analyzer.validate_with_physical_links(verbose=False)
    print(f"  Found {len(analyzer.index.matches)} semantic matches")
    print()

    # Generate report
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    report = analyzer.generate_report()

    print(f"\nDocumentation: {report['doc_concepts']} concepts from {report['total_docs']} files")
    print(f"Code: {report['code_concepts']} concepts from {report['total_code_files']} files")
    print()
    print(f"Semantic Matches: {report['total_matches']} total")
    print(f"  High confidence (>=0.8): {report['high_confidence_matches']}")
    print(f"  Validated by physical links: {report['validated_matches']}")
    print()

    if report["unmatched_docs"] > 0:
        print(f"GC Candidates: {report['unmatched_docs']} docs with no semantic matches")
        if report["gc_candidates"]:
            print("\nExamples:")
            for doc in report["gc_candidates"][:5]:
                print(f"  - {doc}")

    print()

    # Show example matches
    print("=" * 60)
    print("EXAMPLE MATCHES")
    print("=" * 60)
    print()

    high_conf_matches = [m for m in analyzer.index.matches if m.confidence >= 0.8]
    for i, match in enumerate(high_conf_matches[:3], 1):
        code_concept = analyzer.index.get_concept(match.code_concept_id)
        doc_concept = analyzer.index.get_concept(match.doc_concept_id)

        if not code_concept or not doc_concept:
            continue

        print(f"{i}. {doc_concept.source}")
        print(f"   Section: {doc_concept.location}")
        print(f"   Matches: {code_concept.source}:{code_concept.location}")
        print(f"   Confidence: {match.confidence:.2f}")
        print(f"   Reasoning: {match.reasoning}")
        if match.physical_link_valid is not None:
            status = "Valid" if match.physical_link_valid else "Missing/Broken"
            print(f"   Physical Link: {status}")
        print()

    print("=" * 60)
    print("\nDemo complete!")
    print("\nTo see full results, run:")
    print(f"  cd {icegraph_path}")
    print("  defrag semantic-analyze")
    print("  defrag semantic-report --show-gc")
    print("  defrag semantic-fix --doc docs/FAQ.md --preview")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Demo: Analyze IceGraph documentation with defrag")
    parser.add_argument(
        "--icegraph-path",
        default=os.path.expanduser("~/Code/TriSparkLakeHouse"),
        help="Path to IceGraph repository",
    )
    parser.add_argument(
        "--limit-docs", type=int, default=5, help="Limit number of docs (for demo speed)"
    )
    parser.add_argument(
        "--limit-code", type=int, default=10, help="Limit number of code files (for demo speed)"
    )
    parser.add_argument(
        "--provider",
        choices=sorted(LLMClient.SUPPORTED_PROVIDERS),
        help="LLM provider to use",
    )
    parser.add_argument(
        "--model",
        help="Override model for the selected provider",
    )
    parser.add_argument(
        "--api-key",
        help="Override API key for the selected provider",
    )

    args = parser.parse_args()

    return run_demo(
        args.icegraph_path,
        args.limit_docs,
        args.limit_code,
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    sys.exit(main())
