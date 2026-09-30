# hermes-jina-web-extract

Standalone Hermes Agent plugin that uses Jina Reader to extract clean web content for `web_extract`.

Built by [Rad Paluszak](https://paluszak.me/) and [NON.agency](https://non.agency/) for Hermes Agent workflows.

## Bottom Line Up Front

`hermes-jina-web-extract` registers the `jina` web extraction provider through Hermes' public plugin API. It calls `https://r.jina.ai/<url>`, supports keyless Reader access, optional Jina credentials and upstream proxies, JavaScript-capable browser extraction, JSON transport, selector waiting, configurable user-agents, and Jina cache headers.

This plugin is deliberately standalone:

- it does **not** patch Hermes core;
- it does **not** modify Hermes' built-in web tools or cache;
- it uses the public `WebSearchProvider` and plugin registration APIs;
- it can live as a normal Git repository under `~/.hermes/plugins/web/jina/`.

## Status

- Version: `0.1.0`
- Hermes capability: `web_extract` provider
- Runtime dependency: `httpx` (already used by Hermes; declared for standalone development)
- Test dependency: `pytest`
- License: BSD 3-Clause, with attribution to Rad Paluszak and NON.agency

## What this is not

This plugin only provides URL content extraction. It does not add or modify any unrelated Hermes capability.

It does not bypass target-site access controls, authentication, robots policies, or Jina limits. Use a local browser workflow when the target requires a signed-in session.

## Prerequisites

You need:

1. Hermes Agent with the web-provider plugin API.
2. Python 3.11 or newer for development and tests.
3. `httpx` available in the Hermes runtime.
4. Optional: `JINA_API_KEY` for higher Jina limits.
5. Optional: an upstream proxy URL accepted by Jina.

## Installation

This README gives the short path. For the full copy-paste guide, read [`INSTALL.md`](INSTALL.md). Agents working in this repository must read [`AGENTS.md`](AGENTS.md).

Clone the repository into the user web-plugin directory:

```bash
mkdir -p ~/.hermes/plugins/web
git clone <REPO_URL> ~/.hermes/plugins/web/jina
```

Enable the plugin for the target profile:

```bash
hermes -p <profile> plugins enable web/jina
```

Set the extract backend in the profile configuration:

```yaml
web:
  extract_backend: jina
```

Plugin settings use the namespaced configuration entry:

```yaml
plugins:
  entries:
    web/jina:
      settings:
        timeout: 20
        browser_engine: default
        wait_for: ""
        user_agent_mode: random
        user_agents:
          - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
          - "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
        target_selector: ""
        remove_selector: ""
        with_generated_alt: false
        no_cache: false
        cache_tolerance: 0
```

Restart the relevant Hermes session after enabling or changing configuration.

## Secrets and proxy configuration

Put credentials and proxy URLs in the target profile `.env`, not in `config.yaml`:

```dotenv
JINA_API_KEY=your-optional-jina-api-key
JINA_SOCKS5_PROXY=socks5://user:password@proxy.example:1080
```

Alternatively:

```dotenv
JINA_HTTP_PROXY=http://user:password@proxy.example:8080
```

Set only one proxy variable. If both are set, the plugin fails closed with a configuration error; neither variable takes precedence.

The proxy is sent to Jina as `X-Proxy-Url`. It is not used as a proxy for the Hermes-to-Jina connection.

## Configuration

| Setting | Default | Purpose |
|---|---:|---|
| `timeout` | `20` | Jina timeout in seconds, bounded to the supported range. |
| `browser_engine` | `default` | `default`, `auto`, `browser`, `curl`; `browser` enables JS-capable extraction. |
| `wait_for` | empty | CSS selector passed as `X-Wait-For-Selector`. |
| `user_agent_mode` | `random` | Select `random`, `fixed`, or `off`. |
| `user_agents` | built-in list | Editable Chromium, Chrome, and Firefox user-agent strings. |
| `target_selector` | empty | CSS selector passed as `X-Target-Selector`. |
| `remove_selector` | empty | CSS selector passed as `X-Remove-Selector`. |
| `with_generated_alt` | `false` | Ask Jina to generate image alt text. |
| `no_cache` | `false` | Ask Jina not to use its upstream cache. |
| `cache_tolerance` | `0` | Optional Jina upstream cache tolerance in seconds. |

The configured `timeout` is sent to Jina as `X-Timeout`. The HTTP client waits five seconds longer so it does not cancel the request before Reader reaches that deadline. The standard `web_extract` `format` argument maps to Jina's `X-Respond-With` (`html` or `markdown`); `Accept: application/json` remains in place for the JSON response envelope.

`browser_engine: default` intentionally sends no `X-Engine` header. The existing Hermes `web_extract` cache remains responsible for local cache behavior; this plugin does not replace or patch that cache.

## Example prompts

In normal use, ask Hermes to extract a page:

```text
Use web_extract to read https://example.com and return the main content.
```

With configured browser extraction:

```text
Use web_extract to read the configured page and preserve the rendered page content.
```

With configured selectors:

```text
Use web_extract and focus on the article body configured for this profile.
```

Plugin-specific options are profile configuration values. The standard `web_extract` format argument is supported; this plugin does not extend Hermes' core tool schema.

## How it works

At plugin discovery time, `register(ctx)` reads the namespaced settings and registers `JinaWebSearchProvider` through `ctx.register_web_search_provider(...)`.

For each URL, the provider:

1. builds `https://r.jina.ai/<url>`;
2. sends `Accept: application/json`;
3. adds an optional bearer key;
4. adds configured Jina Reader headers;
5. parses the Jina `data` object;
6. returns the Hermes extraction result shape;
7. records a per-URL error without discarding other results.

The provider reports keyless availability without making a network request. It advertises extraction support only.

## Development and verification

Install development dependencies and run tests with the Hermes source on `PYTHONPATH`:

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=/path/to/hermes-agent python -m pytest tests -q
```

The tests mock HTTP responses. A live smoke test should use a test profile and a public page such as `https://example.com`:

```text
Use web_extract on https://example.com.
```

Do not commit `.env`, API keys, proxy credentials, caches, or profile state.

## Support, warranty, and liability

This software is provided **as-is**, without warranty of any kind.

Rad Paluszak, NON.agency, and contributors are not responsible for misconfiguration, failed extraction, provider limits, leaked credentials, provider-side logging, data loss, downtime, business interruption, or any other damages arising from use of this plugin.

Bug reports and fixes may be handled when time allows, at the maintainers' own discretion and on their own schedule. There is no SLA, guaranteed support window, or obligation to provide fixes for a particular deployment.

## Author

- Rad Paluszak: [paluszak.me](https://paluszak.me/)
- NON.agency: [non.agency](https://non.agency/)

## License

BSD 3-Clause License.

You may use, copy, modify, and redistribute this software, including modified versions, provided you preserve the required copyright/license attribution to:

- Rad Paluszak — https://paluszak.me/
- NON.agency — https://non.agency/

See [`LICENSE`](LICENSE) for the full license text.
