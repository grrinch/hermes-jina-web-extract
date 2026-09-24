"""Jina Reader provider plugin for Hermes web_extract."""

from __future__ import annotations

from typing import Any, Dict

from .provider import JinaWebSearchProvider


def register(ctx) -> None:
    """Register the Jina Reader provider with Hermes."""
    settings: Dict[str, Any] = {}
    for key, default in JinaWebSearchProvider.config_defaults().items():
        settings[key] = ctx.get_config(key, default)
    ctx.register_web_search_provider(JinaWebSearchProvider(settings))
