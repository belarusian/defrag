# Defrag

```
     ____  _____ _____ ____      _    ____
    |  _ \| ____|  ___|  _ \    / \  / ___|
    | | | |  _| | |_  | |_) |  / _ \| |  _
    | |_| | |___|  _| |  _ <  / ___ \ |_| |
    |____/|_____|_|   |_| \_\/_/   \_\____|

    Documentation Defragmentation System
    LLM-powered semantic analysis + physical link validation
```

**LLM-powered documentation validation: semantic understanding + physical link grounding. Auto-fixes missing references.**


See `tests/integration/test_intelligent_doc_merging.py:400-502` - The code concept directly relates to defragmenting documentation using semantic analysis and link validation, which matches the description of a system for defragmenting documentation.

See `defrag/fixer.py:575-704` - The code concept of automatically fixing missing references using a semantic index aligns closely with the description of a system for defragmenting documentation using semantic analysis and link validation to auto-fix missing references.

See `defrag/fixer.py:744-799` - The code concept of automatically fixing document references based on semantic matches aligns closely with the description of a system for defragmenting documentation using semantic analysis and link validation to auto-fix missing references.

See `defrag/semantic_cli.py:305-391` - The code concept involves fixing documentation discrepancies using semantic analysis and link validation, which aligns with the description of a system for defragmenting documentation using these methods.

See `defrag/validator.py:112-138` - The code concept of suggesting fixes for invalid code references in documentation aligns with the description of a system for defragmenting documentation using semantic analysis and link validation to auto-fix missing references.

See `defrag/analyzer.py:309-348` - The code concept involves generating reports based on semantic analysis and validation, which aligns with the description of a system for defragmenting documentation using semantic analysis and link validation.

See `defrag/autodoc.py:551-598` - The code concept involves generating documentation for undocumented code concepts through semantic clustering, which aligns closely with the documentation system described in the option. Both involve semantic analysis and the creation of documentation, suggesting a strong match.
## The Problem

Documentation rots. Code changes. Links break. Traditional tools only check if references exist, but can't tell if the documentation actually explains what the code does.

See `defrag/schema.py:109-111` - The code concept involves identifying documents that need updates, which aligns with the issue of documentation becoming outdated as described in this section.

## The Solution

Defrag uses **two-layer validation**:

```
    SEMANTIC (LLM-Based)           PHYSICAL (Grounding)
         |                              |
    Understanding                   Validation
         |                              |
    What does code DO?            Do links exist?
    What do docs SAY?             Are they correct?
         |                              |
         +---------> TRUTH <------------+
```

**Layer 1: Semantic Understanding (Primary)**
- LLM analyzes what code does conceptually
- LLM analyzes what documentation explains
- Matches concepts with confidence scores (0.0 to 1.0)

**Layer 2: Physical Validation (Grounding Heuristic)**
- Checks if documentation references code
- Validates file paths and line numbers
- Signals semantic model correctness

**Together**: Identify accurate docs, outdated docs, missing links, and true orphans.

See `tests/integration/test_semantic_pipeline.py:211-245` - The code concept involves validating documentation links using semantic analysis and physical validation, which aligns with the two-layer validation process described in this section.

See `defrag/cli.py:42-105` - The code concept involves validating documentation against code and updating their status, which aligns with the two-layer validation process described in this section.

See `defrag/semantic_cli.py:238-302` - This section explains Defrag's two-layer validation process for ensuring the accuracy and relevance of documentation by using semantic understanding and physical validation, which aligns with the code concept of validating semantic matches against physical links and reporting discrepancies.

See `defrag/validator.py:84-109` - This section explains Defrag's two-layer validation process for ensuring the accuracy and relevance of documentation, which is relevant to the function's role in validating documentation entries.

See `defrag/analyzer.py:232-286` - This section explains Defrag's two-layer validation process for ensuring the accuracy and relevance of documentation by using semantic understanding and physical validation, which aligns closely with the code concept of validating semantic matches and updating confidence based on physical links.

See `defrag/analyzer.py:309-348` - The code concept includes validation and confidence thresholds, which matches the two-layer validation process described in this section.

See `defrag/autodoc.py:508-528` - The code concept involves validation and normalization of documentation responses, which aligns with the two-layer validation process described in this section.

## Quick Start

### Installation

```bash
pip install defrag
```

Or from source:

```bash
git clone https://github.com/kode-s/defrag.git
cd defrag

# Recommended: create a virtualenv and install deps
scripts/dev_setup.sh

# Or do it manually:
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Physical validation (fast, no LLM)
defrag index                    # Catalog documentation
defrag validate --doc README.md  # Check links
defrag report                   # Show status

# Semantic analysis (set provider + API key)
# OpenAI GPT-4o (default):

See `defrag/llm.py:824-846` - This section explains how to set the API key for OpenAI GPT-4o, which is essential for interacting with the API as described in the code concept.
export OPENAI_API_KEY=your_key_here
# Anthropic (optional override):
# export DEFRAG_LLM_PROVIDER=anthropic
# export ANTHROPIC_API_KEY=your_key_here
# export DEFRAG_LLM_MODEL=claude-sonnet-4-5-20250929   # optional override

defrag semantic-analyze --verbose        # Full analysis
defrag semantic-analyze --verbose --resume  # Resume and skip unchanged files
defrag semantic-report --show-gc         # View results
defrag semantic-validate --verbose       # Check discrepancies
defrag semantic-fix --apply --resume     # Continue fixing after a crash

See `defrag/semantic_cli.py:29-179` - This section provides commands for performing a semantic analysis, viewing results, and validating discrepancies using the defrag tool, with an optional model override, which aligns with the code concept of performing semantic analysis using a language model provider.

See `defrag/semantic_cli.py:182-235` - This section provides commands for performing a semantic analysis, viewing results, and validating discrepancies using the defrag tool, which aligns with the code concept of generating and displaying a semantic analysis report.

See `defrag/analyzer.py:36-46` - This section provides commands for performing a semantic analysis, viewing results, and validating discrepancies using the defrag tool, with an optional model override, which aligns with the code concept of initializing an analyzer for semantic analysis with an optional LLM client.

# Auto-fix missing links
defrag semantic-fix --doc README.md --preview  # Preview
defrag semantic-fix --doc README.md --apply    # Apply
```


See `tests/unit/test_fixer.py:72-95` - The code concept involves updating document references in a markdown file using a fallback mechanism, which aligns with the section explaining how to preview and apply automatic fixes for missing links in a README.md document using the defrag tool.

See `defrag/fixer.py:575-704` - The code concept involves auto-fixing missing links, which matches the documentation section explaining how to preview and apply automatic fixes for missing links in a README.md document using the defrag tool.

See `defrag/fixer.py:802-837` - This section explains how to preview and apply automatic fixes for missing links in a README.md document using the defrag tool, which aligns with the code concept of generating a preview of potential fixes for broken links based on semantic matches.
## How It Works

### Example

**Your Code** (`handler.py:177-208`):
```python
def _is_duplicate(point_id: str, ts_ms: int) -> bool:
    """Check if (point_id, ts) already exists in dedup table."""
    # ... DynamoDB conditional put logic
```

**Your Docs** (`FAQ.md` - "Deduplication" section):
```markdown
## Deduplication

We MERGE by (point_id, ts) to handle duplicates...
```

**Defrag Analyzes**:
1. **Semantic**: LLM understands both explain deduplication
2. **Match**: Confidence 0.92 - "FAQ explains dedup; code implements it"
3. **Physical**: Doc missing reference to handler.py
4. **Result**: Suggests adding `See handler.py:177-208`

**Auto-Fix**:
```bash
defrag semantic-fix --doc FAQ.md --apply
```

Inserts:
```markdown
## Deduplication

We MERGE by (point_id, ts) to handle duplicates...

See `handler.py:177-208` - FAQ explains dedup; code implements it
```

## Confidence Matrix

```
                Physical Link
                Valid   Missing   Broken
Semantic  High   0.95    0.80     0.70
Match     Med    0.75    0.60     0.40
          Low    0.50    0.30     0.20
```

**Interpretation**:
- **High semantic + valid physical = Truth** (0.95) - Everything checks out
- **High semantic + missing physical = Add link** (0.80) - Doc explains code but no reference
- **High semantic + broken physical = Doc outdated** (0.70) - Code moved or changed
- **Low semantic + valid physical = Wrong model?** (0.50) - Physical link exists but semantic match weak
- **Low semantic + no physical = GC candidate** (0.30) - No connection to codebase

See `tests/integration/test_autodoc_generation.py:239-288` - The code concept directly relates to testing the confidence threshold of semantic analysis, which aligns with the documentation section explaining confidence levels of semantic matches.

See `defrag/semantic_cli.py:182-235` - This section explains the confidence levels of semantic matches, which is directly relevant to the code concept's focus on confidence levels in semantic analysis.

## Use Cases

1. **Onboarding**: Quickly find which docs are accurate
2. **Refactoring**: Identify docs that need updating after code changes
3. **Documentation Debt**: Find orphaned docs to remove
4. **Quality Gates**: CI check for documentation staleness
5. **Knowledge Transfer**: Auto-add missing code references

## Commands

### Physical Layer (Fast)

```bash
defrag index                              # Build index
defrag scan                               # Update index
defrag validate --doc path/to/doc.md     # Validate one doc
defrag validate --all                     # Validate all
defrag mark --doc path/to/doc.md --status good  # Mark status
defrag report                             # Show report
defrag gc --show                          # Show GC candidates
```

See `defrag/schema.py:22-57` - The code concept involves managing and serializing documentation file entries with metadata, which aligns with managing and validating documentation indices and statuses.

See `defrag/schema.py:61-115` - The documentation section provides commands for managing and validating documentation indices and statuses, which aligns with the code concept of managing a documentation index with methods for serialization, document retrieval, and maintenance.

See `defrag/cli.py:24-30` - The section provides commands for managing and validating documentation indices, which aligns with the code concept of initializing or rebuilding a documentation index.

See `defrag/cli.py:108-135` - The code concept involves updating documentation status in an index, which aligns with managing and validating documentation indices and statuses.

See `defrag/cli.py:174-211` - The code concept involves generating a report on document status in an index, which aligns with the documentation section that provides commands for managing and validating documentation indices and statuses.

See `defrag/indexer.py:20-71` - This section provides commands for managing and validating documentation indices and statuses, which aligns with the code concept of building or updating a documentation index by scanning a directory for documentation files.

See `defrag/indexer.py:127-152` - The code concept involves updating the status and related information of a document within an index, which aligns with managing and validating documentation indices and statuses.

### Semantic Layer (LLM-Powered)


See `tests/integration/test_intelligent_discovery_integration.py:290-372` - The documentation describes the use of a semantic layer powered by a language model (LLM), which aligns with the code concept of a semantic analysis tool using LLM providers. The integration test for intelligent discovery in a minimal project setup is consistent with enhancing data interpretation through a semantic layer.

See `defrag/fixer.py:121-149` - The documentation describes the use of a language model to enhance data interpretation, which aligns with the code concept of using a language model to process and rewrite documents by merging references. Both involve leveraging a language model for processing and interpretation tasks.

See `defrag/fixer.py:267-357` - The section explains the use of a semantic layer powered by a language model to enhance data interpretation, which is relevant to the code concept of using a language model for document processing.

See `defrag/refiner.py:15-92` - The section explains the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which is relevant to the code's use of LLM suggestions for context expansion.

See `defrag/refiner.py:98-110` - The section explains the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which aligns with the code's use of an LLM client for codebase refinement.

See `defrag/semantic_cli.py:29-179` - This section explains the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which is relevant to the code concept of using a language model for semantic analysis.

See `defrag/analyzer.py:36-46` - This section explains the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which is relevant to the code concept of using an LLM client for semantic analysis.

See `defrag/analyzer.py:89-145` - The section describes the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which aligns with the code's use of an LLM for concept extraction from Python files.

See `defrag/analyzer.py:163-230` - The code concept involves matching code to documentation using a language model, which aligns closely with the documentation section describing the use of a semantic layer powered by a language model to enhance data interpretation. Both involve leveraging language models for understanding and processing information.

See `defrag/intelligent_scanner.py:16-290` - The section explains the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which aligns with the code's use of a language model for intelligent scanning and categorization.

See `defrag/intelligent_scanner.py:293-308` - The section describes the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which aligns with the code's use of an LLM client for file categorization.

See `defrag/intelligent_scanner.py:19-28` - The section explains the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which aligns with the code's use of a language model client for file categorization.

See `defrag/intelligent_scanner.py:30-43` - The section describes the use of a semantic layer powered by a language model (LLM) to enhance data interpretation, which aligns with the code's use of LLM guidance for file categorization.

See `defrag/intelligent_scanner.py:45-94` - The section describes the use of a semantic layer powered by a language model, which aligns with the code's use of a language model for directory exploration.

See `defrag/intelligent_scanner.py:124-169` - This section explains the use of a semantic layer powered by a language model to enhance data interpretation, which is relevant to the code concept of using a language model for file analysis.
```bash
# Requires provider + API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)

defrag semantic-analyze [options]
  --provider NAME         LLM provider (anthropic | openai)
  --model MODEL           LLM model (defaults per provider)
  --api-key KEY           Override API key
  --limit-docs N          Limit docs for testing
  --limit-code N          Limit code files for testing
  --verbose               Show progress

defrag semantic-report [options]
  --doc PATH              Show matches for specific doc
  --show-gc               Show GC candidates

defrag semantic-validate [options]
  --verbose               Show detailed discrepancies

defrag semantic-fix [options]
  --doc PATH              Fix specific doc (default: all)
  --preview               Preview without applying
  --apply                 Apply changes (default: dry run)
  --min-confidence N      Min confidence threshold (default: 0.7)
```


See `tests/integration/test_intelligent_discovery_integration.py:290-372` - The documentation section describes command-line options for semantic analysis using LLM providers, which aligns with the code concept of an integration test for a semantic analysis tool that supports different LLM providers. The keywords 'semantic analysis' and 'LLM provider' are directly relevant, indicating a strong match.

See `defrag/semantic_cli.py:394-490` - The documentation section describes command-line options for semantic analysis, which aligns with the code concept of adding semantic analysis-related commands to a CLI using argparse. The mention of LLM providers and API key requirements further supports the match, as these are likely related to the semantic analysis functionality.

See `defrag/llm.py:17-821` - This section provides command-line options for semantic analysis using LLM providers, which aligns with the code's purpose.

See `examples/icegraph_demo.py:25-197` - The code concept involves semantic analysis using a provider and API key, which matches the documentation on command-line options for semantic analysis using LLM providers with API key requirements.

See `examples/icegraph_demo.py:200-236` - This section provides command-line options for semantic analysis using LLM providers, which matches the code's purpose of analyzing documentation with a specified LLM provider.
## Architecture

```
defrag/
├── schema.py         # Data models (DocEntry, Concept, Match)
├── scanner.py        # Doc/code discovery
├── indexer.py        # Index persistence
├── validator.py      # Physical link validation
├── semantic.py       # Semantic models
├── llm.py            # LLM client (OpenAI/Anthropic)
├── analyzer.py       # Semantic analysis orchestrator
├── fixer.py          # Auto-fix missing links
├── cli.py            # CLI interface
└── semantic_cli.py   # Semantic commands
```

## Examples

See `examples/` for:
- `icegraph_demo.py` - Analyzing a real project
- `simple_demo.py` - Basic usage
- `ci_integration.py` - GitHub Actions integration

## Cost Estimation

LLM API calls for full analysis:
- Document concepts: ~1 call per section
- Code concepts: ~1 call per function/class
- Matching: ~1 call per code concept

**Typical project** (200 doc sections, 500 functions):
- Total calls: ~1200
- Claude 3.5 Sonnet cost: ~$13-15
- One-time cost, results cached

**Testing mode** (use `--limit-docs 5 --limit-code 10`):
- Cost: ~$0.50

## Requirements

- Python 3.8+
- OpenAI or Anthropic API key (for semantic analysis)

## License

MIT

## Contributing

Contributions welcome! See `CONTRIBUTING.md`.

## Authors

Built by [Kode-S](https://github.com/kode-s)

---

**The truth has two layers. Defrag finds both.**
