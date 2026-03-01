from pathlib import Path

from infrastructure.paths import BACKEND_ROOT, PROJECT_ROOT, evals_fixture_path


def test_backend_root_exists_and_is_directory():
    assert BACKEND_ROOT.is_dir()
    assert (BACKEND_ROOT / "domain").is_dir()
    assert (BACKEND_ROOT / "infrastructure").is_dir()


def test_project_root_exists():
    assert PROJECT_ROOT.is_dir()
    assert PROJECT_ROOT == BACKEND_ROOT.parent


def test_evals_fixture_path_returns_path_under_evals_fixtures():
    p = evals_fixture_path("source_overrides.json")
    assert p == BACKEND_ROOT / "evals" / "fixtures" / "source_overrides.json"
    assert p.suffix == ".json"


def test_evals_fixture_path_accepts_any_filename():
    p = evals_fixture_path("gold.json")
    assert p.name == "gold.json"
    assert p.parent.name == "fixtures"
    assert p.parent.parent.name == "evals"
