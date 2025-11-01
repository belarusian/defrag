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

1. **Analyze** - Extract concepts from docs and code using LLM, as implemented in `defrag/analyzer.py:24-363`, which defines a class for semantically analyzing a codebase and its documentation. This process includes analyzing markdown documentation files to extract and index concepts, as seen in `defrag/analyzer.py:48-83`, and analyzing Python files to extract and index concepts from functions and classes, as handled by `defrag/analyzer.py:85-135`.

2. **Match** - Match code concepts to doc concepts, a task that is handled by `defrag/analyzer.py:153-220`, which matches code concepts to documentation concepts using a language model with optional verbose output and iterative refinement.

3. **Validate** - Check physical links as grounding heuristic, supported by the iterative context expansion and language model client found in `defrag/refiner.py:95-234`, which refines semantic matches to ensure accuracy.

4. **Report** - Show semantic matches with confidence scores, a process that benefits from the efficient extraction and return of concepts from multiple document sections, as implemented in `defrag/llm.py:769-783`.

5. **GC** - Identify truly orphaned docs (no semantic matches), ensuring comprehensive coverage and accuracy in the semantic analysis process.
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

In order to perform semantic analysis, it is essential to utilize a provider along with an API key, as seen in the implementation of the client class within `defrag/llm.py:17-783`. This code defines how to interact with large language models (LLMs) from various providers, ensuring that the integration of these models is handled efficiently and securely. By leveraging this client class, users can seamlessly connect to different LLM providers, facilitating robust semantic analysis capabilities.
# Set provider + API key
export ANTHROPIC_API_KEY=your_key_here            # default provider: Anthropic Claude

The process of setting the API key is crucial for interacting with the Anthropic Claude API, as seen in `defrag/llm.py:786-808`, where a class is defined to generate text responses based on user prompts. This integration ensures that the API key is correctly configured to enable seamless communication with the default provider.
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
The process of automatically fixing missing links in your documentation can be efficiently handled by running the command `python -m tools.defrag semantic-fix --doc docs/FAQ.md`. This operation is implemented in the function found in `defrag/fixer.py:188-235`, which is designed to fix document references based on a semantic index. It provides options for performing a dry run and adjusting verbosity, ensuring that you can preview changes before applying them, as emphasized in this section.
# Preview fixes before applying
python -m tools.defrag semantic-fix --doc docs/FAQ.md --preview

# Apply fixes
python -m tools.defrag semantic-fix --doc docs/FAQ.md --apply

# Fix all docs with missing links (confidence >= 0.7)
The process of fixing documentation with missing links is handled by the command `python -m tools.defrag semantic-fix --apply --min-confidence 0.8`, which is implemented in the function found in `defrag/fixer.py:188-235`. This function automatically fixes document references based on a semantic index, ensuring that only links with a confidence level of 0.8 or higher are applied. The functionality includes options for a dry run and verbosity, allowing users to preview changes before applying them, as seen in the code's focus on confidence levels.

### Testing Mode (Limited Scope)
# Analyze just 5 docs and 10 code files
python -m tools.defrag semantic-analyze \
  --limit-docs 5 \
  --limit-code 10 \
  --verbose
```

### Running Integration Tests (LLM Required)

```bash
# Default provider is Anthropic unless DEFRAG_LLM_PROVIDER is set
The default configuration for interacting with large language models (LLMs) is to use Anthropic as the provider, unless the `DEFRAG_LLM_PROVIDER` environment variable is set to specify a different provider. This model selection and provider configuration process is implemented in `defrag/llm.py:17-783`, where a client class is defined to facilitate semantic analysis across different providers. When Anthropic is the chosen provider, the interaction with the Anthropic Claude API for generating text responses is specifically handled by the class defined in `defrag/llm.py:786-808`. Additionally, the initialization and return of a client and provider object, based on the specified provider type—either 'anthropic' or 'openai'—is managed in `defrag/llm.py:79-89`, ensuring that the correct provider is utilized according to the environment settings. To use Anthropic, ensure you have set your API key with `export ANTHROPIC_API_KEY=your_key_here`.
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
The process of scanning affected modules, as implemented in `defrag/cli.py:33-39`, involves using the command `python -m tools.defrag scan --path ingest/`. This function scans a codebase to update an index with code references and prints the results, ensuring that all relevant modules are accounted for and any changes are accurately reflected in the index.
# 2. Validate related docs
python -m tools.defrag validate --all

# 3. Review bad/unchecked docs
python -m tools.defrag report --status bad
python -m tools.defrag report --status unchecked

# 4. Fix or remove
# (manual updates to docs)

# 5. Mark as good after fixing
The command `python -m tools.defrag mark --doc docs/FIXED.md --status good` is part of the command-line interface for a documentation defragmentation tool, as implemented in `defrag/cli.py:214-300`. This code defines various commands to index, scan, validate, and mark documentation, aligning with the section's focus on marking a document as 'good' after fixing.

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