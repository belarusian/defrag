# Semantic Indexing and Concept Management

## Overview
This documentation provides an in-depth look at the components involved in semantic indexing and concept management within the `defrag/semantic.py` module. These components are designed to facilitate the creation, retrieval, and management of concepts and their associations with code files, ultimately enabling efficient semantic indexing.

## How the Semantic Index Works

### 1. Normalising concepts
- Convert raw doc and code snippets into `Concept` objects (`add_concept`, `get_concept`).
- Unique IDs created with `make_concept_id` keep everything addressable from the matcher, fixer and CLI.

### 2. Capturing relationships
- As the matcher runs, every successful pairing is recorded via `add_match`.
- Retrieval helpers (`get_matches_for_code`, `get_matches_for_doc`) quickly surface the relationships the CLI and fixer need.

### 3. Persisting the graph
- The index serialises through `to_dict`/`save` so long‑running analyses can be resumed.
- Loading (`load`) rebuilds the in‑memory objects so downstream tools share the same view of the world.

### 4. Enabling higher layers
- `semantic_cli.py` loads this index to power `semantic-report`, `semantic-validate`, and `semantic-fix`.
- The auto-doc flow uses the concept graph to generate conceptual documentation for every unlinked code path.

Together these pieces keep Defrag’s knowledge base synchronised: concepts are captured once, enriched through matching, and stored so every command can reason about documentation coverage, required fixes, and architectural groupings.

## Implementation References

- `defrag/semantic.py:make_concept_id` (lines 230-238)
- `defrag/semantic.py:to_dict` (lines 150-155)
- `defrag/semantic.py:add_concept` (lines 105-107)
- `defrag/semantic.py:get_concept` (lines 109-111)
- `defrag/semantic.py:get_code_concepts` (lines 117-119)
- `defrag/semantic.py:add_match` (lines 121-123)
- `defrag/semantic.py:get_matches_for_code` (lines 132-139)
- `defrag/semantic.py:save` (lines 167-171)
- `defrag/semantic.py:load` (lines 174-178)
