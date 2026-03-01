import pytest

from infrastructure.env_loader import (
    EnvMissingError,
    get_float,
    get_str,
    optional_path,
    require_float,
    require_path,
    require_str,
)


def test_get_str_missing_returns_default():
    assert get_str("_MISSING_KEY_") is None
    assert get_str("_MISSING_KEY_", default="x") == "x"


def test_get_str_set_returns_value(monkeypatch):
    monkeypatch.setenv("TEST_ENV_VAR", "value")
    assert get_str("TEST_ENV_VAR") == "value"


def test_get_str_empty_returns_default(monkeypatch):
    monkeypatch.setenv("TEST_EMPTY", "")
    assert get_str("TEST_EMPTY") is None
    assert get_str("TEST_EMPTY", default="d") == "d"


def test_get_float_missing_returns_default():
    assert get_float("_MISSING_KEY_") is None
    assert get_float("_MISSING_KEY_", default=0.5) == 0.5


def test_get_float_set_returns_value(monkeypatch):
    monkeypatch.setenv("TEST_FLOAT", "0.2")
    assert get_float("TEST_FLOAT") == 0.2


def test_get_float_empty_returns_default(monkeypatch):
    monkeypatch.setenv("TEST_EMPTY_FLOAT", "")
    assert get_float("TEST_EMPTY_FLOAT") is None
    assert get_float("TEST_EMPTY_FLOAT", default=0.0) == 0.0


def test_get_float_invalid_returns_default(monkeypatch):
    monkeypatch.setenv("TEST_BAD_FLOAT", "not-a-number")
    assert get_float("TEST_BAD_FLOAT") is None
    assert get_float("TEST_BAD_FLOAT", default=0.1) == 0.1


def test_optional_path_missing_returns_default():
    assert optional_path("_MISSING_PATH_") is None
    assert optional_path("_MISSING_PATH_", default=None) is None


def test_optional_path_set_returns_resolved_path(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_PATH_VAR", str(tmp_path))
    result = optional_path("TEST_PATH_VAR")
    assert result is not None
    assert result == tmp_path.resolve()


def test_optional_path_empty_returns_default(monkeypatch):
    monkeypatch.setenv("TEST_EMPTY_PATH", "")
    assert optional_path("TEST_EMPTY_PATH") is None


def test_require_str_missing_raises(monkeypatch):
    monkeypatch.delenv("_REQUIRE_MISSING_", raising=False)
    with pytest.raises(EnvMissingError) as exc_info:
        require_str("_REQUIRE_MISSING_")
    assert exc_info.value.key == "_REQUIRE_MISSING_"
    assert "missing or empty" in str(exc_info.value)


def test_require_str_empty_raises(monkeypatch):
    monkeypatch.setenv("_REQUIRE_EMPTY_", "")
    with pytest.raises(EnvMissingError) as exc_info:
        require_str("_REQUIRE_EMPTY_")
    assert exc_info.value.key == "_REQUIRE_EMPTY_"


def test_require_str_set_returns_value(monkeypatch):
    monkeypatch.setenv("_REQUIRE_SET_", "x")
    assert require_str("_REQUIRE_SET_") == "x"


def test_require_float_missing_raises(monkeypatch):
    monkeypatch.delenv("_REQUIRE_FLOAT_MISSING_", raising=False)
    with pytest.raises(EnvMissingError) as exc_info:
        require_float("_REQUIRE_FLOAT_MISSING_")
    assert exc_info.value.key == "_REQUIRE_FLOAT_MISSING_"


def test_require_float_invalid_raises(monkeypatch):
    monkeypatch.setenv("_REQUIRE_FLOAT_BAD_", "x")
    with pytest.raises(EnvMissingError) as exc_info:
        require_float("_REQUIRE_FLOAT_BAD_")
    assert "not a valid number" in str(exc_info.value)


def test_require_float_set_returns_value(monkeypatch):
    monkeypatch.setenv("_REQUIRE_FLOAT_SET_", "0.5")
    assert require_float("_REQUIRE_FLOAT_SET_") == 0.5


def test_require_path_missing_raises(monkeypatch):
    monkeypatch.delenv("_REQUIRE_PATH_MISSING_", raising=False)
    with pytest.raises(EnvMissingError) as exc_info:
        require_path("_REQUIRE_PATH_MISSING_")
    assert exc_info.value.key == "_REQUIRE_PATH_MISSING_"


def test_require_path_set_returns_resolved(tmp_path, monkeypatch):
    monkeypatch.setenv("_REQUIRE_PATH_SET_", str(tmp_path))
    assert require_path("_REQUIRE_PATH_SET_") == tmp_path.resolve()
