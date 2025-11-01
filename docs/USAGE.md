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

See `defrag/refiner.py:95-234` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which closely matches the code concept of refining semantic matches using iterative context expansion and a language model.

See `defrag/analyzer.py:24-363` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which directly relates to the code concept of semantic analysis and concept matching.

See `defrag/analyzer.py:48-83` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which is related to the code concept of analyzing markdown documentation files to extract and index concepts using a language model.

See `defrag/analyzer.py:85-135` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which is related to the code's function of analyzing Python files to extract and index concepts.

See `defrag/analyzer.py:153-220` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which is relevant to the code concept.

See `defrag/llm.py:769-783` - The section describes a comprehensive semantic analysis process for extracting, matching, validating, and reporting concepts, which aligns with the code's functionality of extracting and returning a list of concepts from multiple document sections for efficiency.

## Usage

### Quick Start (Physical Links Only)

```bash
# Build index
python -m tools.defrag index

See `defrag/cli.py:214-300` - This section provides a command to defragment an index using a Python module, which is related to the CLI tool's functionality described in the code concept.

# Validate a document
python -m tools.defrag validate --doc contracts/sparkplug_brick_example.md

# Mark as good
python -m tools.defrag mark --doc contracts/sparkplug_brick_example.md --status good

# Show report
python -m tools.defrag report
```

### Semantic Analysis (Provider + API Key Required)


See `defrag/llm.py:17-783` - The code concept involves using LLM providers with API keys, which is directly related to the documentation explaining the requirement of a provider and an API key for semantic analysis.
```bash
# Set provider + API key

See `defrag/llm.py:786-808` - This section provides instructions on setting the API key for the default provider, Anthropic Claude, which is essential for the code concept of interacting with the API.
export ANTHROPIC_API_KEY=your_key_here            # default provider: Anthropic Claude
# export DEFRAG_LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here             # use for OpenAI models
# export DEFRAG_LLM_MODEL=gpt-4o                  # optional model override

# Run full semantic analysis
python -m tools.defrag semantic-analyze --verbose
# python -m tools.defrag semantic-analyze --provider openai

# View semantic report
python -m tools.defrag semantic-report --show-gc

# Check semantic vs physical discrepancies
python -m tools.defrag semantic-validate --verbose

# View matches for specific doc
python -m tools.defrag semantic-report --doc docs/FAQ.md

# Auto-fix missing links (dry run first)
python -m tools.defrag semantic-fix --doc docs/FAQ.md

See `defrag/fixer.py:188-235` - The documentation section explicitly mentions performing a dry run to automatically fix missing links, which aligns closely with the code concept of auto-fixing document references with options for dry run and verbosity.

# Preview fixes before applying
python -m tools.defrag semantic-fix --doc docs/FAQ.md --preview

# Apply fixes
python -m tools.defrag semantic-fix --doc docs/FAQ.md --apply

# Fix all docs with missing links (confidence >= 0.7)
python -m tools.defrag semantic-fix --apply --min-confidence 0.8
```


See `defrag/fixer.py:188-235` - The documentation section explicitly describes fixing documentation by applying semantic fixes to missing links, which aligns closely with the code concept of automatically fixing document references based on a semantic index. The mention of a confidence level in the documentation also matches the code's focus on confidence levels.
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
# Default provider is Anthropic unless DEFRAG_LLM_PROVIDER is set

See `defrag/llm.py:17-783` - The code concept involves model selection and provider configuration, which aligns with the documentation on specifying a different provider using the DEFRAG_LLM_PROVIDER environment variable.

See `defrag/llm.py:786-808` - The documentation section describes Anthropic as the default provider, which aligns with the code concept of interacting with the Anthropic Claude API for text generation. This suggests that the code is implementing functionality related to the default provider setting described in the documentation.

See `defrag/llm.py:79-89` - The code concept mentions provider type selection, which is related to the default provider setting described in this documentation.
export ANTHROPIC_API_KEY=your_key_here
# Optional overrides:
# export DEFRAG_LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here
# export DEFRAG_LLM_MODEL=gpt-4o            # defaults to claude-sonnet-4-5-20250929 for Anthropic

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

See `defrag/cli.py:42-105` - The code concept involves validating documentation and updating their status based on issues, which aligns with the documentation section outlining the schema for indexing documents, including their validation status and code references.

## Code Reference Format

Documentation should include code references in format:

```
See: `path/to/file.py:start_line-end_line`

See `defrag/scanner.py:109-144` - The code concept of scanning and validating code references in documentation matches the explanation of how Defrag validates code reference patterns.

See `defrag/scanner.py:68-106` - The section explains the format for including code references in documentation and how Defrag validates these patterns, which aligns with the function's purpose of extracting and normalizing code reference patterns.

See `defrag/validator.py:84-109` - The section explains the format for including code references in documentation and how validation is performed, which is relevant to the function's purpose.

See `defrag/validator.py:14-33` - This section explains the format for including code references in documentation and how Defrag validates these patterns, which aligns with the function's purpose of parsing code references into file paths and line numbers.
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

See `defrag/cli.py:33-39` - The code concept involves scanning a codebase and updating an index, which aligns with the description of scanning affected modules using a defragmentation tool.

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


See `defrag/cli.py:214-300` - The code concept includes a command to mark documentation, which aligns with the section explaining how to mark a document as 'good'. This suggests that the documentation is directly related to the functionality implemented in the code.
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
