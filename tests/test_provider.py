from __future__ import annotations

import random
from typing import Any, Dict

import pytest

pytest.importorskip("agent.web_search_provider")

from provider import JinaSettings, JinaWebSearchProvider


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200, text: str = "") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> Any:
        return self._payload


def test_default_settings_are_keyless_reader_defaults() -> None:
    settings = JinaSettings.from_mapping({})
    assert settings.timeout == 20
    assert settings.browser_engine == "default"
    assert settings.user_agent_mode == "random"
    assert settings.with_generated_alt is False


def test_settings_are_clamped_and_invalid_values_fall_back() -> None:
    settings = JinaSettings.from_mapping(
        {
            "timeout": 999,
            "browser_engine": "unsupported",
            "user_agent_mode": "unsupported",
            "cache_tolerance": -10,
            "user_agents": [],
        }
    )
    assert settings.timeout == 180
    assert settings.browser_engine == "default"
    assert settings.user_agent_mode == "random"
    assert settings.cache_tolerance is None
    assert settings.user_agents


def test_extract_normalizes_jina_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: Dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.update(url=url, **kwargs)
        return FakeResponse(
            {
                "code": 200,
                "status": 20000,
                "data": {
                    "title": "Example",
                    "url": "https://example.com/",
                    "content": "# Example\n\nBody",
                    "metadata": {"lang": "en"},
                    "httpStatus": 200,
                },
            }
        )

    monkeypatch.setattr("provider.httpx.get", fake_get)
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")

    result = JinaWebSearchProvider().extract(["https://example.com"])

    assert result == [
        {
            "url": "https://example.com/",
            "title": "Example",
            "content": "# Example\n\nBody",
            "raw_content": "# Example\n\nBody",
            "metadata": {"lang": "en", "httpStatus": 200},
        }
    ]
    assert calls["url"] == "https://r.jina.ai/https://example.com"
    assert calls["headers"]["Accept"] == "application/json"
    assert "Authorization" not in calls["headers"]
    assert calls["timeout"] == 25
    assert calls["follow_redirects"] is True


@pytest.mark.parametrize(
    ("requested_format", "expected_response_format"),
    [("html", "html"), ("markdown", "markdown")],
)
def test_extract_maps_content_format_without_changing_json_transport(
    monkeypatch: pytest.MonkeyPatch,
    requested_format: str,
    expected_response_format: str,
) -> None:
    calls: Dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.update(url=url, **kwargs)
        return FakeResponse({"data": {"content": "body"}})

    monkeypatch.setattr("provider.httpx.get", fake_get)
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")

    JinaWebSearchProvider().extract(
        ["https://example.com"], format=requested_format
    )

    assert calls["headers"]["Accept"] == "application/json"
    assert calls["headers"]["X-Respond-With"] == expected_response_format


def test_extract_uses_html_payload_for_html_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: Dict[str, Any] = {}
    html = "<html><body>Reader HTML</body></html>"

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.update(url=url, **kwargs)
        return FakeResponse({"data": {"html": html}})

    monkeypatch.setattr("provider.httpx.get", fake_get)
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")

    result = JinaWebSearchProvider().extract(
        ["https://example.com"], format="html"
    )[0]

    assert calls["headers"]["X-Respond-With"] == "html"
    assert result["content"] == html
    assert result["raw_content"] == html


def test_extract_sends_reader_timeout_and_transport_grace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: Dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.update(url=url, **kwargs)
        return FakeResponse({"data": {"content": "body"}})

    monkeypatch.setattr("provider.httpx.get", fake_get)
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")

    JinaWebSearchProvider({"timeout": 20}).extract(["https://example.com"])

    assert calls["headers"]["X-Timeout"] == "20"
    assert calls["timeout"] == 25


def test_headers_cover_browser_wait_proxy_and_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "JINA_API_KEY": "key-value",
        "JINA_SOCKS5_PROXY": "socks5://proxy.example:1080",
        "JINA_HTTP_PROXY": "",
    }
    monkeypatch.setattr("provider.get_provider_env", lambda name: values.get(name, ""))
    provider = JinaWebSearchProvider(
        {
            "browser_engine": "browser",
            "wait_for": ".article",
            "target_selector": "main",
            "remove_selector": ".ads",
            "with_generated_alt": True,
            "no_cache": True,
            "cache_tolerance": 120,
            "user_agent_mode": "fixed",
            "user_agents": ["Test Browser/1.0"],
        }
    )

    headers = provider._headers()

    assert headers == {
        "Accept": "application/json",
        "Authorization": "Bearer key-value",
        "X-Proxy-Url": "socks5://proxy.example:1080",
        "X-Timeout": "20",
        "X-Engine": "browser",
        "X-Wait-For-Selector": ".article",
        "X-Target-Selector": "main",
        "X-Remove-Selector": ".ads",
        "X-With-Generated-Alt": "true",
        "X-No-Cache": "true",
        "X-Cache-Tolerance": "120",
        "X-User-Agent": "Test Browser/1.0",
    }


def test_direct_engine_is_compatible_alias_for_curl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")
    headers = JinaWebSearchProvider({"browser_engine": "direct"})._headers()
    assert headers["X-Engine"] == "curl"


def test_random_user_agent_is_stable_for_provider_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")
    provider = JinaWebSearchProvider(
        {"user_agents": ["Agent A", "Agent B"]},
        randomizer=random.Random(4),
    )
    first = provider._headers()["X-User-Agent"]
    second = provider._headers()["X-User-Agent"]
    assert first in {"Agent A", "Agent B"}
    assert second == first


def test_both_proxy_variables_return_a_per_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "JINA_SOCKS5_PROXY": "socks5://proxy.example:1080",
        "JINA_HTTP_PROXY": "http://proxy.example:8080",
    }
    monkeypatch.setattr("provider.get_provider_env", lambda name: values.get(name, ""))
    result = JinaWebSearchProvider().extract(["https://example.com"])
    assert result[0]["url"] == "https://example.com"
    assert "Set only one" in result[0]["error"]


def test_http_error_is_returned_per_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")
    monkeypatch.setattr(
        "provider.httpx.get",
        lambda *args, **kwargs: FakeResponse({}, status_code=429, text="rate limited"),
    )
    result = JinaWebSearchProvider().extract(["https://example.com"])
    assert result[0]["error"] == "Jina Reader returned HTTP 429: rate limited"


def test_provider_has_extract_only_capability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("provider.get_provider_env", lambda name: "")
    provider = JinaWebSearchProvider()
    assert provider.name == "jina"
    assert provider.supports_extract() is True
    assert provider.supports_search() is False
    assert provider.is_available() is False
    assert provider.is_keyless_available() is True


def test_provider_is_available_when_api_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("provider.get_provider_env", lambda name: "configured-key")
    assert JinaWebSearchProvider().is_available() is True


def test_setup_schema_exposes_optional_environment_variables() -> None:
    env_keys = {item["key"] for item in JinaWebSearchProvider().get_setup_schema()["env_vars"]}
    assert env_keys == {"JINA_API_KEY", "JINA_SOCKS5_PROXY", "JINA_HTTP_PROXY"}
