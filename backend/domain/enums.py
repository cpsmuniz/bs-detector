from __future__ import annotations

from enum import Enum


class RetrievalStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"
    DISABLED = "disabled"
