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


See `defrag/validator.py:112-138` - This section describes a system for defragmenting documentation using semantic analysis and link validation to automatically fix missing references, which aligns closely with the code concept of suggesting fixes for invalid code references in documentation.

See `defrag/fixer.py:103-185` - This section describes a system for defragmenting documentation using semantic analysis and link validation to automatically fix missing references, which aligns closely with the code concept of auto-fixing missing references using a semantic index.

See `defrag/fixer.py:188-235` - The code concept of automatically fixing document references using a semantic index aligns closely with the description of defragmenting documentation using semantic analysis and link validation.

See `defrag/scanner.py:109-144` - The code concept involves scanning documentation for code references and validating them, which aligns with the description of defragmenting documentation using semantic analysis and link validation.
## The Problem

Documentation rots. Code changes. Links break. Traditional tools only check if references exist, but can't tell if the documentation actually explains what the code does.

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

See `defrag/analyzer.py:222-276` - This section explains Defrag's two-layer validation process for ensuring the accuracy and relevance of documentation by using semantic understanding and physical validation.

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


See `defrag/llm.py:375-409` - The documentation section describes a process that involves responding with a JSON object containing a description and keywords, which aligns with the code concept of extracting semantic concepts and returning a JSON object.
```bash
# Physical validation (fast, no LLM)
defrag index                    # Catalog documentation
defrag validate --doc README.md  # Check links
defrag report                   # Show status

# Semantic analysis (set provider + API key)
# Anthropic Claude (default):

See `defrag/llm.py:786-808` - This section explains how to set the API key for Anthropic Claude, which is relevant to the code concept of interacting with the Anthropic Claude API.
export ANTHROPIC_API_KEY=your_key_here
# OpenAI (defaults to gpt-5-mini-2025-08-07):
# export DEFRAG_LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here
# export DEFRAG_LLM_MODEL=gpt-4o   # optional override

defrag semantic-analyze --verbose        # Full analysis
defrag semantic-report --show-gc         # View results
defrag semantic-validate --verbose       # Check discrepancies

See `defrag/analyzer.py:36-46` - This section provides commands for performing a semantic analysis, viewing results, and validating discrepancies using the defrag tool, with an optional model override, which aligns with the code concept of initializing an analyzer for semantic analysis with an optional LLM client.

# Auto-fix missing links
defrag semantic-fix --doc README.md --preview  # Preview
defrag semantic-fix --doc README.md --apply    # Apply
```


See `defrag/fixer.py:103-185` - This section explains how to preview and apply automatic fixes for missing links in a README.md document using the defrag tool, which is directly related to the code concept of auto-fixing missing references.

See `defrag/fixer.py:188-235` - The code concept includes auto-fixing document references, which matches the description of previewing and applying automatic fixes for missing links in a README.md document.
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

See `defrag/analyzer.py:299-338` - This section explains the confidence levels of semantic matches between documentation and physical code links, which is relevant to the code concept's focus on confidence thresholds and validated matches.

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

See `defrag/cli.py:24-30` - This section provides commands for managing and validating documentation indices and statuses, which aligns with the code concept of initializing or rebuilding a documentation index.

See `defrag/cli.py:42-105` - The code concept involves validating documentation against code and updating their status based on identified issues, which aligns closely with the documentation section that provides commands for managing and validating documentation indices and statuses.

See `defrag/cli.py:108-135` - The documentation section provides commands for managing and validating documentation indices and statuses, which aligns with the code concept of updating documentation status in an index.

See `defrag/cli.py:174-211` - The code concept involves generating a report on document status in an index, which aligns with managing and validating documentation indices and statuses.

See `defrag/cli.py:214-300` - This section provides commands for managing and validating documentation indices and statuses, which is relevant to the code concept of a CLI tool with commands to index, scan, validate, and mark documentation.

See `defrag/indexer.py:20-71` - This section provides commands for managing and validating documentation indices and statuses, which aligns with the code concept of building or updating a documentation index by scanning a directory for documentation files.

See `defrag/indexer.py:127-152` - The code concept involves updating the status and related information of a document within an index, which aligns with managing and validating documentation indices and statuses.

### Semantic Layer (LLM-Powered)


See `defrag/refiner.py:98-110` - The section explains the use of a semantic layer powered by a large language model (LLM), which aligns with the code concept of using an LLM client for codebase refinement.

See `defrag/analyzer.py:36-46` - This section explains the use of a semantic layer powered by a large language model (LLM), which is relevant to the code concept involving semantic analysis and an optional LLM client.

See `defrag/analyzer.py:153-220` - The code concept involves matching code and documentation concepts using a language model, which aligns with the documentation section explaining the use of a semantic layer powered by a large language model (LLM).
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

## Architecture

```
defrag/
├── schema.py         # Data models (DocEntry, Concept, Match)
├── scanner.py        # Doc/code discovery
├── indexer.py        # Index persistence
├── validator.py      # Physical link validation
├── semantic.py       # Semantic models
├── llm.py            # LLM client (Anthropic/OpenAI)
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
- Anthropic or OpenAI API key (for semantic analysis)

## License

MIT

## Contributing

Contributions welcome! See `CONTRIBUTING.md`.

## Authors

Built by [Kode-S](https://github.com/kode-s)

---

**The truth has two layers. Defrag finds both.**
