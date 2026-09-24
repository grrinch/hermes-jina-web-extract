# Installation

This document is the full installation guide for `hermes-jina-web-extract`.

## 1. Choose the Hermes profile

Use the profile that should load the plugin. Replace `<profile>` in the commands below with its actual name.

## 2. Install the repository

For a shared user-global checkout:

```bash
mkdir -p ~/.hermes/plugins/web
git clone <REPO_URL> ~/.hermes/plugins/web/jina
```

For a local checkout during development:

```bash
mkdir -p ~/.hermes/plugins/web
git clone <REPO_URL> ~/.hermes/plugins/web/jina
cd ~/.hermes/plugins/web/jina
```

Do not place credentials in the repository.

## 3. Configure the provider

Set the extract backend in the target profile `config.yaml`:

```yaml
web:
  extract_backend: jina
```

Enable the plugin:

```bash
hermes -p <profile> plugins enable web/jina
```

Configure optional settings under the plugin namespace:

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

The default engine is `default`, which means the plugin omits `X-Engine`. Use `browser` to ask Jina for JavaScript-capable rendering.

## 4. Configure optional secrets

Use the target profile `.env` file:

```dotenv
JINA_API_KEY=your-optional-jina-api-key
JINA_SOCKS5_PROXY=socks5://user:password@proxy.example:1080
```

Or use an HTTP proxy:

```dotenv
JINA_HTTP_PROXY=http://user:password@proxy.example:8080
```

Set only one proxy variable. The plugin fails closed when both are set.

## 5. Restart the session

Start a new Hermes session after enabling the plugin or changing profile configuration. If the profile runs under a gateway, restart it from a separate host shell when required:

```bash
hermes -p <profile> gateway restart
```

## 6. Verify discovery

From a Hermes source checkout:

```bash
HERMES_HOME=~/.hermes/profiles/<profile> \
PYTHONPATH=/path/to/hermes-agent \
python - <<'PY'
from hermes_cli.plugins import _ensure_plugins_discovered
from agent.web_search_registry import get_provider

manager = _ensure_plugins_discovered(force=True)
provider = get_provider("jina")
print("plugin_loaded=", "web/jina" in manager._plugins)
print("provider_registered=", provider is not None)
print("extract_supported=", provider.supports_extract() if provider else False)
print("available=", provider.is_available() if provider else False)
PY
```

Expected values are `True` for all four checks.

## 7. Run tests

From the repository root:

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=/path/to/hermes-agent python -m pytest tests -q
```

The tests use mocked HTTP responses and do not consume Jina quota.

## 8. Run a live smoke test

Use a public test page:

```text
Use web_extract on https://example.com and return the extracted title and content.
```

Do not use a production credential or a private page for the first smoke test.

## Troubleshooting

### Plugin is not listed

Check the directory layout:

```text
~/.hermes/plugins/web/jina/plugin.yaml
~/.hermes/plugins/web/jina/__init__.py
```

Check the plugin list and enable the path-derived plugin key:

```bash
hermes -p <profile> plugins list
hermes -p <profile> plugins enable web/jina
```

### Extract backend is unavailable

Confirm:

- `web.extract_backend: jina` is set;
- the plugin is enabled;
- the Hermes process was restarted after configuration changes;
- the source checkout is on `PYTHONPATH` for development discovery tests.

### Jina returns a limit or authorization error

Keyless Reader access is rate-limited. Add `JINA_API_KEY` to the profile `.env` and restart the profile session.

### Proxy errors

Confirm that exactly one of `JINA_SOCKS5_PROXY` or `JINA_HTTP_PROXY` is set and that the URL includes its scheme.
