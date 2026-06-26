# Contributing to ortidy

Thanks for your interest! `ortidy` is a backend-agnostic dataframe façade over
Google OR-Tools. Please read [CLAUDE.md](CLAUDE.md) for the design principles
before proposing larger changes.

## Development setup

`ortidy` uses [uv](https://docs.astral.sh/uv/). The dev interpreter is pinned by
`.python-version` (3.12).

```bash
uv sync                 # runtime + dev dependencies
uv sync --group docs    # also the docs toolchain
```

## The checks (all must pass)

```bash
uv run pytest                                    # tests
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run mypy ortidy                               # types
uv run --group docs sphinx-build -W -b html docs docs/_build/html   # docs
```

`uv run pre-commit run --all-files` runs ruff, nbstripout, and mypy locally.

## Design contracts

These are the through-lines that keep `ortidy` coherent — match them:

- **Three result shapes.** Every solver returns *assignment-matrix*, *edge-flow*,
  or *interval-schedule* (see [docs/result-shapes.md](docs/result-shapes.md)).
  Don't add a fourth without raising it first.
- **One result object.** Solvers return a `SolveResult` (frame, status, objective,
  metadata); a `FEASIBLE` solution is a success.
- **Backend-agnostic.** Go through the Narwhals layer (`ortidy/_narwhals.py`);
  accept native frames in, return the same backend out, extract plain Python at
  the solver boundary. No hard pandas dependency in solver logic.
- **Explicit id columns**, never a positional index.
- **Verify OR-Tools import paths/method casing against the installed version** —
  the bindings drift.

## Adding a solver

1. Validate inputs with `ortidy/schema.py` (precise `ValueError`/`KeyError`).
2. Return a `SolveResult`; expose `time_limit` / `random_seed` where supported.
3. Add it to `ortidy/__init__.py` `__all__` and the docs.
4. Tests: correctness, golden-file (bundled CSVs), infeasible-status, and
   pandas + Polars backend-parity.

## Pull requests

Keep PRs focused; make sure the checks above are green. Update `CHANGELOG.md`
under an `## [Unreleased]` heading.
