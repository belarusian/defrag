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
# Anthropic Claude (default):
export ANTHROPIC_API_KEY=your_key_here
# OpenAI (defaults to gpt-5-mini-2025-08-07):
# export DEFRAG_LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here
# export DEFRAG_LLM_MODEL=gpt-4o   # optional override

defrag semantic-analyze --verbose        # Full analysis
defrag semantic-report --show-gc         # View results
defrag semantic-validate --verbose       # Check discrepancies

# Auto-fix missing links
defrag semantic-fix --doc README.md --preview  # Preview
defrag semantic-fix --doc README.md --apply    # Apply
```

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

### Semantic Layer (LLM-Powered)

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
