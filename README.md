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
git clone https://github.com/belarusian/defrag.git
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

# Semantic analysis (using local LLM)
# Set local LLM endpoint and dummy API key
export OPENAI_BASE_URL=http://192.168.1.157:8080/v1
export OPENAI_API_KEY=dummy

defrag semantic-analyze --verbose --provider openai --model Qwen3.6-27B-UD-Q4_K_XL.gguf
defrag semantic-analyze --verbose --resume      # Resume and skip unchanged files
defrag semantic-report --show-gc                # View results
defrag semantic-validate --verbose              # Check discrepancies

# Auto-fix missing links
defrag semantic-fix --doc README.md --preview   # Preview changes
defrag semantic-fix --doc README.md --apply     # Apply changes
defrag semantic-fix --apply --resume            # Resume interrupted fix run
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
# Configure LLM: Set OPENAI_BASE_URL=http://your-local-llm:port/v1 and OPENAI_API_KEY=dummy

defrag semantic-analyze [options]
  --provider NAME         LLM provider (openai)
  --model MODEL           LLM model
  --api-key KEY           Override API key
  --limit-docs N          Limit docs for testing
  --limit-code N          Limit code files for testing
  --verbose               Show progress
  --output OUTPUT         Output file for semantic index
  --resume                Resume from existing index

defrag semantic-report [options]
  --semantic-index PATH   Semantic index file
  --doc PATH              Show matches for specific doc
  --show-gc               Show GC candidates

defrag semantic-validate [options]
  --semantic-index PATH   Semantic index file
  --verbose               Show detailed discrepancies

defrag semantic-fix [options]
  --semantic-index PATH   Semantic index file
  --doc PATH              Fix specific doc (default: all)
  --preview               Preview without applying
  --apply                 Apply changes
  --min-confidence N      Min confidence threshold (default: 0.7)
  --resume                Resume a previous fix run
```

## Architecture

```
defrag/
├── schema.py         # Data models (DocEntry, Concept, Match)
├── scanner.py        # Doc/code discovery
├── indexer.py        # Index persistence
├── validator.py      # Physical link validation
├── semantic.py       # Semantic models
├── llm.py            # LLM client (OpenAI-compatible API)
├── analyzer.py       # Semantic analysis orchestrator
├── fixer.py          # Auto-fix missing links
├── cli.py            # CLI interface
└── semantic_cli.py   # Semantic commands
```

## Examples

See `examples/` for:
- `icegraph_demo.py` - Analyzing a real project

## Requirements

- Python 3.8+
- LLM endpoint (local via OPENAI_BASE_URL with dummy API key)

## License

MIT

## Contributing

Contributions welcome! See `CONTRIBUTING.md`.

## Authors

Built by [belarusian](https://github.com/belarusian)

---

**The truth has two layers. Defrag finds both.**
