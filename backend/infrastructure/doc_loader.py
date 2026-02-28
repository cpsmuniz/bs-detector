import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "documents"
DOCS_DIR = Path(os.environ["DOCS_DIR"]).resolve() if os.environ.get("DOCS_DIR") else _DEFAULT_DOCS_DIR


def load_case_docs(docs_dir: Path | None = None) -> dict[str, str]:
    target = docs_dir or DOCS_DIR
    out: dict[str, str] = {}
    for path in sorted(target.glob("*.txt")):
        out[path.stem] = path.read_text()
    return out
