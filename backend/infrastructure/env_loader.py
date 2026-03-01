from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class EnvMissingError(ValueError):
    def __init__(self, key: str, reason: str = "missing or empty") -> None:
        self.key = key
        self.reason = reason
        super().__init__(f"Required env {key!r} is {reason}")


def get_str(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    return value if value else default


def get_float(key: str, default: float | None = None) -> float | None:
    value = os.getenv(key)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def optional_path(key: str, default: Path | None = None) -> Path | None:
    value = os.getenv(key)
    if not value:
        return default
    return Path(value).resolve()


def require_str(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvMissingError(key)
    return value


def require_float(key: str) -> float:
    value = os.getenv(key)
    if not value:
        raise EnvMissingError(key)
    try:
        return float(value)
    except ValueError:
        raise EnvMissingError(key, "not a valid number")


def require_path(key: str) -> Path:
    value = os.getenv(key)
    if not value:
        raise EnvMissingError(key)
    return Path(value).resolve()
