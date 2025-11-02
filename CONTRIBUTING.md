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
# export ANTHROPIC_API_KEY=your_key_here       # Anthropic Claude

When setting up your API key for testing, the LLM client implemented in `defrag/llm.py`
selects OpenAI by default and falls back to Anthropic when `DEFRAG_LLM_PROVIDER` is
overridden. The client handles semantic analysis prompts and requires a valid key for
the chosen provider.

See `tests/integration/test_semantic_pipeline.py:35-37` - This section explains how the
tests check for provider credentials before running.

See `tests/integration/test_autodoc_generation.py:18-26` - This section explains how
integration tests skip when provider keys are absent, matching the client behaviour.

See `tests/unit/test_llm_client.py:55-65` - This section verifies that OpenAI is the
default provider and demonstrates how environment variables control provider selection.

See `defrag/llm.py:79-89` - The code initializes the provider and highlights the need to
set the appropriate API key.

## Running Tests


See `tests/integration/test_semantic_pipeline.py:35-37` - This section details the setup and initialization process for OpenAI models, which is relevant to checking for API credentials for LLM providers.

See `tests/integration/test_autodoc_generation.py:18-26` - This section details the setup and initialization process for API keys when running tests with OpenAI models, which is directly related to the code's functionality of skipping tests if the API key is not set.

See `tests/integration/test_intelligent_doc_merging.py:18-26` - This section details the setup and initialization process for API keys when running tests with OpenAI models, which is directly relevant to the code's functionality of checking for an API key for testing purposes.

See `tests/integration/test_intelligent_discovery_integration.py:25-286` - The code concept mentions the necessity of an API key for running tests with a language model, which is similar to the documentation about configuring API keys for OpenAI models.

See `tests/unit/test_llm_client.py:13-20` - The code concept involves clearing environment variables related to LLM providers before tests, which aligns with the documentation on configuring API keys for OpenAI models for testing.

See `tests/unit/test_llm_client.py:68-79` - This section explains the importance of correctly configuring API keys for running tests with OpenAI models, which aligns with the code concept of configuring defaults based on environment variables for the LLMClient using OpenAI.

See `tests/unit/test_llm_client.py:145-153` - This section explains the importance of correctly configuring API keys for running tests, which aligns with the code concept of testing error handling when an API key is missing.

See `tests/unit/test_llm_client.py:48-49` - The code concept involves sending prompts to a language model, which aligns with the need for correctly configuring API keys for OpenAI models as described in this section.

See `defrag/llm.py:849-906` - The documentation explains the importance of correctly configuring API keys for running tests with OpenAI models, which aligns with the code's purpose of interacting with OpenAI models.

See `defrag/llm.py:854-866` - This section explains the importance of correctly configuring API keys for running tests with OpenAI models, detailing the setup and initialization process in the code.

See `defrag/llm.py:91-93` - The code concept of sending a prompt to a provider and receiving a response is related to configuring API keys for OpenAI models.

See `defrag/autodoc.py:22-24` - The code concept involves initializing an object with a language model client, which aligns with the documentation's focus on setting up and initializing API keys for OpenAI models.

See `examples/icegraph_demo.py:25-197` - The code concept mentions using a provider and API key for semantic analysis, which is related to the documentation on configuring API keys for OpenAI models.
When setting up your environment for running tests, it's crucial to configure your API keys correctly. For OpenAI, this involves setting the `OPENAI_API_KEY` environment variable, as detailed in the documentation. This setup is essential for initializing an OpenAI client, as seen in `defrag/llm.py:816-828`, where the client is initialized with a specified model and API key. The process of interacting with OpenAI models, which requires this API key for authentication, is further handled by the class defined in `defrag/llm.py:811-868`. Additionally, the broader context of interacting with large language models (LLMs) from various providers, including OpenAI, is implemented in `defrag/llm.py:17-783`, where environment variables for API keys are a key consideration. Finally, the initialization of a client for the 'openai' provider, which aligns with setting this environment variable, is addressed in `defrag/llm.py:79-89`.
# Run all tests
pytest

See `tests/integration/test_intelligent_doc_merging.py:30-502` - The code concept involves testing using pytest, which aligns with the documentation on running tests using the pytest framework.

See `tests/unit/test_llm_client.py:176-188` - The code concept involves testing a method, which aligns with the section on running tests using pytest.

# With coverage
pytest --cov=defrag --cov-report=html

# Run specific test
To ensure the robustness of our semantic models, we run targeted tests such as `pytest tests/unit/test_semantic_models.py::TestConcept::test_concept_creation`. This test specifically examines the creation of concepts, a process intricately handled by the class implemented in `defrag/semantic.py:16-54`. This class is responsible for representing and managing semantic concepts extracted from documents or code, allowing seamless conversion between object and dictionary forms.


See `tests/integration/test_autodoc_generation.py:30-288` - The code concept involves testing the generation of documentation, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/integration/test_autodoc_generation.py:119-154` - The code concept involves testing the generation of conceptual documentation using semantic analysis, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/integration/test_autodoc_generation.py:156-189` - The code concept involves testing semantic clustering, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/integration/test_autodoc_generation.py:191-237` - The code concept involves testing documentation generation, which aligns with running a specific test to verify semantic concepts.

See `tests/integration/test_autodoc_generation.py:239-288` - The code concept involves testing a semantic analysis tool's respect for a confidence threshold, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/integration/test_intelligent_doc_merging.py:30-502` - The documentation describes running a test to verify semantic concepts, which aligns with the code's purpose of testing intelligent document merging using a semantic index.

See `tests/integration/test_intelligent_doc_merging.py:34-170` - The documentation describes running a specific test to verify the creation of semantic concepts, which aligns with the code concept of creating a semantic index with associated concepts for testing.

See `tests/integration/test_intelligent_doc_merging.py:224-282` - The code concept involves testing a fallback mechanism, which aligns with running a specific test to verify a feature.

See `tests/integration/test_intelligent_doc_merging.py:400-502` - The code concept involves testing the integration of multiple code references within a documentation section using a semantic index, which aligns with the documentation's focus on verifying the creation of semantic concepts through testing.

See `tests/unit/test_semantic_models.py:12-52` - The documentation describes running a specific test to verify the creation of semantic concepts, which aligns with the code concept of testing the creation and serialization of a Concept data model.

See `tests/unit/test_semantic_models.py:56-115` - This section explains how to run a specific test to verify the creation of semantic concepts using a targeted unit test, which aligns with the code concept of defining unit tests for the ConceptMatch data model.

See `tests/unit/test_semantic_models.py:119-224` - This section explains how to run a specific test to verify the creation of semantic concepts using a targeted unit test, which aligns with the code concept of unit tests for the SemanticIndex data structure.

See `tests/unit/test_semantic_models.py:15-30` - The documentation specifically explains how to run a test to verify the creation of semantic concepts, which aligns with the code concept of testing the creation of a Concept object with specific attributes and verifying its properties.

See `tests/unit/test_semantic_models.py:32-52` - The documentation describes a unit test for verifying the creation of semantic concepts, which aligns with the code concept of testing serialization and deserialization of a Concept object. Both involve testing the handling of Concept objects.

See `tests/unit/test_semantic_models.py:59-73` - The code concept involves testing the creation of a ConceptMatch object and verifying its properties, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/unit/test_semantic_models.py:75-92` - The code concept involves testing and refining concept matches, which aligns with running specific tests to verify semantic concepts.

See `tests/unit/test_semantic_models.py:122-126` - The code concept involves testing the creation of a semantic index, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/unit/test_semantic_models.py:128-155` - The code concept involves testing the functionality of adding and retrieving concepts in a semantic index, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/unit/test_semantic_models.py:157-166` - The documentation describes running a specific test to verify the creation of semantic concepts, which aligns with the code concept of testing the functionality of adding a concept match to a semantic index.

See `tests/unit/test_semantic_models.py:168-195` - The code concept involves testing the filtering of document concepts from a semantic index, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/unit/test_semantic_models.py:197-224` - The code concept involves testing the functionality of filtering and retrieving code-related concepts from a semantic index, which aligns with running a specific test to verify the creation of semantic concepts.

See `tests/unit/test_scanner.py:40-82` - The section explains running a specific test to verify creation of semantic concepts, which aligns with testing the IntelligentScanner's categorization capabilities.

See `tests/unit/test_llm_client.py:121-142` - The test verifies concept matching, which aligns with running a specific test to verify semantic concepts.
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

See `tests/test_intelligent_scanner.py:13-105` - The code concept involves handling and categorizing files within a directory structure, which aligns with the documentation outlining the directory structure and purpose of each component within the 'defrag' project.

See `tests/test_intelligent_scanner.py:160-270` - The code concept involves analyzing a project structure, which aligns with the documentation outlining the directory structure and purpose of each component within the 'defrag' project.

See `tests/test_intelligent_scanner.py:46-87` - The code concept involves directory scanning and project structure, which aligns with the documentation outlining the directory structure and purpose of each component within the 'defrag' project.

See `tests/test_intelligent_scanner.py:204-256` - The code concept involves intelligent scanning and categorization of files and directories, which aligns with the documentation outlining the directory structure and purpose of each component within the 'defrag' project.

See `defrag/intelligent_scanner.py:218-239` - The code concept involves directory structure, which aligns with the documentation outlining the directory structure and purpose of each component within the 'defrag' project.

## Adding Features

### New Semantic Analysis Feature

1. Add logic to `semantic.py` or `analyzer.py`, as seen in `defrag/semantic.py:16-54`, where a class is defined for representing and managing semantic concepts extracted from documents or code. This implementation allows for conversion between object and dictionary forms, which is crucial for the new feature.
2. Update `SemanticIndex` model if needed to ensure it aligns with the new logic and supports the conversion processes handled by the class in `defrag/semantic.py:16-54`.
3. Add tests in `tests/unit` or `tests/integration` as appropriate to verify the functionality and integration of the new semantic analysis feature, ensuring that the conversion between object and dictionary forms is thoroughly tested.

See `tests/integration/test_autodoc_generation.py:119-154` - The code concept involves semantic analysis and language models, which relates to managing semantic concepts in a semantic analysis tool.

See `tests/integration/test_autodoc_generation.py:156-189` - The documentation describes the implementation and testing of a feature related to managing semantic concepts, which aligns closely with the code's focus on semantic clustering and analysis of undocumented code.

See `tests/integration/test_intelligent_doc_merging.py:34-170` - The documentation outlines the implementation and testing of a feature for managing semantic concepts, which is relevant to the code concept of creating a semantic index with associated concepts.

See `tests/integration/test_intelligent_doc_merging.py:400-502` - The code concept involves testing the integration of code references within documentation using a semantic index, which aligns with the documentation section that outlines the implementation and testing of managing semantic concepts. Both involve semantic analysis and testing, indicating a strong match.

See `tests/unit/test_semantic_models.py:12-52` - The documentation outlines the implementation and testing of a feature for managing semantic concepts, which is relevant to the code concept of testing a Concept data model.

See `tests/unit/test_semantic_models.py:56-115` - The documentation describes the implementation and testing of a feature related to semantic concepts, which aligns with the code's focus on unit tests for the ConceptMatch data model, including its creation, context handling, and serialization.

See `tests/unit/test_semantic_models.py:119-224` - This section outlines the implementation and testing of a new feature for managing semantic concepts, which is relevant to the code concept of testing the SemanticIndex data structure.

See `tests/unit/test_semantic_models.py:15-30` - The documentation outlines the implementation and testing of a feature for managing semantic concepts, which is relevant to the code concept of testing a Concept object.

See `tests/unit/test_semantic_models.py:32-52` - This section outlines the implementation and testing of a new feature for managing semantic concepts with object-dictionary conversion, which directly relates to the code concept of testing serialization and deserialization of a Concept object.

See `tests/unit/test_semantic_models.py:59-73` - The code concept involves testing the creation and verification of a ConceptMatch object, which aligns with the documentation's focus on managing semantic concepts and object-dictionary conversion. This suggests a strong connection between the code and the documentation.

See `tests/unit/test_semantic_models.py:75-92` - The code concept involves testing and refining semantic concept matches, which aligns with the documentation's focus on managing semantic concepts and testing new features related to semantic analysis.

See `tests/unit/test_semantic_models.py:94-115` - The section outlines the implementation and testing of a new feature for managing semantic concepts with object-dictionary conversion, which aligns with the code concept of testing serialization and deserialization of a ConceptMatch object.

See `tests/unit/test_semantic_models.py:128-155` - The code concept of adding and retrieving concepts in a semantic index is related to managing semantic concepts with object-dictionary conversion in a semantic analysis tool.

See `tests/unit/test_semantic_models.py:157-166` - The code concept involves testing the addition of concept matches to a semantic index, which aligns with the documentation's focus on managing semantic concepts. The keywords 'semantic index' and 'concept match' are directly relevant to the documentation's description of semantic analysis tools.

See `tests/unit/test_semantic_models.py:168-195` - The documentation section describes the implementation and testing of a feature related to managing semantic concepts, which aligns closely with the code concept of testing the filtering of document concepts from a semantic index.

See `defrag/schema.py:68-74` - The documentation outlines the implementation and testing of a feature for managing semantic concepts with object-dictionary conversion, which aligns with the code's functionality of converting an object into a dictionary format for YAML serialization.

See `defrag/schema.py:77-87` - The documentation outlines the implementation and testing of a feature for managing semantic concepts with object-dictionary conversion, which aligns with the code concept of creating a DefragIndex object from a dictionary.

See `defrag/refiner.py:95-234` - The section outlines the implementation and testing of a new feature for managing semantic concepts, which aligns with the code's focus on refining semantic matches using a language model.

See `defrag/analyzer.py:24-373` - The section outlines the implementation and testing of a new feature for managing semantic concepts, which aligns with the code's purpose of semantic analysis and concept extraction using a language model.

See `defrag/llm.py:413-447` - The section outlines the implementation and testing of a feature for managing semantic concepts, which aligns with the code's purpose of extracting semantic concepts from documentation.

See `defrag/autodoc.py:70-155` - The documentation outlines the implementation and testing of a new feature for managing semantic concepts, which aligns with the code's purpose of clustering undocumented concepts based on their semantic meaning.

See `defrag/autodoc.py:255-353` - The section outlines the implementation and testing of a new feature for managing semantic concepts, which aligns with the purpose of '_force_semantic_grouping' to ensure logical grouping.

See `defrag/autodoc.py:551-598` - The section outlines the implementation and testing of a new feature for managing semantic concepts, which aligns with the code's focus on generating documentation for semantic clusters.

See `defrag/semantic.py:58-95` - The documentation outlines the implementation and testing of a feature for managing semantic concepts with object-dictionary conversion, which aligns with the code concept of managing relationships between code and documentation concepts and converting them to/from dictionary representations.

See `defrag/semantic.py:99-178` - The documentation outlines the implementation and testing of a feature for managing semantic concepts, which aligns with the code's purpose of managing and querying a semantic index of concepts.

See `defrag/semantic.py:150-155` - The documentation outlines the implementation and testing of a feature for managing semantic concepts with object-dictionary conversion, which aligns with the code concept of converting an object containing concepts and matches into a dictionary format.

See `defrag/semantic.py:158-165` - This section outlines the implementation and testing of a new feature for managing semantic concepts with object-dictionary conversion in a semantic analysis tool, which aligns with the code concept of constructing a SemanticIndex object from a dictionary.

See `defrag/semantic.py:105-107` - The section outlines the implementation and testing of a new feature for managing semantic concepts with object-dictionary conversion, which aligns with the code concept of adding or updating concepts in a dictionary.
4. Update `docs/SEMANTIC.md` to reflect the changes and enhancements made, including the new capabilities for managing semantic concepts as implemented in `defrag/semantic.py:16-54`.
### New CLI Command

1. Add command function in `cli.py` or `semantic_cli.py`, as seen in the implementation of the command-line interface for a documentation defragmentation tool in `defrag/cli.py:214-300`, which includes commands to index, scan, validate, and mark documentation.
2. Register in subparsers, a process that is crucial for integrating new commands into the existing CLI structure, similar to how commands are structured in the aforementioned code.
3. Add tests to ensure the new command functions correctly within the CLI, following the robust testing practices that support the functionality seen in `defrag/cli.py:214-300`.

See `defrag/fixer.py:707-741` - The code concept involves writing documentation files with options for dry run and verbose output, which aligns with adding a new command to a CLI for documentation management.

See `defrag/semantic_cli.py:394-490` - This section explains the steps to add a new command to a command-line interface, which aligns with the code concept of adding semantic analysis-related commands to a CLI using argparse.

See `examples/icegraph_demo.py:200-236` - This section explains how to add a new command to a command-line interface, which aligns with setting up a CLI for a demo.
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

See `tests/integration/test_semantic_pipeline.py:18-29` - The documentation outlines best practices for testing new features, including the use of fixtures, which aligns with the code concept of creating a temporary directory and fixture codebase for testing.

See `tests/unit/test_scanner.py:40-82` - The code concept involves unit testing the IntelligentScanner, which aligns with the documentation's focus on testing new features and maintaining high test coverage. The use of mocking and categorization of Python files are consistent with best practices in testing.

See `tests/unit/test_depth_limit.py:12-74` - The documentation section outlines best practices for testing new features, which aligns with the code concept of testing a directory scanning function with a depth limit using mocking and unit tests. This indicates that the documentation is relevant to the code's implementation.

See `tests/unit/test_llm_client.py:34-52` - The documentation section outlines best practices for testing, which aligns with the code concept of creating a stub client-provider pair for testing purposes. The use of stubs and mocks is a common practice in testing to simulate components without actual implementation.

See `tests/unit/test_llm_client.py:176-188` - The code concept involves testing a method for JSON parsing and validation, which aligns with the documentation's focus on testing new features and maintaining high test coverage. The use of fixtures mentioned in the documentation is relevant to the context of unit testing, which is part of the code concept.

## Documentation

- Update README.md for user-facing changes
- Update SEMANTIC.md for semantic layer changes
- Add docstrings to all public functions
- Include examples in docstrings

See `defrag/autodoc.py:600-679` - The code concept involves writing documentation to files, which aligns with updating documentation as described in this section.

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
