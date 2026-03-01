from pathlib import Path

from infrastructure.env_loader import require_path

DOCS_DIR = require_path("DOCS_DIR")


def load_case_docs(docs_dir: Path | None = None) -> dict[str, str]:
    target = docs_dir or DOCS_DIR
    out: dict[str, str] = {}
    for path in sorted(target.glob("*.txt")):
        out[path.stem] = path.read_text()
    return out
