# Defrag - Documentation Defragmentation Tool

```
     ____  _____ _____ ____      _    ____
    |  _ \| ____|  ___|  _ \    / \  / ___|
    | | | |  _| | |_  | |_) |  / _ \| |  _
    | |_| | |___|  _| |  _ <  / _ _\ \ |_| |
    |____/|_____|_|   |_| \_\/_/   \_\____|

    Documentation Defragmentation System
    LLM-powered semantic analysis + physical link validation
```

## Purpose

Defrag uses two-layer validation to keep documentation synchronized with code:

**Layer 1: Semantic (LLM-Based)**
- What does the code DO conceptually?
- What do the docs DESCRIBE?
- Match concepts using LLM understanding
- Primary truth source

**Layer 2: Physical (Grounding Heuristic)**
- Do code references exist?
- Are line numbers valid?
- Validates semantic model correctness
- Provides confidence signal

Together: Identify accurate, outdated, and orphaned documentation.

## Concept

```
   CODEBASE                INDEX                 DOCUMENTATION
   --------                -----                 -------------

   handler.py    -------> [docs_index.yaml] <------ ARCHITECTURE.md
   ids.py        -------> |                | <------ FAQ.md
   birth.py      -------> | Status:        | <------ contracts/*.md
                           |  - good        |
                           |  - bad         |
                           |  - unchecked   |
                           |                |
                           | GC candidates  |
                           '------------------'
```

## Two Workflows

### Physical Link Validation (Fast)

1. **Index** - Catalog all documentation files
2. **Scan** - Extract code references from docs
3. **Validate** - Check if references are valid
4. **Mark** - Set status (good/bad/unchecked)
5. **Report** - Show what needs fixing

### Semantic Analysis (LLM-Powered, Comprehensive)

1. **Analyze** - Extract concepts from docs and code using LLM
2. **Match** - Match code concepts to doc concepts
3. **Validate** - Check physical links as grounding heuristic
4. **Report** - Show semantic matches with confidence scores
5. **GC** - Identify truly orphaned docs (no semantic matches)

## Usage

### Quick Start (Physical Links Only)

```bash
# Build index
python -m tools.defrag index

# Validate a document
python -m tools.defrag validate --doc contracts/sparkplug_brick_example.md

# Mark as good
python -m tools.defrag mark --doc contracts/sparkplug_brick_example.md --status good

# Show report
python -m tools.defrag report
```

### Semantic Analysis (Provider + API Key Required)

```bash
# Set provider + API key
export OPENAI_API_KEY=your_key_here             # default provider: OpenAI GPT-4o
# export DEFRAG_LLM_PROVIDER=anthropic
# export ANTHROPIC_API_KEY=your_key_here         # optional Anthropic support
# export DEFRAG_LLM_MODEL=claude-sonnet-4-5-20250929  # optional model override

# Run full semantic analysis
python -m tools.defrag semantic-analyze --verbose
# python -m tools.defrag semantic-analyze --provider openai

# Resume a previous run (skips unchanged files automatically)
python -m tools.defrag semantic-analyze --verbose --resume
# Resume mode:
# - Reuses the existing semantic_index.json
# - Skips docs/code whose content hash has not changed
# - Reprocesses only new or modified files
# - Preserves existing matches and validation results
# - Ensures atomic writes to avoid index corruption

# View semantic report
python -m tools.defrag semantic-report --show-gc

# Check semantic vs physical discrepancies
python -m tools.defrag semantic-validate --verbose

# View matches for specific doc
python -m tools.defrag semantic-report --doc docs/FAQ.md

# Auto-fix missing links (dry run first)
python -m tools.defrag semantic-fix --doc docs/FAQ.md

# Preview fixes before applying
python -m tools.defrag semantic-fix --doc docs/FAQ.md --preview

# Apply fixes
python -m tools.defrag semantic-fix --doc docs/FAQ.md --apply

# Resume a previous fix run after a failure
python -m tools.defrag semantic-fix --apply --resume
# Resume mode uses the saved semantic index and `.defrag_fix_state.json` to skip
# documents that were already rewritten and to avoid regenerating conceptual docs
# for code that was processed before the crash.

# Fix all docs with missing links (confidence >= 0.7)
python -m tools.defrag semantic-fix --apply --min-confidence 0.8
```

### Testing Mode (Limited Scope)

```bash
# Analyze just 5 docs and 10 code files
python -m tools.defrag semantic-analyze \
  --limit-docs 5 \
  --limit-code 10 \
  --verbose
```

### Running Integration Tests (LLM Required)

```bash
# Default provider is OpenAI unless DEFRAG_LLM_PROVIDER is set
export OPENAI_API_KEY=your_key_here
# Optional overrides:
# export DEFRAG_LLM_PROVIDER=anthropic
# export ANTHROPIC_API_KEY=your_key_here
# export DEFRAG_LLM_MODEL=claude-sonnet-4-5-20250929  # defaults to gpt-4o for OpenAI

# Run semantic pipeline integration suite with verbose logging
pytest tests/integration -vv \
  --log-cli-level=INFO \
  --log-cli-format='%(levelname)s %(name)s:%(lineno)d %(message)s'
```

Use `--log-cli-level=DEBUG` for even more detail, and remember that each provider's environment variable must be available to the test process.

## Index Schema

```yaml
version: "1.0"
last_updated: "2025-10-30T10:00:00Z"

documents:
  - path: "docs/ARCHITECTURE.md"
    status: "good"              # good | bad | unchecked
    last_validated: "2025-10-30T10:00:00Z"
    code_refs:
      - "ingest/iot_rule/exploder_lambda/handler.py:177-208"
      - "ingest/birth_processor/handler.py:191-311"
    notes: "Verified dedup logic section"

  - path: "docs/LEGACY.md"
    status: "bad"
    last_validated: "2025-10-29T15:00:00Z"
    code_refs:
      - "old_module/handler.py:50-100"  # File no longer exists
    notes: "References deleted code"
    fixes:
      - "Update to reference new handler.py"
      - "Remove section on deprecated workflow"

  - path: "docs/ORPHAN.md"
    status: "unchecked"
    last_validated: null
    code_refs: []
    notes: "Never referenced in recent scans - GC candidate"
```

## Code Reference Format

Documentation should include code references in format:

```
See: `path/to/file.py:start_line-end_line`
```

Examples:
- `ingest/birth_processor/handler.py:87-128`
- `ingest/iot_rule/exploder_lambda/handler.py:177`

Defrag scans for these patterns and validates them.

## Integration with Workflow

After major code changes:

```bash
# 1. Scan affected modules
python -m tools.defrag scan --path ingest/

# 2. Validate related docs
python -m tools.defrag validate --all

# 3. Review bad/unchecked docs
python -m tools.defrag report --status bad
python -m tools.defrag report --status unchecked

# 4. Fix or remove
# (manual updates to docs)

# 5. Mark as good after fixing
python -m tools.defrag mark --doc docs/FIXED.md --status good
```

## Files

**Physical Layer**:
- `schema.py` - Data models (DocEntry, DefragIndex)
- `scanner.py` - Doc discovery & code ref extraction
- `indexer.py` - Index builder & persistence
- `validator.py` - Physical link validation
- `cli.py` - Command-line interface
- `docs_index.yaml` - Physical index (generated)

**Semantic Layer**:
- `semantic.py` - Concept models (Concept, Match, SemanticIndex)
- `llm.py` - LLM client (Anthropic/OpenAI API)
- `analyzer.py` - Semantic analysis orchestrator
- `fixer.py` - Auto-fix missing physical links
- `semantic_cli.py` - Semantic CLI commands
- `semantic_index.json` - Semantic index (generated)
- `SEMANTIC.md` - Detailed semantic analysis docs

## Philosophy

Documentation has two forms of truth:

**Semantic Truth**: Does the doc explain what the code actually does?
**Physical Grounding**: Do the references point to valid locations?

Traditional tools only check physical links. We check semantic understanding first, then validate with physical evidence.

```
         SEMANTIC (Primary)
              |
    Does code DO what docs SAY?
         (LLM-based)
              |
              v
         Confidence: 0.0 - 1.0
              |
              v
         PHYSICAL (Grounding)
              |
    Are the links valid?
         (Fast check)
              |
              v
    Final Confidence = Semantic × Physical
```

### Confidence Matrix

```
                Physical Link
                Valid   Missing   Broken
Semantic  High   0.95    0.80     0.70
Match     Med    0.75    0.60     0.40
          Low    0.50    0.30     0.20
```

**High semantic + valid physical = Truth**
**High semantic + missing physical = Add link**
**High semantic + broken physical = Doc outdated**
**Low semantic + valid physical = Wrong semantic model**
**Low semantic + no physical = GC candidate**

## License

Same as parent project.
