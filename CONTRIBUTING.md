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

See `defrag/llm.py:17-783` - The code concept involves setting up API keys for LLM providers, which aligns with the documentation on setting up an API key for Anthropic Claude.

See `defrag/llm.py:786-808` - This section directly relates to setting up an API key for Anthropic Claude, which is necessary for interacting with the API as described in the code concept.

See `defrag/llm.py:79-89` - The code concept involves initializing a client for the 'anthropic' provider, which aligns with setting up an API key for Anthropic Claude.
export ANTHROPIC_API_KEY=your_key_here           # Anthropic Claude (default)
# export DEFRAG_LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here            # OpenAI
```


See `defrag/llm.py:17-783` - The code concept mentions environment variables for API keys, which matches the documentation on setting an environment variable for the OpenAI API key.

See `defrag/llm.py:811-868` - The code concept involves interacting with OpenAI models, which likely requires setting an API key for authentication. This documentation section provides instructions for setting an environment variable for the OpenAI API key, which is relevant to the code's functionality.

See `defrag/llm.py:816-828` - The documentation section provides instructions for setting an environment variable for the OpenAI API key, which is relevant to the code concept of initializing an OpenAI client with an API key.

See `defrag/llm.py:79-89` - The code concept involves initializing a client for the 'openai' provider, which aligns with setting an environment variable for the OpenAI API key.
## Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=defrag --cov-report=html

# Run specific test
pytest tests/unit/test_semantic_models.py::TestConcept::test_concept_creation
```


See `defrag/semantic.py:16-54` - The documentation section explains testing concept creation in semantic models, which aligns with the code's focus on managing semantic concepts.
## Code Style

We use Black and Ruff for formatting:

```bash
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

1. Add logic to `semantic.py` or `analyzer.py`
2. Update `SemanticIndex` model if needed
3. Add tests in `tests/unit` or `tests/integration` as appropriate
4. Update `docs/SEMANTIC.md`

See `defrag/semantic.py:16-54` - The documentation section outlines steps for implementing and documenting a new semantic analysis feature, which aligns closely with the code concept of managing semantic concepts and conversion between object and dictionary forms.

### New CLI Command

1. Add command function in `cli.py` or `semantic_cli.py`
2. Register in subparsers
3. Add tests
4. Update README.md usage section

See `defrag/cli.py:214-300` - This section outlines the steps to add a new command to the CLI, which aligns with the code concept of defining a command-line interface for a documentation defragmentation tool.

### New Physical Validation Feature

1. Add logic to `validator.py`
2. Update `DocEntry` model if needed
3. Add tests in `tests/test_validator.py`
4. Update `docs/USAGE.md`

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
