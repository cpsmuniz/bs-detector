import sys
from unittest.mock import MagicMock

from infrastructure import llm as llm_module


def test_is_llm_available_returns_true():
    assert llm_module.is_llm_available() is True


def test_call_llm_returns_message_content(monkeypatch):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"x": 1}'
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    monkeypatch.setattr(llm_module, "client", mock_client)
    out = llm_module.call_llm([{"role": "user", "content": "Hi"}])
    assert out == '{"x": 1}'


def test_call_llm_passes_model_and_temperature(monkeypatch):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    monkeypatch.setattr(llm_module, "client", mock_client)
    llm_module.call_llm([], model="gpt-5", temperature=0.5)
    mock_client.chat.completions.create.assert_called_once()
    call_kw = mock_client.chat.completions.create.call_args[1]
    assert call_kw["model"] == "gpt-5"
    assert call_kw["temperature"] == 0.5


def test_call_llm_uses_env_defaults_when_model_and_temperature_not_passed(monkeypatch):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    monkeypatch.setattr(llm_module, "client", mock_client)
    monkeypatch.setattr(llm_module, "_default_model", "gpt-4o-mini")
    monkeypatch.setattr(llm_module, "_default_temperature", 0.3)
    llm_module.call_llm([{"role": "user", "content": "Hi"}])
    mock_client.chat.completions.create.assert_called_once()
    call_kw = mock_client.chat.completions.create.call_args[1]
    assert call_kw["model"] == "gpt-4o-mini"
    assert call_kw["temperature"] == 0.3


def test_call_llm_json_returns_parsed_dict(monkeypatch):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"a": 1, "b": 2}'
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    monkeypatch.setattr(llm_module, "client", mock_client)
    out = llm_module.call_llm_json([{"role": "user", "content": "Hi"}])
    assert out == {"a": 1, "b": 2}


def test_get_client_uses_openai_when_config_missing(monkeypatch, tmp_path):
    """Covers the branch where guardrails_config.json does not exist: we use OpenAI()."""
    no_config = tmp_path / "nonexistent_guardrails_config.json"
    assert not no_config.exists()
    monkeypatch.setattr(llm_module, "client", None)
    monkeypatch.setattr(llm_module, "_guardrails_config", no_config)
    mock_openai_instance = MagicMock()
    monkeypatch.setattr(llm_module, "OpenAI", MagicMock(return_value=mock_openai_instance))
    got = llm_module._get_client()
    assert got is mock_openai_instance
    llm_module.OpenAI.assert_called_once_with(api_key=llm_module._api_key)


def test_get_client_uses_guardrails_when_config_exists(monkeypatch, tmp_path):
    """Covers the branch where guardrails_config.json exists; we mock guardrails so we don't load spacy."""
    config_file = tmp_path / "guardrails_config.json"
    config_file.write_text("{}")
    monkeypatch.setattr(llm_module, "client", None)
    monkeypatch.setattr(llm_module, "_guardrails_config", config_file)
    mock_guardrails = MagicMock()
    mock_client_instance = MagicMock()
    mock_guardrails.GuardrailsOpenAI.return_value = mock_client_instance
    with monkeypatch.context() as m:
        m.setitem(sys.modules, "guardrails", mock_guardrails)
        got = llm_module._get_client()
    assert got is mock_client_instance
    mock_guardrails.GuardrailsOpenAI.assert_called_once()
    assert llm_module.client is mock_client_instance
