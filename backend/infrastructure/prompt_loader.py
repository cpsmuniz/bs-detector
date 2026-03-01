from __future__ import annotations

import yaml
from jinja2 import Environment, FileSystemLoader

from infrastructure.paths import BACKEND_ROOT

_PROMPTS_DIR = BACKEND_ROOT / "prompts"
_CONTRACT_PATH = _PROMPTS_DIR / "contract.yaml"

_raw_contract: dict | None = None
_env: Environment | None = None


def _load_contract() -> dict:
    global _raw_contract
    if _raw_contract is None:
        with open(_CONTRACT_PATH) as f:
            _raw_contract = yaml.safe_load(f) or {}
    return _raw_contract


def get_contract() -> dict:
    data = _load_contract()
    keys = data.get("output_keys") or {}
    fields = data.get("fields") or {}
    schemas = data.get("schemas") or {}
    flat = {**keys, **fields}
    flat["_schemas"] = schemas
    return flat


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)), autoescape=False)
    return _env


def render(template_name: str, **context: object) -> str:
    env = _get_env()
    template = env.get_template(template_name if template_name.endswith(".j2") else f"{template_name}.j2")
    return template.render(**context)
