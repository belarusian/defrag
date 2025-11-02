# Semantic Analysis - LLM-Based Documentation Validation

```
    SEMANTIC LAYER (Primary Truth)

    What does the code DO?  <--LLM-->  What do docs DESCRIBE?
              |                              |
              v                              v
        Code Concepts                   Doc Concepts
              |                              |
              +---------> MATCH <------------+
                            |
                            v
                    Confidence Score
                            |
                            v
    PHYSICAL LAYER (Grounding Heuristic)

    Do the links exist?
    Are line numbers valid?
              |
              v
        Validation Signal
              |
              v
        Final Confidence
```


See `tests/integration/test_semantic_pipeline.py:42-245` - The code concept involves testing semantic matching between documentation and code, which aligns with the process described in this section.

See `tests/integration/test_semantic_pipeline.py:45-91` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which aligns with the code concept of testing semantic matching between documentation and code.

See `tests/integration/test_semantic_pipeline.py:93-134` - This section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which is relevant to the code concept of detecting orphaned documentation through semantic analysis.

See `tests/integration/test_semantic_pipeline.py:136-170` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which aligns with the code concept of detecting undocumented code using a semantic analyzer.

See `tests/integration/test_semantic_pipeline.py:211-245` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions, which matches the code concept of validating physical links and semantic matches.

See `tests/integration/test_autodoc_generation.py:191-237` - The code concept involves testing documentation generation and matching, which aligns with validating documentation by comparing code functionality with documentation descriptions.

See `tests/integration/test_autodoc_generation.py:239-288` - The documentation section describes a process for validating documentation using a language model and confidence scores, which aligns closely with the code concept of testing a semantic analysis tool's respect for a confidence threshold.

See `tests/integration/test_autodoc_generation.py:251-259` - The code concept involves identifying code concepts that are not documented with a high confidence level, which aligns with the process described in this section about validating documentation by comparing code functionality with documentation descriptions using a language model.

See `tests/integration/test_intelligent_doc_merging.py:172-222` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which aligns with the code concept of testing LLM integration for natural reference insertion.

See `tests/integration/test_intelligent_doc_merging.py:224-282` - The documentation describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which aligns with the code concept of testing a fallback mechanism triggered by an empty response from a language model.

See `tests/integration/test_intelligent_doc_merging.py:284-314` - The code concept involves testing that a document remains unchanged when there are no semantic matches, which aligns with the documentation validation process described in this section.

See `tests/integration/test_intelligent_doc_merging.py:339-398` - This section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which aligns with the code concept of testing LLM integration in documentation.

See `tests/unit/test_fixer.py:72-95` - The documentation describes a process for validating documentation using a language model and assessing accuracy through a confidence score, which aligns with the code concept of testing document reference updates using a fallback mechanism when a language model fails.

See `tests/unit/test_semantic_models.py:75-92` - The code concept involves testing concept matches and confidence, which aligns with validating documentation using a language model and confidence scores.

See `defrag/fixer.py:360-438` - The code concept involves using a language model to rewrite document chunks and provide a structured JSON response, which aligns with the documentation's focus on validating documentation by comparing code functionality with documentation descriptions using a language model.

See `defrag/fixer.py:744-799` - The documentation describes a process for validating documentation using a language model and confidence scores, which aligns with the code concept of automatically fixing document references based on semantic matches and confidence levels.

See `defrag/cli.py:42-105` - This section directly describes a process for validating documentation by comparing code functionality with documentation descriptions, which matches the code concept.

See `defrag/refiner.py:112-200` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, and assessing the accuracy through a confidence score, which aligns with the code concept of refining matches by expanding context to reach a sufficient confidence level.

See `defrag/semantic_cli.py:182-235` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which is related to the code concept of semantic analysis and confidence levels.

See `defrag/semantic_cli.py:238-302` - This section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, and assessing the accuracy through a confidence score and physical validation, which closely matches the code concept.

See `defrag/semantic_cli.py:305-391` - The code concept involves using a language model to validate documentation against code, which matches the description of validating documentation by comparing code functionality with documentation using a language model.

See `defrag/validator.py:84-109` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions, which aligns with the function's purpose of validating documentation entries by checking code references.

See `defrag/analyzer.py:163-230` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which aligns with the code concept of matching code concepts to documentation concepts using a language model.

See `defrag/analyzer.py:232-286` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, and assessing the accuracy through a confidence score and physical validation, which matches the code concept.

See `defrag/analyzer.py:309-348` - The code concept involves semantic analysis and validation, which is similar to the process described in this section for validating documentation using a language model and confidence scores.

See `defrag/analyzer.py:350-373` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, and assessing the accuracy through a confidence score, which aligns with the code concept of identifying undocumented code concepts through semantic matches and confidence levels.

See `defrag/intelligent_scanner.py:45-94` - The section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which is similar to the code's use of a language model for file scanning.

See `defrag/intelligent_scanner.py:171-215` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which aligns with the code concept of validating and normalizing a response from a language model.

See `defrag/llm.py:103-158` - This section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, and assessing the accuracy through a confidence score and physical validation. This aligns with the code concept of sending a prompt to an API, validating the JSON response, and retrying with corrections if parsing or schema validation fails.

See `defrag/llm.py:778-805` - The code concept involves using a language model to correct errors in JSON responses related to matching code concepts with documentation, which aligns with the process described in this section.

See `defrag/autodoc.py:508-528` - This section describes a process for validating documentation by comparing code functionality with documentation descriptions, which is similar to the code concept of validating documentation generation responses.

See `defrag/autodoc.py:530-549` - The code concept involves constructing a retry prompt for generating documentation, which aligns with the process of validating documentation by comparing code functionality with documentation descriptions using a language model.
## Philosophy

Documentation quality has two dimensions:

1. **Semantic Truth**: Does the doc explain what the code actually does?
2. **Physical Grounding**: Do the references point to valid code locations?

Traditional tools only check #2. We check both.

See `tests/integration/test_intelligent_doc_merging.py:339-398` - This section explains the two dimensions of documentation quality: semantic truth and physical grounding, which relates to the code's focus on quality checks for LLM integration.

## Architecture

### Layer 1: Semantic Understanding (LLM-Based)

**Document Analyzer**:
- Extracts concepts from markdown sections
- LLM answers: "What does this section explain?"
- Output: `Concept(description, keywords, location)`

**Code Analyzer**:
- Extracts functions/classes from code
- LLM answers: "What does this code do conceptually?"
- Output: `Concept(description, keywords, location)`

**Matcher**:
- For each code concept, query: "Which docs explain this?"
- LLM scores relevance (0.0 to 1.0)
- Output: `Match(code_concept, doc_concept, confidence, reasoning)`

See `tests/integration/test_semantic_pipeline.py:42-245` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which is relevant to the code concept.

See `tests/integration/test_semantic_pipeline.py:45-91` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is relevant to the code concept of semantic analysis and matching.

See `tests/integration/test_semantic_pipeline.py:136-170` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is relevant to the code concept of semantic analysis for documentation detection.

See `tests/integration/test_autodoc_generation.py:119-154` - The code concept directly involves using a language model for semantic analysis, which is described in this section.

See `tests/integration/test_autodoc_generation.py:156-189` - The code concept directly involves semantic understanding using LLMs to analyze documents and code, which matches the description of this documentation section.

See `tests/integration/test_intelligent_doc_merging.py:172-222` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is relevant to the code concept of testing LLM integration for natural reference insertion.

See `tests/integration/test_intelligent_doc_merging.py:339-398` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is relevant to the code concept of ensuring document references are naturally integrated.

See `defrag/fixer.py:121-149` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which aligns with the code concept of using a language model for document rewriting and reference merging.

See `defrag/fixer.py:152-264` - The code concept involves using an LLM client to integrate code references into markdown documents, which aligns with the description of using LLMs to analyze documents and code for semantic understanding.

See `defrag/fixer.py:267-357` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which aligns with the code concept of using a language model to rewrite document chunks.

See `defrag/fixer.py:360-438` - The code concept of using a language model for document editing and code integration matches the documentation's description of a system for semantic understanding using LLMs to analyze documents and code.

See `defrag/refiner.py:15-92` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which aligns with the code concept of using LLM suggestions for context expansion.

See `defrag/refiner.py:95-234` - This section describes a system for semantic understanding using LLMs, which is relevant to the code's use of a language model for refining semantic matches.

See `defrag/refiner.py:98-110` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is similar to the code's functionality of using an LLM client for codebase refinement.

See `defrag/refiner.py:112-200` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance, which is closely related to the code concept of refining matches by expanding context.

See `defrag/refiner.py:202-234` - The code concept of refining low-confidence matches using a semantic index aligns closely with the documentation section describing a system for semantic understanding using LLMs to analyze documents and code. Both involve using semantic analysis to improve the relevance of matches.

See `defrag/semantic_cli.py:29-179` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance, which is closely related to the code concept of semantic analysis using a language model.

See `defrag/semantic_cli.py:305-391` - The code concept uses a language model for semantic analysis, which aligns with the description of a system for semantic understanding using LLMs to analyze documents and code.

See `defrag/analyzer.py:24-373` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which directly matches the code's functionality of using a language model for semantic analysis and concept extraction.

See `defrag/analyzer.py:48-87` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance, which is relevant to the code concept of using a language model for concept extraction and indexing.

See `defrag/analyzer.py:89-145` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which matches the code's functionality of using an LLM for concept extraction.

See `defrag/analyzer.py:163-230` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance, which is closely related to the code concept.

See `defrag/analyzer.py:309-348` - The code concept of semantic analysis and matching aligns with the description of a system for semantic understanding using LLMs.

See `defrag/analyzer.py:350-373` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance, which is closely related to the code concept of identifying undocumented code concepts through semantic matches.

See `defrag/intelligent_scanner.py:16-290` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is relevant to the code's functionality of using a language model for file categorization.

See `defrag/intelligent_scanner.py:293-308` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which matches the code's functionality of using an LLM client for intelligent scanning and categorization.

See `defrag/intelligent_scanner.py:30-43` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which is relevant to the code's use of LLM guidance for categorizing files.

See `defrag/intelligent_scanner.py:124-169` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which aligns with the code concept of using a language model for file analysis and categorization.

See `defrag/llm.py:413-447` - The section describes a system for semantic understanding using LLMs to analyze documents, which is related to the code's function of extracting semantic concepts.

See `defrag/llm.py:568-726` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance, which aligns with the code concept of matching concepts and identifying similarities.

See `defrag/autodoc.py:19-679` - The documentation describes a system for semantic understanding using LLMs, which aligns with the code's purpose of generating conceptual documentation for code. The mention of LLMClient in the code concept further supports this match, as it suggests the use of language models for document analysis.

See `defrag/autodoc.py:682-732` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which aligns with the code concept of generating documentation using a semantic index and LLM client.

See `defrag/autodoc.py:70-155` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is closely related to the code's use of a language model for semantic clustering.

See `defrag/semantic.py:125-130` - The code concept involves retrieving concept matches for documentation, which aligns with the section describing a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance.

See `defrag/semantic.py:132-139` - The code concept involves retrieving concept matches for a code file, which aligns with the section describing a system for semantic understanding using LLMs to analyze documents and code, and match them based on relevance.

### Layer 2: Physical Validation (Grounding)

**Link Validator**:
- Checks if doc contains references to matched code
- Validates file paths and line numbers exist
- Output: `physical_link_valid: bool`

**Confidence Adjuster**:
- High semantic + valid physical = HIGH confidence (0.9+)
- High semantic + no physical = MEDIUM (suggest adding link)
- High semantic + broken physical = INVESTIGATE (doc outdated?)
- Low semantic + valid physical = INVESTIGATE (semantic model wrong?)
- Low semantic + no physical = GC candidate

See `tests/integration/test_semantic_pipeline.py:211-245` - The section explains adjusting confidence levels based on semantic and physical validation results, which is directly related to the code concept of confidence adjustment in link validation.

See `defrag/cli.py:42-105` - The section explains adjusting confidence levels based on validation results, which is relevant to updating documentation status based on validation.

See `defrag/semantic_cli.py:238-302` - This section explains the process of validating documentation links and adjusting confidence levels based on semantic and physical validation results, which is directly related to the code concept.

See `defrag/validator.py:112-138` - The code concept involves validation and fix suggestions for documentation, which matches the explanation of validating documentation links and adjusting confidence levels based on semantic and physical validation results.

See `defrag/analyzer.py:232-286` - This section explains the process of validating documentation links and adjusting confidence levels based on semantic and physical validation results, which directly relates to the code concept.

## Workflow

### Step 1: Build Semantic Index

```bash
python -m tools.defrag semantic-analyze \
  --model claude-sonnet-4-5-20250929 \
  --output semantic_index.json \
  --verbose
```

If a run stops midway, re-run with `--resume` (same root/output path) to reuse the
existing index. Defrag persists SHA256 hashes for each analyzed file, so only
docs or code that changed are reprocessed and any unfinished matching or
validation work is completed without repeating earlier LLM calls.

This will:
1. Scan all markdown files
2. Extract concepts using LLM
3. Analyze Python files (functions/classes)
4. Match code concepts to doc concepts
5. Validate with physical link checker
6. Save semantic index

See `tests/integration/test_intelligent_doc_merging.py:34-170` - The documentation section describes building a semantic index by analyzing files to extract and match concepts, which aligns closely with the code concept of creating a semantic index with associated concepts for testing intelligent document merging.

See `tests/integration/test_intelligent_doc_merging.py:400-502` - The code concept involves using a semantic index to map code references, which aligns with building a semantic index by analyzing files to extract and match concepts.

See `tests/unit/test_fixer.py:7-40` - The code concept of building a semantic index by linking document sections to code functions based on workflow concepts directly aligns with the description in this documentation section.

See `tests/unit/test_semantic_models.py:168-195` - The code concept involves testing the filtering of document concepts from a semantic index, which directly relates to the documentation section explaining how to build a semantic index by analyzing files to extract and match concepts. The keywords 'semantic', 'index', 'document', and 'concepts' are common to both the code concept and the documentation.

See `tests/unit/test_semantic_models.py:197-224` - The code concept involves filtering and retrieving code-related concepts from a semantic index, which aligns with the documentation section explaining how to build a semantic index by analyzing files to extract and match concepts.

See `defrag/refiner.py:202-234` - The code concept involves refining low-confidence matches using a semantic index, which aligns with the process of building a semantic index by analyzing files to extract and match concepts.

See `defrag/analyzer.py:48-87` - This section explains how to build a semantic index by analyzing markdown and Python files to extract and match concepts using a language model, which aligns closely with the code concept of analyzing markdown documentation files to extract and index concepts using a language model.

See `defrag/autodoc.py:682-732` - This section explains how to build a semantic index by analyzing markdown and Python files, which is relevant to the code concept of using a semantic index for generating documentation.

See `defrag/semantic.py:99-178` - This section directly explains how to build a semantic index by analyzing files to extract and match concepts, which is the core functionality of the code described.

See `defrag/semantic.py:158-165` - This section explains how to build a semantic index by analyzing markdown and Python files to extract and match concepts using a language model, which is relevant to the code concept of populating concepts and matches attributes in a SemanticIndex object.

See `defrag/semantic.py:113-115` - The code concept involves retrieving a list of concepts from documentation sources, which aligns with the process of building a semantic index by analyzing files to extract and match concepts.

### Step 2: Review Results

```bash
python -m tools.defrag semantic-report \
  --show-gc
```

Output:
```
=== Semantic Analysis Report ===
Documentation: 83 files, 421 concepts
Code: 156 files, 892 concepts
Total concepts: 1313

Semantic matches: 287
  High confidence (>=0.8): 203
  Validated by physical links: 145

GC candidates: 15 docs with no matches

Garbage Collection Candidates:
  - docs/OLD_DESIGN.md
  - docs/DEPRECATED_API.md
  ...
```

### Step 3: Investigate Discrepancies

```bash
python -m tools.defrag semantic-validate --verbose
```

Shows where semantic and physical disagree:

```
High confidence matches without physical links: 58
Suggested physical links to add:

  docs/FAQ.md:
    Add link: ingest/iot_rule/exploder_lambda/handler.py:177-208
    Reason: FAQ explains deduplication; code implements it

Mismatches (good semantic, broken physical): 12
Docs need updating (code changed):

  docs/ARCHITECTURE.md:
    Update reference to: ingest/birth_processor/handler.py:191-311
    Reasoning: Architecture describes birth processing; handler moved
```

See `defrag/semantic_cli.py:305-391` - The code concept involves resolving discrepancies between code and documentation, which is similar to the process of identifying and resolving discrepancies between semantic documentation and physical code links.

### Step 4: Auto-Fix Missing Links


See `defrag/fixer.py:575-704` - The code concept of automatically fixing missing references is directly related to the documentation section explaining how to automatically fix missing links in a process.

See `defrag/fixer.py:744-799` - The code concept involves automatically fixing document references, which matches the description of a process for automatically fixing missing links.

See `defrag/fixer.py:802-837` - This section explains how to automatically fix missing links in a process, which is closely related to the code concept of generating fixes for broken links.

See `defrag/validator.py:112-138` - The code concept of suggesting fixes for invalid code references is directly related to the process of automatically fixing missing links in documentation.
```bash
# Preview what would be fixed
python -m tools.defrag semantic-fix --doc docs/FAQ.md --preview

# Dry run (show changes but don't write)
python -m tools.defrag semantic-fix --doc docs/FAQ.md

# Apply fixes
python -m tools.defrag semantic-fix --doc docs/FAQ.md --apply

# Resume after a failure (skips docs already updated)
python -m tools.defrag semantic-fix --apply --resume
```

Output:
```
Fixing docs/FAQ.md...
  + Added reference in 'Bronze vs. Silver': ingest/iot_rule/exploder_lambda/handler.py:177-208 (confidence: 0.92)

Applied 1 fixes
```

The tool will:
1. Find sections with semantic matches
2. Insert code references at appropriate locations
3. Preserve markdown formatting
4. Group references with existing "See:" lines if present

### Step 5: View Specific Doc

```bash
python -m tools.defrag semantic-report --doc docs/FAQ.md
```

Shows all code matched to that doc with confidence and reasoning.

## Auto-Fix Details

The `semantic-fix` command intelligently inserts references:

**Insertion Strategy**:
1. Finds the correct section by name
2. Looks for existing reference groupings ("See:", "Reference:")
3. Inserts near similar references or at end of section
4. Preserves markdown formatting and spacing

**Format**:
```markdown
See `ingest/iot_rule/exploder_lambda/handler.py:177-208` - FAQ explains deduplication; code implements it
```

**Safety**:
- Default is dry run (use `--apply` to write)
- Only fixes high confidence matches (>= 0.7)
- Adjustable via `--min-confidence`
- Preview mode shows what would change

Resume mode (`--resume`) reuses `.defrag_fix_state.json` together with the
existing `semantic_index.json` so already rewritten documents are skipped and
conceptual docs are not regenerated for code clusters processed before an
interruption.

See `defrag/fixer.py:525-572` - The section explains how the `semantic-fix` command automatically inserts references into documentation, which aligns with the code concept of inserting a code reference into a markdown document.

See `defrag/fixer.py:575-704` - The code concept of using a semantic index to suggest high-confidence matches for missing links is similar to the documentation section explaining how the `semantic-fix` command automatically inserts references into documentation with a focus on maintaining formatting and ensuring high confidence in changes.

See `defrag/fixer.py:744-799` - The code concept of auto-fixing document references with a focus on confidence levels is similar to the description of the `semantic-fix` command that automatically inserts references into documentation with high confidence.

## Example Output

```json
{
  "concepts": {
    "doc:docs/FAQ.md:bronze_vs_silver": {
      "description": "Explains the difference between Bronze and Silver tables in the medallion architecture",
      "keywords": ["bronze", "silver", "deduplication", "enrichment"],
      "source": "docs/FAQ.md",
      "location": "Bronze vs. Silver"
    },
    "code:ingest/iot_rule/exploder_lambda/handler.py:_is_duplicate": {
      "description": "Implements deduplication check using DynamoDB conditional put",
      "keywords": ["deduplication", "dynamodb", "idempotency"],
      "source": "ingest/iot_rule/exploder_lambda/handler.py",
      "line_range": [177, 208]
    }
  },
  "matches": [
    {
      "code_concept_id": "code:ingest/iot_rule/exploder_lambda/handler.py:_is_duplicate",
      "doc_concept_id": "doc:docs/FAQ.md:bronze_vs_silver",
      "confidence": 0.92,
      "reasoning": "FAQ explains deduplication in Silver layer; code implements the actual dedup logic",
      "physical_link_valid": true,
      "suggested_link": "ingest/iot_rule/exploder_lambda/handler.py:177-208"
    }
  ]
}
```

## Confidence Scoring Matrix

```
                Physical Link Status
                Valid   Missing   Broken
Semantic  High   0.95    0.80     0.70
Match     Med    0.75    0.60     0.40
          Low    0.50    0.30     0.20
```

## Testing Mode

For development/testing, limit analysis scope:

```bash
# Analyze just 5 docs and 10 code files
python -m tools.defrag semantic-analyze \
  --limit-docs 5 \
  --limit-code 10 \
  --verbose
```

## Cost Considerations

LLM API calls:
- Document concept extraction: 1 call per section (~200 sections = 200 calls)
- Code concept extraction: 1 call per function/class (~500 functions = 500 calls)
- Concept matching: 1 call per code concept (~500 calls)

Total: ~1200 API calls for full analysis

Estimated cost (Claude 3.5 Sonnet):
- Input: ~2M tokens ($3/MTok) = $6
- Output: ~500K tokens ($15/MTok) = $7.50
- **Total: ~$13.50** for complete codebase analysis

Run incrementally or cache results.

## Future Enhancements

1. **Incremental Analysis**: Only analyze changed files
2. **Caching**: Store LLM responses to avoid re-analysis
3. **Multi-language**: Add TypeScript, Java analyzers
4. **Embeddings**: Pre-compute embeddings for faster matching
5. **Auto-fix**: Automatically add suggested physical links to docs
6. **CI Integration**: Fail builds if docs become stale

## Truth

```
    Semantic Match = What SHOULD be documented
    Physical Links = What IS documented

    Defrag tells you:
    1. What you forgot to document (high semantic, no link)
    2. What docs are wrong (low semantic, has link)
    3. What docs are stale (high semantic, broken link)
    4. What docs are orphans (no semantic match at all)
```

The physical layer grounds the semantic understanding.
Together, they tell the truth.

See `tests/integration/test_semantic_pipeline.py:136-170` - The code concept involves detecting undocumented code using semantic analysis, which aligns closely with the documentation section that explains the relationship between documented and undocumented code, highlighting discrepancies. This suggests that the documentation is directly relevant to the code's functionality.

See `tests/integration/test_autodoc_generation.py:251-259` - The documentation section explains the relationship between documented and undocumented code, which directly relates to the function's purpose of identifying code concepts that are not documented above a certain confidence threshold.

See `defrag/analyzer.py:350-373` - The documentation section directly addresses the issue of discrepancies between documented and undocumented code, which aligns with the function's purpose of identifying orphaned documentation.
