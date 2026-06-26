# Releasing

`ortidy` builds and publishes with **uv** — no `twine`/`build` needed.

## 1. Publish `ortidy`

```bash
# from the repo root
uv build                      # → dist/ortidy-<version>.{whl,tar.gz}
uv publish --token pypi-XXXX  # or set UV_PUBLISH_TOKEN
```

`uv publish` defaults to PyPI. To dry-run against TestPyPI first:

```bash
uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-XXXX
```

## 2. Publish the `pandas-or` deprecation shim

Publish the shim **after** `ortidy` (it depends on it):

```bash
cd packaging/pandas-or-shim
uv build
uv publish --token pypi-XXXX
```

Do **not** delete the old `pandas-or` PyPI project — leaving the shim as a
tombstone prevents the name being taken by typosquatters.

## Version bump checklist

Bump the version in **all four** places, then rebuild:

- `pyproject.toml` → `[project] version`
- `ortidy/__init__.py` → `__version__`
- `CITATION.cff` → `version`
- `RELEASE.md` → new changelog entry
