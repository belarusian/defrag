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

## Philosophy

Documentation quality has two dimensions:

1. **Semantic Truth**: Does the doc explain what the code actually does?
2. **Physical Grounding**: Do the references point to valid code locations?

Traditional tools only check #2. We check both.

## Architecture

### Layer 1: Semantic Understanding (LLM-Based)

**Document Analyzer**:
- Extracts concepts from markdown sections, as implemented in `defrag/analyzer.py:48-83`, where a language model is used to extract and index these concepts.
- LLM answers: "What does this section explain?" This process is further detailed in `defrag/llm.py:375-409`, which defines a method to extract semantic concepts from documentation.
- Output: `Concept(description, keywords, location)`, managed by the class in `defrag/semantic.py:16-54`, allowing conversion between object and dictionary forms.

**Code Analyzer**:
- Extracts functions/classes from code, as seen in `defrag/analyzer.py:85-135`, where a language model is used to analyze Python files.
- LLM answers: "What does this code do conceptually?" This is supported by `defrag/llm.py:411-449`, which extracts and analyzes code snippets for conceptual understanding.
- Output: `Concept(description, keywords, location)`, with relationships managed by the class in `defrag/semantic.py:58-95`.

**Matcher**:
- For each code concept, query: "Which docs explain this?" This matching process is handled by `defrag/analyzer.py:153-220`, which uses a language model for matching code concepts to documentation concepts.
- LLM scores relevance (0.0 to 1.0), a process refined through iterative context expansion as described in `defrag/refiner.py:95-234`.
- Output: `Match(code_concept, doc_concept, confidence, reasoning)`, with matches managed and queried by the class in `defrag/semantic.py:99-178`. The refinement of low-confidence matches is specifically addressed in `defrag/refiner.py:112-200`, ensuring sufficient confidence levels are reached.
### Layer 2: Physical Validation (Grounding)

**Link Validator**:
- Checks if doc contains references to matched code, as implemented in `defrag/validator.py:84-109`, which validates a documentation entry by checking its code references and returns a status and list of issues.
- Validates file paths and line numbers exist, a process further refined by the code in `defrag/analyzer.py:222-276`, which validates semantic matches between documentation and code by checking for physical links.
- Output: `physical_link_valid: bool`

**Confidence Adjuster**:
- High semantic + valid physical = HIGH confidence (0.9+), a concept supported by the iterative refinement process in `defrag/analyzer.py:153-220`, which matches code concepts to documentation concepts using a language model.
- High semantic + no physical = MEDIUM (suggest adding link), with suggestions for fixes handled by `defrag/validator.py:112-138`, which provides appropriate update or removal suggestions for invalid code references.
- High semantic + broken physical = INVESTIGATE (doc outdated?), a scenario that can be identified and updated as seen in `defrag/cli.py:42-105`, which validates documentation against code and updates their status based on identified issues.
- Low semantic + valid physical = INVESTIGATE (semantic model wrong?), a situation that might require further analysis as described in `defrag/analyzer.py:153-220`.
- Low semantic + no physical = GC candidate
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

### Step 4: Auto-Fix Missing Links

```bash
# Preview what would be fixed
When you run the command `python -m tools.defrag semantic-fix --doc docs/FAQ.md --preview`, it utilizes the functionality implemented in `defrag/fixer.py:238-273`. This function is responsible for generating a preview of potential fixes for broken links in a document by identifying semantic matches. By leveraging this code, the command provides a detailed look at what would be corrected, allowing you to review and verify the proposed changes before applying them.
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

The `semantic-fix` command intelligently inserts references, as implemented in `defrag/fixer.py:53-100`, which handles the insertion of a code reference into a specified section of a markdown document, ensuring that the reasoning for the reference is optionally included.

**Insertion Strategy**:
1. Finds the correct section by name
2. Looks for existing reference groupings ("See:", "Reference:")
3. Inserts near similar references or at end of section
4. Preserves markdown formatting and spacing, a process also handled by `defrag/fixer.py:103-185`, which automatically fixes missing references by using a semantic index to identify and suggest high-confidence matches.

**Format**:
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
