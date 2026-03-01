import json

from openai import OpenAI

from infrastructure.env_loader import require_float, require_str
from infrastructure.paths import BACKEND_ROOT

_api_key = require_str("OPENAI_API_KEY")
_default_model = require_str("OPENAI_MODEL")
_default_temperature = require_float("OPENAI_TEMPERATURE")
_guardrails_config = BACKEND_ROOT / "prompts" / "guardrails_config.json"

# Set on first _get_client() call, or patched by tests. No guardrails import at module load.
client = None


def _get_client():
    global client
    if client is not None:
        return client
    if _guardrails_config.exists():
        from guardrails import GuardrailsOpenAI
        client = GuardrailsOpenAI(api_key=_api_key, config=_guardrails_config)  # noqa: PLW0603
    else:
        client = OpenAI(api_key=_api_key)  # noqa: PLW0603
    return client


def is_llm_available() -> bool:
    return True


def call_llm(
    messages: list[dict],
    model: str | None = None,
    temperature: float | None = None,
) -> str:
    model = model if model is not None else _default_model
    temperature = temperature if temperature is not None else _default_temperature
    response = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


def call_llm_json(
    messages: list[dict],
    model: str | None = None,
    temperature: float | None = None,
) -> dict:
    raw = call_llm(messages, model=model, temperature=temperature)
    return json.loads(raw)
