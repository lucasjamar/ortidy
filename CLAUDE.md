# CLAUDE.md — ortidy

Guidance for Claude Code working in this repository. Read this fully before making changes.

> **Naming note:** this project is the revival of `pandas-or` (PyPI, last release `0.1.3`, dormant ~4 years), renamed to **`ortidy`** to reflect its new backend-agnostic design. "ortidy" = **OR** (operations research) on **tidy** dataframes. See *Renaming & migration* below for the mechanics.

## What this project is

`ortidy` is a dataframe-native façade over [Google OR-Tools](https://developers.google.com/optimization). The thesis: bridge operations research and the data ecosystem so that solver outputs come back as tidy dataframes ready for analysis, plotting, and dashboards.

**Core principle to internalize:** the dataframe is *glue*, not the compute engine. All heavy lifting happens inside OR-Tools (C++). Our code does input validation, light reshaping (joins, group-bys), the solver handoff, and result assembly. Do not optimize dataframe operations for speed — the bottleneck is always the solve. Optimize for *clarity, correctness, and a consistent API*.

---

## Hard decisions already made (do not relitigate)

1. **Dataframe backend: Narwhals, not raw pandas or Polars.**
   The library must be backend-agnostic. Use [Narwhals](https://narwhals-dev.github.io/narwhals/) as the internal layer so a user who passes pandas gets pandas back, a user who passes Polars gets Polars back. pandas remains the *default/reference* backend. Polars, pyarrow, etc. come for free.
   - Import the stable namespace: `import narwhals.stable.v1 as nw`. This carries a backward-compatibility guarantee and shields us from upstream pandas/Polars churn — the exact rot that killed the original.
   - Accept native frames at the public boundary, convert with `nw.from_native(...)`, do internal work in Narwhals expressions, return with `.to_native()`. The `@nw.narwhalify` decorator is acceptable for simple functions.
   - At the **solver boundary**, extract plain Python lists/ints/floats from columns. OR-Tools does not consume dataframes; this handoff is backend-neutral by design.

2. **No implicit pandas index.** Narwhals follows the Polars index-free model. Identify rows with explicit ID columns (`itemId`, `binId`, `vehicleId`, `locationId`, …), never with a positional index. This is also required by the return contract below.

3. **Name: `ortidy`** (renamed from `pandas-or`). The importable module is `ortidy` (`import ortidy`). The old `pandas-or` 0.1.3 stays on PyPI unmaintained (not deleted). Update all references, badges, and the module folder accordingly.

4. **Modern solver choice:** prefer **CP-SAT** (`from ortools.sat.python import cp_model`) for packing/assignment/scheduling models over the legacy `pywraplp`/SCIP path. CP-SAT is Google's recommended modern solver and removes the variable-construction mess in the old code. Keep the dedicated routing library (`ortools.constraint_solver.pywrapcp`) for routing, and the dedicated graph solvers for flow.

---

## Renaming & migration (pandas-or → ortidy)

The two platforms behave differently — handle each correctly.

- **GitHub: rename the existing repo in place. Do NOT start a fresh repo.** Renaming preserves history, stars, issues, and watchers, and GitHub auto-redirects the old URL (web, clones, fetches, API) to the new name. Redirects break only if a new repo is later created at the old path — so don't reuse it.
  - Before the rewrite lands, preserve the old version: tag it (`v0.1.3-legacy`) and/or cut a `legacy/0.1.x` branch. Do the rewrite on `main`.
- **PyPI: there is no rename feature — register `ortidy` as a new project.** Publish the new code under `ortidy`. **Decision:** *no* `pandas-or` deprecation/redirect shim is shipped — `pandas-or` had effectively no adoption, so a redirect shim isn't worth the maintenance. **Do not delete** the old `pandas-or` 0.1.3 project (deleting frees the name for typosquatters); leave it as-is. Its project page links to this GitHub repo, which redirects to `ortidy`.
- **Availability:** `ortidy` is confirmed free on PyPI and as an import name. If the name is ever changed again, re-check PyPI, the importable module name, GitHub, and Read the Docs *before* committing.
- **Surfaces to update during the rename:** `pyproject.toml` (name, urls), the module folder `pandas_or/` → `ortidy/`, `CITATION.cff`, README + badges, Read the Docs project, Binder links, and any `import pandas_or` in examples/notebooks.

---

## Design contracts (apply to every solver)

These are the through-lines that make this a coherent library rather than a bag of functions.

### Consistent return contract
Every solver returns the user's original frame (same backend, same rows where applicable) with assignment columns added, plus a status. There are exactly **three result shapes** — design every feature to fit one of them:
- **assignment-matrix** — rows mapped to columns/bins/resources (knapsack, multi-knapsack, bin packing, assignment, transportation, facility location).
- **edge-flow** — values on an edge list (max-flow, min-cost-flow, shortest path, transshipment).
- **interval-schedule** — intervals placed on a timeline (shift scheduling, job-shop, RCPSP).

Do **not** invent a fourth shape without flagging it for discussion first.

### Result object, not print-and-None
The old code does `print("no optimal solution")` and implicitly returns `None`. Replace everywhere with a structured result carrying: the result frame, a status enum (`OPTIMAL` / `FEASIBLE` / `INFEASIBLE` / `UNBOUNDED` / `MODEL_INVALID`), objective value, and solve metadata (wall time, gap). **A `FEASIBLE` solution is a success, not a failure** — the old code wrongly discards anything that isn't `OPTIMAL`.

### Functional API (the canonical interface)
Solvers are plain functions: pass a native frame, get a `SolveResult` back in the
same backend, e.g. `ortidy.knapsack(df, capacity=100)` and
`ortidy.solve_routing(distances, vehicles=...)`. This is the canonical, fully
backend-agnostic surface — it works for *any* Narwhals backend.

> **Decision:** the `.or_` dataframe accessor was **removed**. It only worked on
> backends we explicitly registered (pandas, Polars) — undercutting the
> backend-agnostic promise — and mutated the global pandas/Polars namespace at
> import time. The functional API is the single, portable interface. If a
> chainable surface is wanted later, prefer an explicit, side-effect-free wrapper
> (`ortidy.wrap(df).knapsack(...)`) over a monkeypatch accessor.

### Schema validation
Standardize input validation. The old ad-hoc `if not {"value","weight"}.issubset(...)` pattern is a good instinct — formalize it with [Pandera](https://pandera.readthedocs.io/) (which supports Narwhals/Polars) or explicit schema checks. Raise precise, actionable errors (which column is missing, what dtype was expected). Prefer `ValueError`/`KeyError` over the `AttributeError` the old code raises.

### Surface solver controls
No magic numbers buried in function bodies. Expose `time_limit`, `random_seed`/determinism, and optimality `gap` as parameters with sensible defaults. (The old routing code hardcodes `3000` max distance, `100` span coefficient, `1`s time limit — these must become parameters.)

### Numeric data handling
OR-Tools knapsack requires integer values/weights; real data has floats. Provide a unit-scaling layer (scale floats to ints, solve, unscale) rather than silently passing floats through.

### Infeasibility diagnostics
When there is no solution, report *why* where the solver allows it (e.g. CP-SAT sufficient-assumptions-for-infeasibility, or an irreducible infeasible subset). This is a genuine differentiator — most libraries in this niche just say "no solution."

---

## Roadmap (phased — work in this order)

### P0 — Unbreak, rename, modernize (do first, no new features)
- **Execute the rename** per *Renaming & migration*: rename the GitHub repo, tag/branch the legacy version, rename the module folder `pandas_or/` → `ortidy/`, update `pyproject.toml`/`CITATION.cff`/README/badges, and register `ortidy` on PyPI (no `pandas-or` shim).
- **Fix the dead knapsack import.** Current OR-Tools moved the knapsack solver to `from ortools.algorithms.python import knapsack_solver` with snake_case methods. Verify exact method casing (`init` / `solve` / `best_solution_contains`) against the *installed* ortools version before committing.
- **Fix the broken test.** `tests/` asserts `__version__ == '0.1.0'` while the package was `0.1.3` — it has always failed. Replace with a real suite (see Testing).
- **Fix known bugs:**
  - `knapsack` return type lies: docstring/annotation says `pd.Series` but `items.index.map(...)` returns an `Index`. Align with the new return contract.
  - `single_vehicle_route` appends a phantom final row after the loop using an out-of-range index — drop it.
  - `solve_routing` has a dead `if "capacity" in column_names` branch that checks a distance matrix's columns for a capacity field that cannot be there — remove.
- **Modernize packaging/tooling:** Python floor to 3.10+; PEP 621 `[project]` metadata with **uv** as the package/dependency manager (PEP 735 `[dependency-groups]`) and **hatchling** as the build backend; unpin to current `ortools` (`>=9.12`), add `narwhals`; add `ruff` (lint+format, replacing black-only), `mypy`, `pre-commit`; add GitHub Actions CI; add `nbstripout` and strip the embedded notebook output bloating the repo.
- **Migrate the working solvers to Narwhals + the return contract** without changing their math: `knapsack`, `multi_knapsack`, `bin_packing`, `solve_routing`. While here, kill the `items.apply(lambda x: solver.BoolVar(...), axis=1)` cross-product variable-construction anti-pattern (rebuild on CP-SAT).

### P1 — API consistency + new shapes (cheap, high-value)
- **Assignment & transportation** (assignment-matrix shape). Linear assignment via `ortools.graph.python.linear_sum_assignment`; generalized assignment (GAP) and transportation/transshipment via CP-SAT/MIP. A cost matrix *is* a dataframe — the most natural fit and the cheapest big win.
- **Network flow** (edge-flow shape). Max-flow, min-cost-flow, shortest path via the dedicated `ortools.graph.python` solvers. Naturally an edge-list frame.
- **Finish the routing promises** already advertised in the old README: **time windows (VRPTW)** and **pickups & deliveries**. Also expose multiple depots and heterogeneous fleets.
- **Separate distance-matrix construction from routing.** The old API secretly requires `df` to be a precomputed distance matrix. Add a helper that builds the matrix from lat/long (haversine) or x/y (euclidean) so the routing API takes *locations* — what users actually have.
- Ship the **result object** across all P0/P1 solvers. (The `.or_` accessor was removed — see *Functional API* above.)

### P2 — Flagship + polish
- **Scheduling / rostering** (interval-schedule shape) on CP-SAT: shift scheduling (the long-promised feature), job-shop/flow-shop, RCPSP. Build this only after the result-object design has proven itself on P1.
- **Facility location & covering:** facility location, p-median, set cover/partition.
- **Docs:** stand up `mkdocs-material` (the README has promised "Read The Docs coming soon" for four years). Document the three result shapes as the conceptual spine.
- Optional routing extras: optional visits / prize-collecting, backhauls.

---

## What to preserve from the existing code

- `pandas_or/binning/knapsack.py` — cleanest file; keep its structure and docstring style, fix the bugs above.
- The column-validation instinct — formalize, don't discard.
- The **route feature-engineering** (`tripsSinceStart`, `tripsTillEnd`, `distanceSinceStart`, `distanceTillEnd`) — the most original idea in the repo and the clearest expression of the OR-meets-analytics thesis. Reimplement on Narwhals `over` expressions (grouped `shift`, `cum_sum`); keep the concept.
- The sample CSVs under `pandas_or/data/` (move to `ortidy/data/`) and the Binder examples — good onboarding assets and the basis for golden-file tests.
- The Parameters/Returns/Link docstring convention.

---

## Conventions

- **Style:** `ruff format` + `ruff check`. Type-annotate all public functions; `mypy` must pass.
- **Types:** annotate honestly. If a function returns the result object, say so — no more `pd.Series` annotations on things that aren't.
- **Errors:** precise and actionable. Name the missing column and expected dtype. Prefer `ValueError`/`KeyError` over `AttributeError`.
- **No magic numbers** in function bodies — promote to named parameters with documented defaults.
- **Determinism:** plumb a `random_seed` through solvers that support it so tests and examples are reproducible.
- **Public API** is re-exported from `ortidy/__init__.py` and listed in `__all__`; keep it curated.

## Testing

- `pytest`, run via `uv run pytest`.
- Every solver needs: a correctness test (assert the math), a **golden-file test** against the bundled sample CSVs, an **infeasible-input test** (assert the right status, not an exception), and a **backend-parity test** (same input as pandas *and* Polars yields equivalent results — this is the whole point of Narwhals).
- Assert solver *status*, not just output shape. Cover the `FEASIBLE`-is-success path explicitly.

## Dev commands

```bash
uv sync                 # install runtime + dev deps into .venv (uses .python-version = 3.12)
uv sync --group docs    # also install the docs toolchain
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy ortidy
uv run pre-commit run --all-files
uv build                # build sdist + wheel (hatchling)
```

## Guardrails for Claude Code

- Do not reintroduce a hard pandas dependency in solver logic — go through the Narwhals layer.
- Do not pin OR-Tools to an old version to make old import paths work; migrate to current imports instead.
- Do not add a result shape beyond the three above without raising it first.
- When unsure whether a solver returned its best answer, prefer accepting `FEASIBLE` over rejecting it.
- Verify any OR-Tools import path and method casing against the installed version — the bindings have drifted and will drift again.
- Do not start a fresh GitHub repo for the rename — rename in place to preserve history and redirects.
