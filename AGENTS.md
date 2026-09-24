# AGENTS.md

Instructions for agents working in this repository.

## Repository purpose

This repository contains a standalone Hermes Agent plugin that registers the Jina Reader provider for `web_extract`.

## Non-negotiable scope

- Keep the plugin standalone.
- Do not patch Hermes core.
- Do not edit files in the Hermes source checkout.
- Do not add unrelated capabilities.
- Preserve the public `WebSearchProvider` extraction contract.
- Keep profile settings in `config.yaml` and credentials in the profile `.env`.

## Files and secrets

- Never commit `.env`, API keys, proxy credentials, caches, or profile state.
- Do not log `JINA_API_KEY` or proxy URLs.
- Keep public documentation in English.
- Preserve the BSD 3-Clause copyright and attribution terms.

## Development workflow

1. Read `README.md` and `INSTALL.md` before changing the plugin.
2. Run the unit tests with Hermes source on `PYTHONPATH`.
3. Inspect `git diff` and `git status`.
4. Run a plugin discovery smoke test against a temporary or explicitly selected profile.
5. Do not run live extraction unless it is part of the approved verification scope.
6. Do not add a Git remote, create a remote repository, publish, or push without explicit operator approval.

## Implementation rules

- Use `get_provider_env()` for Hermes-aware environment lookup.
- Keep extraction errors per URL.
- Do not make availability checks perform network requests.
- Ignore unknown forward-compatible provider kwargs.
- Keep the default timeout at 20 seconds.
- Keep `browser_engine: default` equivalent to omitting `X-Engine`.
- Do not use Hermes core patches to expose new tool parameters.

## Verification command

```bash
PYTHONPATH=/path/to/hermes-agent python -m pytest tests -q
```

## Commit rule

Local commits are allowed after tests pass. Do not push or publish the repository without a separate explicit approval.
