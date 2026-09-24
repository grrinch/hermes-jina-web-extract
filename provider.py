"""Jina Reader implementation for the Hermes web-extract provider contract."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import quote

import httpx

from agent.web_search_provider import WebSearchProvider, get_provider_env

logger = logging.getLogger(__name__)

_READER_BASE_URL = "https://r.jina.ai/"
_DEFAULT_USER_AGENTS = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) "
    "Gecko/20100101 Firefox/132.0",
)
_ALLOWED_ENGINES = {"default", "auto", "browser", "curl", "direct"}
_ALLOWED_UA_MODES = {"random", "fixed", "off"}


@dataclass(frozen=True)
class JinaSettings:
    """Validated plugin settings loaded from the profile config."""

    timeout: int = 20
    browser_engine: str = "default"
    wait_for: str = ""
    user_agent_mode: str = "random"
    user_agents: tuple[str, ...] = _DEFAULT_USER_AGENTS
    target_selector: str = ""
    remove_selector: str = ""
    with_generated_alt: bool = False
    no_cache: bool = False
    cache_tolerance: Optional[int] = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "JinaSettings":
        values = values or {}

        try:
            timeout = int(values.get("timeout", 20))
        except (TypeError, ValueError):
            timeout = 20
        timeout = max(1, min(timeout, 180))

        engine = str(values.get("browser_engine", "default") or "default").strip().lower()
        if engine not in _ALLOWED_ENGINES:
            logger.warning("Invalid Jina browser_engine=%r; using default", engine)
            engine = "default"

        ua_mode = str(values.get("user_agent_mode", "random") or "random").strip().lower()
        if ua_mode not in _ALLOWED_UA_MODES:
            logger.warning("Invalid Jina user_agent_mode=%r; using random", ua_mode)
            ua_mode = "random"

        configured_agents = values.get("user_agents", _DEFAULT_USER_AGENTS)
        if not isinstance(configured_agents, (list, tuple)):
            configured_agents = _DEFAULT_USER_AGENTS
        agents = tuple(
            str(agent).strip()[:512]
            for agent in configured_agents
            if str(agent).strip()
        )
        if not agents:
            agents = _DEFAULT_USER_AGENTS

        cache_tolerance: Optional[int]
        raw_tolerance = values.get("cache_tolerance", 0)
        try:
            cache_tolerance = int(raw_tolerance) if raw_tolerance else None
        except (TypeError, ValueError):
            cache_tolerance = None
        if cache_tolerance is not None:
            cache_tolerance = max(0, min(cache_tolerance, 86_400)) or None

        return cls(
            timeout=timeout,
            browser_engine=engine,
            wait_for=str(values.get("wait_for", "") or "").strip(),
            user_agent_mode=ua_mode,
            user_agents=agents,
            target_selector=str(values.get("target_selector", "") or "").strip(),
            remove_selector=str(values.get("remove_selector", "") or "").strip(),
            with_generated_alt=bool(values.get("with_generated_alt", False)),
            no_cache=bool(values.get("no_cache", False)),
            cache_tolerance=cache_tolerance,
        )


class JinaWebSearchProvider(WebSearchProvider):
    """Extract web pages with Jina Reader; this provider has no other capability."""

    def __init__(
        self,
        settings: Mapping[str, Any] | JinaSettings | None = None,
        *,
        randomizer: random.Random | None = None,
    ) -> None:
        self.settings = (
            settings
            if isinstance(settings, JinaSettings)
            else JinaSettings.from_mapping(settings)
        )
        self._randomizer = randomizer or random.SystemRandom()
        self._selected_user_agent: Optional[str] = None

    @staticmethod
    def config_defaults() -> Dict[str, Any]:
        return {
            "timeout": 20,
            "browser_engine": "default",
            "wait_for": "",
            "user_agent_mode": "random",
            "user_agents": list(_DEFAULT_USER_AGENTS),
            "target_selector": "",
            "remove_selector": "",
            "with_generated_alt": False,
            "no_cache": False,
            "cache_tolerance": 0,
        }

    @property
    def name(self) -> str:
        return "jina"

    @property
    def display_name(self) -> str:
        return "Jina Reader"

    def is_available(self) -> bool:
        """Reader extraction is available without credentials."""
        return True

    def is_keyless_available(self) -> bool:
        return True

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "keyless",
            "tag": "Reader extraction works without a key; a key raises limits.",
            "env_vars": [
                {
                    "key": "JINA_API_KEY",
                    "prompt": "Optional Jina API key",
                    "url": "https://jina.ai/reader",
                },
                {
                    "key": "JINA_SOCKS5_PROXY",
                    "prompt": "Optional Jina SOCKS5 upstream proxy URL",
                    "url": "https://github.com/jina-ai/reader",
                },
                {
                    "key": "JINA_HTTP_PROXY",
                    "prompt": "Optional Jina HTTP upstream proxy URL",
                    "url": "https://github.com/jina-ai/reader",
                },
            ],
        }

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Extract every URL and return one normalized result per input URL."""
        del kwargs  # The standalone plugin uses profile configuration for options.
        return [self._extract_one(str(url)) for url in urls]

    def _extract_one(self, source_url: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "url": source_url,
            "title": "",
            "content": "",
            "raw_content": "",
            "metadata": {},
        }
        if not source_url.strip():
            result["error"] = "URL is empty"
            return result

        try:
            response = httpx.get(
                self._reader_url(source_url),
                headers=self._headers(),
                timeout=self.settings.timeout,
                follow_redirects=True,
            )
            if response.status_code >= 400:
                raise ValueError(self._http_error(response))
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                raise ValueError("Jina response did not contain a data object")

            content = str(data.get("content") or "")
            metadata = dict(data.get("metadata") or {}) if isinstance(data.get("metadata"), dict) else {}
            for key in ("publishedTime", "warning", "httpStatus", "httpStatusText"):
                if key in data:
                    metadata[key] = data[key]

            result.update(
                {
                    "url": str(data.get("url") or source_url),
                    "title": str(data.get("title") or ""),
                    "content": content,
                    "raw_content": content,
                    "metadata": metadata,
                }
            )
        except Exception as exc:  # noqa: BLE001 - preserve per-URL contract
            result["error"] = self._safe_error(exc)
        return result

    @staticmethod
    def _reader_url(source_url: str) -> str:
        return _READER_BASE_URL + quote(source_url, safe=":/?&=#%")

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        api_key = get_provider_env("JINA_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        socks_proxy = get_provider_env("JINA_SOCKS5_PROXY")
        http_proxy = get_provider_env("JINA_HTTP_PROXY")
        if socks_proxy and http_proxy:
            raise ValueError("Set only one of JINA_SOCKS5_PROXY or JINA_HTTP_PROXY")
        if socks_proxy or http_proxy:
            headers["X-Proxy-Url"] = socks_proxy or http_proxy

        engine = "curl" if self.settings.browser_engine == "direct" else self.settings.browser_engine
        if engine != "default":
            headers["X-Engine"] = engine
        if self.settings.wait_for:
            headers["X-Wait-For-Selector"] = self.settings.wait_for
        if self.settings.target_selector:
            headers["X-Target-Selector"] = self.settings.target_selector
        if self.settings.remove_selector:
            headers["X-Remove-Selector"] = self.settings.remove_selector
        if self.settings.with_generated_alt:
            headers["X-With-Generated-Alt"] = "true"
        if self.settings.no_cache:
            headers["X-No-Cache"] = "true"
        if self.settings.cache_tolerance is not None:
            headers["X-Cache-Tolerance"] = str(self.settings.cache_tolerance)

        user_agent = self._user_agent()
        if user_agent:
            headers["X-User-Agent"] = user_agent
        return headers

    def _user_agent(self) -> Optional[str]:
        mode = self.settings.user_agent_mode
        if mode == "off":
            return None
        if self._selected_user_agent is None:
            if mode == "fixed":
                self._selected_user_agent = self.settings.user_agents[0]
            else:
                self._selected_user_agent = self._randomizer.choice(self.settings.user_agents)
        return self._selected_user_agent

    @staticmethod
    def _http_error(response: httpx.Response) -> str:
        detail = (response.text or "").strip().replace("\n", " ")
        if len(detail) > 300:
            detail = detail[:300] + "..."
        return f"Jina Reader returned HTTP {response.status_code}" + (f": {detail}" if detail else "")

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        text = str(exc).strip().replace("\n", " ")
        if not text:
            text = exc.__class__.__name__
        return text[:500]
