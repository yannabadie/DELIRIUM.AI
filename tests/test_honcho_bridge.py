import importlib
import sys


def _clear_modules(*module_names: str) -> None:
    for module_name in module_names:
        sys.modules.pop(module_name, None)


def test_honcho_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HONCHO_ENABLED", raising=False)
    _clear_modules("src.config", "src.honcho_bridge")

    try:
        config = importlib.import_module("src.config")
    finally:
        _clear_modules("src.config", "src.honcho_bridge")

    assert config.HONCHO_ENABLED is False
