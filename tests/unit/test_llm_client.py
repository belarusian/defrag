"""
Unit tests for LLMClient provider configuration and prompt handling.
"""

import types

import pytest

from defrag.llm import LLMClient


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    """Clear provider-related environment variables before each test."""
    for key in [
        LLMClient.PROVIDER_ENV_VAR,
        LLMClient.PROVIDER_KEY_ENVS["anthropic"],
        LLMClient.PROVIDER_KEY_ENVS["openai"],
    ]:
        monkeypatch.delenv(key, raising=False)


def stub_client():
    """Create a simple stub client with the methods LLMClient expects."""
    return types.SimpleNamespace(
        messages=types.SimpleNamespace(create=lambda *a, **k: None),
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda *a, **k: None)),
        responses=types.SimpleNamespace(
            create=lambda *a, **k: types.SimpleNamespace(output_text="")
        ),
    )


def make_stub_provider(send_return=""):
    """Return client/provider pair for patching _initialize_provider."""

    def _send(prompt, max_tokens):  # noqa: ARG001 - we don't use the parameters in tests
        if callable(send_return):
            return send_return()
        return send_return

    client = stub_client()

    class _StubProvider:
        def __init__(self):
            self.client = client

        def send_prompt(self, prompt, max_tokens):
            return _send(prompt, max_tokens)

    provider = _StubProvider()
    return client, provider


def test_llm_client_defaults_to_anthropic(monkeypatch):
    """Default provider should be Anthropic with corresponding model."""
    client_obj, provider = make_stub_provider()
    monkeypatch.setattr(LLMClient, "_initialize_provider", lambda self: (client_obj, provider))
    monkeypatch.setenv(LLMClient.PROVIDER_KEY_ENVS["anthropic"], "ant-key")

    client = LLMClient()

    assert client.provider == "anthropic"
    assert client.model == LLMClient.DEFAULT_MODELS["anthropic"]
    assert client.api_key == "ant-key"


def test_llm_client_selects_openai_from_env(monkeypatch):
    """Explicit provider via environment should configure OpenAI defaults."""
    client_obj, provider = make_stub_provider()
    monkeypatch.setattr(LLMClient, "_initialize_provider", lambda self: (client_obj, provider))
    monkeypatch.setenv(LLMClient.PROVIDER_ENV_VAR, "openai")
    monkeypatch.setenv(LLMClient.PROVIDER_KEY_ENVS["openai"], "openai-key")

    client = LLMClient()

    assert client.provider == "openai"
    assert client.model == LLMClient.DEFAULT_MODELS["openai"]
    assert client.api_key == "openai-key"


def test_llm_client_model_env_override(monkeypatch):
    """Model env var should override provider default."""
    client_obj, provider = make_stub_provider()
    monkeypatch.setattr(LLMClient, "_initialize_provider", lambda self: (client_obj, provider))
    monkeypatch.setenv(LLMClient.PROVIDER_ENV_VAR, "openai")
    monkeypatch.setenv(LLMClient.PROVIDER_KEY_ENVS["openai"], "openai-key")
    monkeypatch.setenv(LLMClient.MODEL_ENV_VAR, "gpt-4o")

    client = LLMClient()

    assert client.model == "gpt-4o"


def test_llm_client_requires_api_key(monkeypatch):
    """Missing API key for selected provider should raise an error."""
    client_obj, provider = make_stub_provider()
    monkeypatch.setattr(LLMClient, "_initialize_provider", lambda self: (client_obj, provider))

    with pytest.raises(ValueError) as exc:
        LLMClient(provider="openai", api_key=None)

    assert "OPENAI_API_KEY" in str(exc.value)


def test_extract_doc_concept_recovers_from_bad_json(monkeypatch):
    """The client should retry JSON parsing and fall back gracefully."""
    client_obj, provider = make_stub_provider()
    monkeypatch.setattr(LLMClient, "_initialize_provider", lambda self: (client_obj, provider))
    client = LLMClient(api_key="dummy", model="stub-model", provider="anthropic")

    responses = iter(
        [
            "not-a-json-response",
            '{"description": "Recovered", "keywords": ["ok"]}',
        ]
    )
    monkeypatch.setattr(client, "_send_prompt", lambda *args, **kwargs: next(responses))

    result = client.extract_doc_concept("Section", "Content here")

    assert result["description"] == "Recovered"
    assert result["keywords"] == ["ok"]
