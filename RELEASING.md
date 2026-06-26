# Releasing

`ortidy` builds and publishes with **uv** — no `twine`/`build` needed.

## Recommended: publish from CI (Trusted Publishing, no token)

`.github/workflows/publish.yml` builds and publishes `ortidy` whenever a GitHub
Release is published, authenticating to PyPI via OIDC — **no API token is stored
anywhere**.

**One-time PyPI setup** (before the first release): go to
<https://pypi.org/manage/account/publishing/> and add a *pending publisher*:

| Field | Value |
| --- | --- |
| PyPI project name | `ortidy` |
| Owner | `lucasjamar` |
| Repository | `ortidy` |
| Workflow name | `publish.yml` |
| Environment | `pypi` |

Then in the GitHub repo, create an Environment named `pypi`
(*Settings → Environments*). After that, each release:

1. Bump the version (see checklist below) and merge to `main`.
2. Create a GitHub Release with tag `vX.Y.Z` → the workflow builds and publishes.

## Manual fallback (local, token-based)

```bash
# from the repo root
uv build                      # → dist/ortidy-<version>.{whl,tar.gz}
uv publish --token pypi-XXXX  # or set UV_PUBLISH_TOKEN
```

`uv publish` defaults to PyPI. To dry-run against TestPyPI first:

```bash
uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-XXXX
```

## The old `pandas-or` PyPI project

There is no migration shim. The existing `pandas-or` 0.1.3 project stays on PyPI
as-is (don't delete it — that would free the name for typosquatters). Its project
page links to this GitHub repo, which redirects to `ortidy`. New users install
`ortidy` directly.

## Version bump checklist

Bump the version in **all four** places, then rebuild:

- `pyproject.toml` → `[project] version`
- `ortidy/__init__.py` → `__version__`
- `CITATION.cff` → `version`
- `CHANGELOG.md` → new changelog entry
