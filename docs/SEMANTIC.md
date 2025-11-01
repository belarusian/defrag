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


See `defrag/validator.py:84-109` - The documentation describes a process for validating documentation by comparing code functionality with documentation descriptions, which aligns with the function's purpose of validating documentation entries by checking code references.

See `defrag/validator.py:112-138` - This section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which is related to the code concept of checking validity and suggesting fixes.

See `defrag/refiner.py:112-200` - The code concept of refining matches by expanding context aligns with the process described in this section, which involves validating documentation by comparing code functionality with documentation descriptions and adjusting confidence levels.

See `defrag/analyzer.py:153-220` - This section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, which is similar to the code concept of matching code concepts to documentation concepts.

See `defrag/analyzer.py:222-276` - This section explains a process for validating documentation by comparing code functionality with documentation descriptions using a language model, and then verifying the physical links and line numbers to generate a final confidence score.

See `defrag/analyzer.py:299-338` - The documentation section describes a process for validating documentation by comparing code functionality with documentation descriptions, which aligns closely with the code concept of generating a semantic analysis report based on confidence levels. Both involve matching code and documentation and assessing confidence in those matches.

See `defrag/analyzer.py:340-363` - The code concept of identifying undocumented code concepts through semantic matches aligns with the process described in this section, which involves validating documentation by comparing code functionality with documentation descriptions using a language model.

See `defrag/llm.py:218-238` - The code concept involves generating prompts for schema violations, which aligns with the process of validating documentation by comparing code functionality with documentation descriptions.

See `defrag/cli.py:42-105` - The code concept involves validating documentation against code and updating their status based on identified issues, which aligns with the process described in this section.
## Philosophy

Documentation quality has two dimensions:

1. **Semantic Truth**: Does the doc explain what the code actually does?
2. **Physical Grounding**: Do the references point to valid code locations?

Traditional tools only check #2. We check both.

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

See `defrag/refiner.py:95-234` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which aligns with the code concept of refining semantic matches using a language model.

See `defrag/refiner.py:98-110` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is similar to the code concept of using an LLM client for codebase refinement.

See `defrag/refiner.py:112-200` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which matches the code concept of refining matches through context expansion and confidence adjustment.

See `defrag/semantic.py:16-54` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which directly relates to the code's purpose of managing semantic concepts.

See `defrag/semantic.py:58-95` - The code concept involves managing relationships between code and documentation concepts, which aligns with the section describing a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance.

See `defrag/semantic.py:99-178` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which aligns with the code concept of managing and querying semantic concepts and their matches.

See `defrag/semantic.py:113-115` - The code concept involves retrieving a list of concepts from documentation sources, which aligns with the section describing a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance.

See `defrag/semantic.py:125-130` - The code concept involves retrieving concept matches for documentation, which aligns with the section describing a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance.

See `defrag/analyzer.py:24-363` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which aligns closely with the code concept of semantic analysis and concept matching using a language model.

See `defrag/analyzer.py:48-83` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which is relevant to the code concept of using a language model for concept extraction and indexing.

See `defrag/analyzer.py:85-135` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which is relevant to the code's use of a language model for concept extraction and indexing.

See `defrag/analyzer.py:153-220` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which aligns closely with the code concept of matching code concepts to documentation concepts using a language model.

See `defrag/analyzer.py:299-338` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which is closely related to the code concept of generating a semantic analysis report based on concept matches.

See `defrag/analyzer.py:340-363` - The section describes a system for semantic understanding using LLMs to analyze documents and code, which matches the code concept of identifying undocumented code concepts through semantic matches.

See `defrag/llm.py:375-409` - This section describes a system for semantic understanding using LLMs to analyze documents and code, which is closely related to the code concept of extracting semantic concepts from documentation.

See `defrag/llm.py:411-449` - This section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which aligns with the code concept of extracting and analyzing code snippets for conceptual understanding.

See `defrag/llm.py:530-688` - The section describes a system for semantic understanding using LLMs to analyze documents and code, and match them based on conceptual relevance, which aligns closely with the 'match_concepts' function's purpose of identifying and matching related concepts within a dataset.

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

See `defrag/validator.py:84-109` - This section explains the process of validating documentation by checking references to code, which is directly related to the function's task of validating documentation entries.

See `defrag/validator.py:112-138` - This section explains the process of validating documentation by checking references to code and adjusting confidence levels based on semantic and physical validation results, which is relevant to the code concept of suggesting fixes for invalid code references.

See `defrag/analyzer.py:153-220` - The documentation section describes a process of validating documentation by checking references to code, which aligns closely with the code concept of matching code concepts to documentation concepts using a language model. Both involve validation and refinement processes.

See `defrag/analyzer.py:222-276` - This section explains the process of validating documentation by checking references to code and adjusting confidence levels based on semantic and physical validation results.

See `defrag/cli.py:42-105` - This section explains the process of validating documentation by checking references to code and adjusting confidence levels based on semantic and physical validation results, which is closely related to the code concept.

## Workflow

### Step 1: Build Semantic Index

```bash
python -m tools.defrag semantic-analyze \
  --model claude-sonnet-4-5-20250929 \
  --output semantic_index.json \
  --verbose
```

This will:
1. Scan all markdown files
2. Extract concepts using LLM
3. Analyze Python files (functions/classes)
4. Match code concepts to doc concepts
5. Validate with physical link checker
6. Save semantic index

See `defrag/refiner.py:202-234` - The code concept involves refining low-confidence matches using a semantic index, which aligns with the process of building a semantic index by analyzing files to extract and match concepts.

See `defrag/semantic.py:99-178` - This section explains how to build a semantic index by analyzing markdown and Python files to extract and match concepts, which is directly related to the code concept of managing and querying semantic concepts.

See `defrag/semantic.py:158-165` - This section explains how to build a semantic index by analyzing markdown and Python files to extract and match concepts using a language model, which aligns with the code concept of constructing a SemanticIndex object from a dictionary by populating its concepts and matches attributes.

See `defrag/analyzer.py:48-83` - This section explains how to build a semantic index by analyzing markdown and Python files to extract and match concepts using a language model, which aligns closely with the code concept of analyzing markdown documentation files to extract and index concepts using a language model.

See `defrag/analyzer.py:85-135` - This section explains how to build a semantic index by analyzing markdown and Python files to extract and match concepts using a language model, which aligns closely with the code concept of analyzing a Python file to extract and index concepts using a language model.

See `defrag/indexer.py:20-71` - This section explains how to build a semantic index by analyzing markdown and Python files, which is related to the code concept of building or updating a documentation index.

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

See `defrag/cli.py:138-171` - This section explains how to review the results of a semantic analysis report, including the identification of garbage collection candidates, which aligns with the code concept of identifying orphaned documentation for garbage collection.

See `defrag/analyzer.py:299-338` - This section explains how to review the results of a semantic analysis report, including the identification of garbage collection candidates, which aligns with the code concept of generating a semantic analysis report summarizing documentation and code file matches.

See `defrag/semantic.py:141-148` - This section explains how to review the results of a semantic analysis report, including the identification of garbage collection candidates, which aligns with the code concept of identifying unmatched documentation files.
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

### Step 4: Auto-Fix Missing Links


See `defrag/fixer.py:103-185` - This section explains how to automatically fix missing links in a process, which is relevant to the code concept of auto-fixing missing references.

See `defrag/fixer.py:188-235` - The function's purpose of automatically fixing document references is directly related to the process of automatically fixing missing links.
```bash
# Preview what would be fixed
python -m tools.defrag semantic-fix --doc docs/FAQ.md --preview

See `defrag/fixer.py:238-273` - The section explains how to preview semantic fixes in a document using a specific Python command, which aligns with the code concept of generating a preview of potential fixes for broken links based on semantic matches.

# Dry run (show changes but don't write)
python -m tools.defrag semantic-fix --doc docs/FAQ.md

# Apply fixes
python -m tools.defrag semantic-fix --doc docs/FAQ.md --apply
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

See `defrag/fixer.py:53-100` - The section explains how the `semantic-fix` command automatically inserts references into documentation, which aligns with the code concept of inserting a code reference into a markdown document.

See `defrag/fixer.py:103-185` - This section explains how the `semantic-fix` command automatically inserts references into documentation with a focus on maintaining formatting and ensuring high-confidence matches, which is similar to the code concept.

See `defrag/fixer.py:188-235` - The semantic-fix command's focus on automatically inserting references with high-confidence matches is relevant to the code's functionality.

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

See `defrag/analyzer.py:340-363` - This section highlights the relationship between what should be documented and what is actually documented, which is relevant to the code concept of identifying undocumented code concepts.
