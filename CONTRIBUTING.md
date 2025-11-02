# Contributing to Defrag

We welcome contributions! Here's how to get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/kode-s/defrag.git
cd defrag

# Recommended: bootstrap a virtualenv and install deps
scripts/dev_setup.sh

# Or install manually
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Set up API key for testing (choose provider)
export OPENAI_API_KEY=your_key_here            # OpenAI GPT-4o (default)
# export DEFRAG_LLM_PROVIDER=anthropic
# export ANTHROPIC_API_KEY=your_key_here       # optional Anthropic support

## Running Tests
Most unit tests run without network access, but integration tests require a valid
API key for the selected provider. With the environment prepared:

```bash
# Run all tests
pytest

# With coverage
pytest --cov=defrag --cov-report=html

# Run a specific test
pytest tests/unit/test_semantic_models.py::TestConcept::test_concept_creation
```

## Code Style

We use Black and Ruff for formatting:
# Format code
black defrag tests examples

# Lint
ruff check defrag tests examples
```

## Project Structure

```
defrag/
├── defrag/           # Main package
│   ├── schema.py     # Data models
│   ├── scanner.py    # Doc/code discovery
│   ├── indexer.py    # Index persistence
│   ├── validator.py  # Physical validation
│   ├── semantic.py   # Semantic models
│   ├── llm.py        # LLM client (provider abstraction)
│   ├── analyzer.py   # Semantic analysis
│   ├── fixer.py      # Auto-fix
│   └── cli.py        # CLI interface
├── tests/            # Test suite
├── examples/         # Usage examples
└── docs/             # Documentation
```

## Adding Features

### New Semantic Analysis Feature

1. Extend `semantic.py` or `analyzer.py` with the new behaviour.
2. Update `SemanticIndex` (and related models) if additional data needs to be stored.
3. Add unit and integration tests covering the new behaviour.
4. Document the change in `docs/SEMANTIC.md` (and `docs/USAGE.md` if user-facing).
### New CLI Command

1. Implement the command in `cli.py` or `semantic_cli.py`.
2. Register it with the CLI subparsers so it appears in `python -m tools.defrag --help`.
3. Add unit and/or integration tests that cover success and error paths.
4. Document the new command in `README.md` and, if relevant, `docs/USAGE.md`.

### New Physical Validation Feature

1. Extend the logic in `validator.py` (and related models) as needed.
2. Update `DocEntry` or other schema classes if new data needs to be stored.
3. Add tests in `tests/unit/test_validator.py` (and integration tests if required).
4. Update `docs/USAGE.md` to explain the new validation behaviour.

## Testing Guidelines

- All new features need tests
- Maintain test coverage above 80%
- Use fixtures for LLM mocking (don't hit API in tests)
- Test both success and error cases

## Documentation

- Update README.md for user-facing changes
- Update SEMANTIC.md for semantic layer changes
- Add docstrings to all public functions
- Include examples in docstrings

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with clear message
6. Push to your fork
7. Open a Pull Request

### Commit Message Format

```
Add brief description of change

Longer explanation of what changed and why.
Include any relevant context or decisions.

Fixes #123
```

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Assume good intent

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
