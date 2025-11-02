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


See `tests/integration/test_semantic_pipeline.py:136-170` - This section describes a tool for defragmenting documentation using semantic analysis, which is related to the code concept of detecting undocumented code.

See `defrag/semantic_cli.py:305-391` - The code concept is about fixing documentation using semantic analysis, which is related to a tool for defragmenting documentation using similar methods.

See `defrag/autodoc.py:551-598` - The section describes a tool for defragmenting documentation using semantic analysis, which aligns with the code's purpose of generating documentation for semantic clusters.
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

See `defrag/analyzer.py:232-286` - This section explains the two-layer validation process used by Defrag to ensure documentation is synchronized with code, which is relevant to the code concept of validating semantic matches and updating confidence.

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

See `tests/integration/test_semantic_pipeline.py:93-134` - This section describes the relationship between codebase files and their corresponding documentation, highlighting their status and potential garbage collection candidates, which aligns with the code concept of identifying orphaned documentation for garbage collection.

See `tests/integration/test_autodoc_generation.py:251-259` - The documentation section describes the process of identifying orphaned documentation, which aligns with the code concept of identifying code concept IDs that are not matched with a confidence level above a given threshold. Both focus on the relationship between code and documentation and the potential for garbage collection.

See `defrag/schema.py:103-107` - This section highlights the relationship between codebase files and their corresponding documentation, including potential garbage collection candidates, which aligns with the code concept of identifying orphaned documentation for garbage collection.

See `defrag/cli.py:42-105` - This section highlights the relationship between codebase files and documentation status, which is directly related to the code concept of updating documentation status based on validation.

See `defrag/cli.py:138-171` - This section describes the relationship between codebase files and their corresponding documentation, highlighting their status and potential garbage collection candidates, which aligns with the code concept of identifying orphaned documentation for garbage collection.

See `defrag/semantic_cli.py:182-235` - This section illustrates the relationship between codebase files and their corresponding documentation, highlighting their status and potential garbage collection candidates, which matches the code concept's focus on identifying orphaned documentation.

See `defrag/semantic.py:141-148` - This section describes the relationship between codebase files and their corresponding documentation, highlighting their status and potential garbage collection candidates, which aligns with the code concept of identifying orphaned documentation.

## Two Workflows

### Physical Link Validation (Fast)

1. **Index** - Catalog all documentation files
2. **Scan** - Extract code references from docs
3. **Validate** - Check if references are valid
4. **Mark** - Set status (good/bad/unchecked)
5. **Report** - Show what needs fixing

See `defrag/cli.py:214-300` - This section outlines a process involving indexing, scanning, validating, and marking, which aligns with the commands described in the code concept.

### Semantic Analysis (LLM-Powered, Comprehensive)

1. **Analyze** - Extract concepts from docs and code using LLM
2. **Match** - Match code concepts to doc concepts
3. **Validate** - Check physical links as grounding heuristic
4. **Report** - Show semantic matches with confidence scores
5. **GC** - Identify truly orphaned docs (no semantic matches)

See `tests/test_intelligent_scanner.py:13-105` - The code concept involves testing an intelligent scanner's ability to handle and categorize files, which aligns with the documentation's focus on LLM-powered semantic analysis for extracting and matching concepts. The keywords 'intelligent scanner', 'file categorization', and 'testing' are relevant to the described semantic analysis process.

See `tests/integration/test_semantic_pipeline.py:42-245` - This section explains a comprehensive LLM-powered semantic analysis process, which matches the code concept of testing semantic matching.

See `tests/integration/test_semantic_pipeline.py:45-91` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which is directly related to the code concept.

See `tests/integration/test_semantic_pipeline.py:136-170` - The code concept involves detecting undocumented code using semantic analysis, which aligns closely with the documentation section describing a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code.

See `tests/integration/test_semantic_pipeline.py:172-206` - The section describes a comprehensive LLM-powered semantic analysis process, which aligns with the code concept of iterative refinement in a semantic analysis pipeline.

See `tests/integration/test_autodoc_generation.py:119-154` - The code concept is about semantic analysis of an undocumented codebase, which matches the comprehensive LLM-powered semantic analysis process described here.

See `defrag/refiner.py:112-200` - The code concept of refining matches through iterative context expansion aligns closely with the described process of semantic analysis for matching and validating concepts. Both involve a methodical approach to improving match confidence between code and documentation.

See `defrag/analyzer.py:24-373` - The section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts, which is highly relevant to the code's purpose.

See `defrag/analyzer.py:48-87` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which is related to the code concept of analyzing markdown documentation files to extract and index concepts using a language model.

See `defrag/analyzer.py:89-145` - The documentation describes a semantic analysis process using an LLM to extract and process concepts from code, which aligns closely with the code concept of analyzing a Python file to extract and process concepts from functions and classes using an LLM.

See `defrag/analyzer.py:163-230` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which is relevant to the code concept.

See `defrag/analyzer.py:309-348` - The code concept of generating a report from semantic analysis matches the comprehensive LLM-powered semantic analysis process described in this section.

See `defrag/llm.py:568-726` - This section explains a comprehensive LLM-powered semantic analysis process for extracting, matching, validating, and reporting concepts from documentation and code, which is closely related to the code concept of matching concepts and identifying similarities.

See `defrag/llm.py:807-821` - The section describes a comprehensive semantic analysis process for extracting, matching, validating, and reporting concepts, which aligns with the code's functionality of extracting and returning a list of concepts from multiple document sections for efficiency.

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


See `tests/integration/test_semantic_pipeline.py:35-37` - This section involves a process related to semantic analysis requiring a provider and an API key, which matches the concept of checking for API credentials for LLM providers.

See `defrag/semantic_cli.py:29-179` - The code concept involves semantic analysis of a codebase using a language model provider, which aligns with the documentation section describing a process related to semantic analysis requiring a provider and an API key. This suggests the code implements the process described in the documentation.

See `defrag/llm.py:17-821` - This section involves a process related to semantic analysis requiring a provider and an API key, which matches the code's functionality.

See `defrag/llm.py:95-101` - The documentation section describes a process involving a provider and an API key, which aligns with the code concept of using a text generation provider. The mention of semantic analysis suggests a text-based operation, which matches the text generation aspect of the code.

See `defrag/llm.py:868-887` - The documentation section describes a process involving an API and a provider, which aligns with the code concept of sending a prompt to an API for text generation and response extraction. The mention of an API key suggests interaction with an external service, which is consistent with the code's use of a responses API or chat completions API.

See `examples/icegraph_demo.py:25-197` - The code concept involves a process related to semantic analysis requiring a provider and an API key, which aligns with the documentation on using an external service for semantic analysis.
```bash
# Set provider + API key

See `defrag/llm.py:824-846` - This section explains how to set the API key for the default provider, Anthropic Claude, which is directly related to the code's purpose of interacting with the Anthropic Claude API.
export ANTHROPIC_API_KEY=your_key_here            # default provider: Anthropic Claude
# export DEFRAG_LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here             # use for OpenAI models
# export DEFRAG_LLM_MODEL=gpt-4o                  # optional model override

# Run full semantic analysis
python -m tools.defrag semantic-analyze --verbose
# python -m tools.defrag semantic-analyze --provider openai

# Resume a previous run (skips unchanged files automatically)
python -m tools.defrag semantic-analyze --verbose --resume
# Resume mode features:
# - Loads existing semantic_index.json from previous run
# - Skips already-processed docs/code (file hash unchanged)
# - Detects file changes via SHA256 hash comparison
# - Reprocesses only modified files
# - Skips already-matched concept pairs
# - Skips already-validated matches
# - Dramatically reduces API costs on resume (~60% savings)
# - Safe to use even if previous run crashed mid-analysis
# - Atomic saves prevent index corruption

# View semantic report
python -m tools.defrag semantic-report --show-gc

# Check semantic vs physical discrepancies
python -m tools.defrag semantic-validate --verbose

See `defrag/analyzer.py:163-230` - The documentation describes a Python tool that validates semantic discrepancies with verbose output, which aligns closely with the code concept of matching code concepts to documentation using a language model with optional verbose output and refinement iterations.

# View matches for specific doc
python -m tools.defrag semantic-report --doc docs/FAQ.md

# Auto-fix missing links (dry run first)
python -m tools.defrag semantic-fix --doc docs/FAQ.md

See `tests/integration/test_intelligent_doc_merging.py:316-337` - This section explains how to perform a dry run to automatically fix missing links in a documentation file using a specific Python command, which aligns with the code concept of testing a document reference fixing function in dry run mode.

See `tests/unit/test_autodoc_security.py:127-150` - The section explains how to perform a dry run to automatically fix missing links in a documentation file, which aligns with the code concept of testing dry run mode for documentation generation.

# Preview fixes before applying
python -m tools.defrag semantic-fix --doc docs/FAQ.md --preview

See `defrag/fixer.py:802-837` - This section explains how to preview semantic fixes in a document before applying them using a specific Python command, which matches the code concept of generating a preview of potential fixes.

# Apply fixes
python -m tools.defrag semantic-fix --doc docs/FAQ.md --apply

# Resume a previous fix run after a failure
python -m tools.defrag semantic-fix --apply --resume
# Resume reuses the semantic_index.json plus .defrag_fix_state.json to skip documents
# already updated and to avoid regenerating conceptual docs for processed code.

# Fix all docs with missing links (confidence >= 0.7)
python -m tools.defrag semantic-fix --apply --min-confidence 0.8
```


See `defrag/fixer.py:744-799` - The code concept of fixing document references based on confidence levels matches the description of a command to fix documentation by applying semantic fixes with a specified confidence level.
### Testing Mode (Limited Scope)

```bash
# Analyze just 5 docs and 10 code files
python -m tools.defrag semantic-analyze \
  --limit-docs 5 \
  --limit-code 10 \
  --verbose
```

### Running Integration Tests (LLM Required)


See `tests/test_intelligent_scanner.py:108-126` - The code concept involves testing with a language model, and this section provides instructions for running integration tests that require a language model.

See `tests/integration/test_semantic_pipeline.py:42-245` - The code concept involves testing semantic matching between documentation and code implementations using a semantic analyzer, which aligns with the documentation section that provides instructions for running integration tests requiring a language model. The keywords 'semantic matching', 'documentation', 'code', and 'integration test' are directly relevant to the described functionality.

See `tests/integration/test_autodoc_generation.py:18-26` - This section provides instructions for running integration tests that require a language model, which matches the code's purpose of retrieving a language model client for testing.

See `tests/integration/test_intelligent_doc_merging.py:18-26` - This section provides instructions for running integration tests that require a language model, which is relevant to the code's purpose of retrieving a language model client for testing.

See `tests/integration/test_intelligent_discovery_integration.py:25-286` - The documentation specifically mentions running integration tests that require a language model, which directly matches the code concept of an integration test using a language model.

See `tests/integration/test_intelligent_discovery_integration.py:290-372` - The code concept is an integration test for a semantic analysis tool, which aligns with the documentation about running integration tests that require a language model.

See `tests/unit/test_fixer.py:43-69` - The code concept involves testing the integration of a language model, which aligns with running integration tests that require a language model.

See `tests/unit/test_depth_limit.py:77-136` - The code concept involves testing a scanner's ability to handle directory structures using a mock language model, which aligns with the documentation about running integration tests that require a language model.
```bash
# Default provider is Anthropic unless DEFRAG_LLM_PROVIDER is set

See `tests/unit/test_llm_client.py:55-65` - This section explains that Anthropic is the default provider, which directly matches the code concept of verifying the default provider.

See `tests/unit/test_llm_client.py:68-79` - This section explains that Anthropic is the default provider unless a different provider is specified using the DEFRAG_LLM_PROVIDER environment variable, which is relevant to the code concept of selecting OpenAI as the provider based on environment variables.

See `tests/unit/test_llm_client.py:82-92` - This section explains that Anthropic is the default provider unless a different provider is specified using the DEFRAG_LLM_PROVIDER environment variable, which aligns with the code concept of testing model environment variable overrides.

See `defrag/semantic_cli.py:29-179` - The documentation section explains the default provider for the language model, which aligns with the code concept of performing semantic analysis using a specified or default language model provider. This indicates that the code likely implements the functionality described in the documentation.

See `defrag/llm.py:79-89` - The code concept involves selecting a provider, which matches the documentation about Anthropic being the default provider unless specified otherwise.
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

See `defrag/schema.py:13-18` - The section outlines the schema for indexing documents, including their validation status, which aligns with the code concept of defining an enumeration for validation status.

See `defrag/schema.py:61-115` - This section outlines the schema for indexing documents, including their validation status, which is relevant to the code concept of managing a documentation index.

## Code Reference Format

Documentation should include code references in format:

```
See: `path/to/file.py:start_line-end_line`

See `defrag/scanner.py:109-144` - This section explains the format for including code references in documentation and how Defrag scans and validates these patterns, which aligns with the code concept of scanning documentation for code references and validating paths.

See `defrag/scanner.py:68-106` - The code concept involves extracting and normalizing code reference patterns from documentation, which aligns with the explanation of how Defrag scans and validates code reference patterns in documentation.

See `defrag/validator.py:84-109` - The documentation section explains the format for including code references and how Defrag validates these patterns, which directly aligns with the function's purpose of validating documentation entries by checking code references.

See `defrag/validator.py:66-81` - The documentation section explains the format for including code references in documentation and how Defrag scans and validates these patterns, which aligns with the code concept of validating code references against a root directory.

See `defrag/validator.py:36-63` - This section explains the format for including code references in documentation and how Defrag scans and validates these patterns, which aligns with the function's purpose of validating code references by checking file existence and line range.

See `defrag/validator.py:14-33` - This section explains the format for including code references in documentation and how Defrag scans and validates these patterns, which aligns with the function's purpose of parsing code reference strings into file paths and line numbers.

See `defrag/cli.py:33-39` - The documentation section explains the format for including code references in documentation and how Defrag scans and validates these patterns, which aligns with the code concept of scanning a codebase to update an index with code references.
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

See `defrag/schema.py:103-107` - The documentation describes generating reports on documentation with 'bad' or 'unchecked' status, which aligns with the code concept of identifying documents that are unchecked and have no code references for garbage collection.

See `defrag/schema.py:109-111` - The code concept involves retrieving documents marked as needing updates, which aligns with the documentation section that describes generating reports on documentation with 'bad' or 'unchecked' status. Both involve identifying documents that require attention.

# 4. Fix or remove
# (manual updates to docs)

# 5. Mark as good after fixing
python -m tools.defrag mark --doc docs/FIXED.md --status good
```

**Tip**: If semantic analysis stops midway (crash, network issue, etc.), simply re-run
with `--resume` to continue where you left off:

```bash
defrag semantic-analyze --resume --verbose
```

Resume mode is intelligent:
- Skips already-processed files (unchanged content hash)
- Detects file modifications since last run (SHA256 comparison)
- Reprocesses only changed files
- Preserves all matches and validation state
- Saves ~60% of API costs compared to full rerun

Example: Analysis crashes after processing 300/500 functions. Without `--resume`, you'd
pay for all 500 again ($15). With `--resume`, you only pay for the remaining 200 ($6).
Total savings: $9 on resume, or 60% reduction in wasted API costs.

**Tip**: `semantic-fix --apply --resume` reuses `.defrag_fix_state.json` plus the cached
`semantic_index.json` so completed documents are skipped and conceptual docs are not
regenerated for code you already processed before the crash.

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

See `defrag/semantic_cli.py:238-302` - This section explains the confidence levels of semantic matches against physical link statuses and their implications, which is relevant to the code concept.

See `defrag/analyzer.py:232-286` - This section explains the confidence levels of semantic matches against physical link statuses and their implications, which is related to the code concept of updating match confidence based on link validity.

## License

Same as parent project.
