from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


def evals_fixture_path(filename: str) -> Path:
    return BACKEND_ROOT / "evals" / "fixtures" / filename
