from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict

import pytest

pytest.importorskip("agent.web_search_provider")


class FakeContext:
    def __init__(self) -> None:
        self.settings: Dict[str, Any] = {}
        self.provider = None

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def register_web_search_provider(self, provider: Any) -> None:
        self.provider = provider


def test_register_uses_public_web_provider_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin_parent = str(Path(__file__).resolve().parents[1].parent)
    monkeypatch.syspath_prepend(plugin_parent)
    plugin = importlib.import_module("jina")

    context = FakeContext()
    context.settings["browser_engine"] = "browser"
    plugin.register(context)

    assert context.provider is not None
    assert context.provider.name == "jina"
    assert context.provider.supports_extract() is True
    assert context.provider.supports_search() is False
    assert context.provider.settings.browser_engine == "browser"
