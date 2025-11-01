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
export ANTHROPIC_API_KEY=your_key_here           # Anthropic Claude (default)

When setting up your API key for testing with Anthropic Claude, it's essential to understand how this key is utilized within the system. The process of interacting with large language models (LLMs) from various providers, including Anthropic, is defined in the client class implemented in `defrag/llm.py:17-783`. This class is crucial for semantic analysis and requires proper API key configuration to function correctly.

Specifically, for Anthropic Claude, the interaction is further detailed in the class defined in `defrag/llm.py:786-808`, which handles generating text responses based on user prompts. This interaction necessitates the API key setup as described here.

Additionally, the initialization of a client and provider object, which is based on the specified provider type such as 'anthropic', is handled by the code in `defrag/llm.py:79-89`. This initialization process underscores the importance of correctly setting up your API key to ensure seamless communication with the Anthropic Claude API.
# export DEFRAG_LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here            # OpenAI

## Running Tests

When setting up your environment for running tests, it's crucial to configure your API keys correctly. For OpenAI, this involves setting the `OPENAI_API_KEY` environment variable, as detailed in the documentation. This setup is essential for initializing an OpenAI client, as seen in `defrag/llm.py:816-828`, where the client is initialized with a specified model and API key. The process of interacting with OpenAI models, which requires this API key for authentication, is further handled by the class defined in `defrag/llm.py:811-868`. Additionally, the broader context of interacting with large language models (LLMs) from various providers, including OpenAI, is implemented in `defrag/llm.py:17-783`, where environment variables for API keys are a key consideration. Finally, the initialization of a client for the 'openai' provider, which aligns with setting this environment variable, is addressed in `defrag/llm.py:79-89`.
# Run all tests
pytest

# With coverage
pytest --cov=defrag --cov-report=html

# Run specific test
To ensure the robustness of our semantic models, we run targeted tests such as `pytest tests/unit/test_semantic_models.py::TestConcept::test_concept_creation`. This test specifically examines the creation of concepts, a process intricately handled by the class implemented in `defrag/semantic.py:16-54`. This class is responsible for representing and managing semantic concepts extracted from documents or code, allowing seamless conversion between object and dictionary forms.

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

1. Add logic to `semantic.py` or `analyzer.py`, as seen in `defrag/semantic.py:16-54`, where a class is defined for representing and managing semantic concepts extracted from documents or code. This implementation allows for conversion between object and dictionary forms, which is crucial for the new feature.
2. Update `SemanticIndex` model if needed to ensure it aligns with the new logic and supports the conversion processes handled by the class in `defrag/semantic.py:16-54`.
3. Add tests in `tests/unit` or `tests/integration` as appropriate to verify the functionality and integration of the new semantic analysis feature, ensuring that the conversion between object and dictionary forms is thoroughly tested.
4. Update `docs/SEMANTIC.md` to reflect the changes and enhancements made, including the new capabilities for managing semantic concepts as implemented in `defrag/semantic.py:16-54`.
### New CLI Command

1. Add command function in `cli.py` or `semantic_cli.py`, as seen in the implementation of the command-line interface for a documentation defragmentation tool in `defrag/cli.py:214-300`, which includes commands to index, scan, validate, and mark documentation.
2. Register in subparsers, a process that is crucial for integrating new commands into the existing CLI structure, similar to how commands are structured in the aforementioned code.
3. Add tests to ensure the new command functions correctly within the CLI, following the robust testing practices that support the functionality seen in `defrag/cli.py:214-300`.
4. Update README.md usage section to reflect the new command, ensuring users understand how to utilize it, much like the comprehensive documentation provided for existing commands in the CLI.
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
