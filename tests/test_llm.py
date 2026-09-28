"""Validate model configuration without developer secrets or API calls."""

import pytest
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from llm import get_model


@pytest.fixture(autouse=True)
def model_environment(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    for prefix in ("DEEPSEEK", "OPENAI"):
        monkeypatch.setenv(f"{prefix}_API_KEY", "offline-placeholder")
        monkeypatch.setenv(f"{prefix}_MODEL", "offline-model")
        monkeypatch.setenv(f"{prefix}_BASE_URL", "https://example.invalid/v1")


def test_get_model_defaults_to_deepseek(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    model = get_model()
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "deepseek-chat"
    assert model.temperature == 0
    assert model.openai_api_base == "https://example.invalid/v1"
    assert model.openai_api_key.get_secret_value() == "offline-placeholder"
    assert model.use_responses_api is False


def test_openai_provider_remains_supported(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", " OpenAI ")
    assert get_model().model_name == "offline-model"


def test_deepseek_disables_thinking_for_forced_structured_tools(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    assert get_model().extra_body == {"thinking": {"type": "disabled"}}


def test_openai_does_not_receive_deepseek_options(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert not get_model().extra_body


@pytest.mark.parametrize("provider", ["deepseek", "openai"])
@pytest.mark.parametrize("suffix", ["API_KEY", "MODEL", "BASE_URL"])
def test_missing_configuration_names_variable_without_exposing_secret(monkeypatch, provider, suffix):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    variable = f"{provider.upper()}_{suffix}"
    monkeypatch.setenv(variable, " ")
    with pytest.raises(ValueError, match=variable) as error:
        get_model()
    assert "offline-placeholder" not in str(error.value)


def test_unsupported_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        get_model()


def test_model_supports_tools_and_structured_output():
    class Answer(BaseModel):
        answer: str

    model = get_model()
    assert model.bind_tools([Answer]).kwargs["tools"][0]["function"]["name"] == "Answer"
    assert callable(model.with_structured_output(Answer, method="function_calling").invoke)
