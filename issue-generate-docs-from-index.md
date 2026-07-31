# Ticket: Generate documentation from semantic index using autodoc

## Problem

The `defrag` tool currently produces a `semantic_index.json` file with doc and code concepts, but doesn't automatically generate documentation from it. The semantic index is just a half-step.

The goal of `defrag` is to:
1. Extract concepts from docs and code (semantic analysis)
2. Match code concepts to doc concepts
3. **Generate documentation for undocumented code** using `autodoc.py`'s `generate_conceptual_docs_for_undocumented_code`
4. **Fix missing links** in existing docs using `semantic-fix --apply`

Currently, the CLI has `semantic-analyze`, `semantic-report`, `semantic-validate`, and `semantic-fix`, but `semantic-fix --generate-docs --apply` isn't properly exposed or documented for generating new docs.

## Solution

1. **Ensure semantic index extraction is complete**: Remove any `--limit-docs` or `--limit-code` defaults that truncate analysis. All docs and code files should be processed.

2. **Add `semantic-autodoc` CLI command**: A new command that:
   - Loads the `semantic_index.json`
   - Finds undocumented code concepts (code with no doc matches)
   - Generates conceptual documentation using `ConceptualDocGenerator`
   - Writes docs to `docs/` directory

3. **Update `semantic-fix` to include doc generation**: Ensure `--generate-docs` flag works properly and is documented.

## Tasks

- [ ] Remove `--limit-docs` and `--limit-code` truncation from default `semantic-analyze`
- [ ] Add `semantic-autodoc` CLI command or ensure `semantic-fix --generate-docs --apply` works
- [ ] Document the full workflow: `semantic-analyze` → `semantic-fix --generate-docs --apply`
- [ ] Add tests for doc generation from semantic index

## Expected Outcome

After running:
```bash
defrag semantic-analyze
defrag semantic-fix --generate-docs --apply
```

The tool should:
- Extract all doc and code concepts
- Identify undocumented code
- Generate conceptual documentation in `docs/` directory
- Add physical links to existing docs where appropriate
