# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-06-26 - Fill the remaining OR-Tools coverage gaps

### Added
* **`blend`** — diet / blending linear program (Glop): continuous item quantities
  minimizing cost subject to per-attribute min/max requirements.
* **Routing optional visits** — `solve_routing(penalties=…)` makes stops droppable
  at a penalty (prize-collecting); dropped nodes are in `metadata["dropped"]`.
* **Routing fleet sizing** — `solve_routing(vehicle_fixed_cost=…)` minimizes the
  number of vehicles used.
* **Assignment with teams** — `assignment(teams=…, team_capacity=…)` caps how many
  agents each team may use.
* **Assignment with allowed groups** — `assignment(allowed_groups=…)` restricts the
  active-agent set of each group to an allowed pattern.

### Changed
* Stronger input validation: required numeric columns reject nulls; weights, sizes,
  capacities, and supply/demand must be non-negative; id and lookup-key columns must
  be unique.
* Dropped the unused `pandera` runtime dependency — validation is hand-rolled in the
  Narwhals layer, so runtime deps are just `narwhals` + `ortools`.

## [0.4.0] - 2026-06-26 - Long-form (tidy) inputs

### Changed (breaking)
* **`assignment`, `generalized_assignment`, `facility_location`, `transportation`,
  and `set_cover` now take long, tidy edge lists** instead of wide matrices — one
  row per allowed pairing, so sparse problems are expressed by omitting rows. This
  is more on-brand (tidy data), handles sparsity and forbidden pairs naturally, and
  unifies these solvers with the network-flow API.
  - `assignment(edges, left=, right=, value=)` → edges + a `selected` column.
  - `generalized_assignment(edges, capacities, ...)` — one `(task, agent, value,
    size)` edge frame replaces the two value/size matrices.
  - `facility_location(edges, setup_costs)` → edges + `selected`.
  - `transportation(edges, supply, demand)` — `(source, sink, cost)` lanes.
  - `set_cover(membership, costs)` — `(subset, element)` pairs + a subset cost table.
* Per-node inputs (capacities / supply / demand / setup costs) accept a mapping or a
  two-column `(node, value)` frame.
* The first result shape is renamed **selection** (was "assignment-matrix") — these
  solvers annotate the input rows with what was chosen.

The wide-matrix entry points are removed; `melt` a matrix to long form if needed.

## [0.3.0] - 2026-06-26 - New solvers + Sphinx docs

### Added
* **Transportation** (`transportation`) — min-cost shipping from sources to sinks
  (edge-flow shape).
* **Generalized assignment** (`generalized_assignment`) — capacity-limited agents
  with task sizes/values (assignment-matrix shape).
* **Job shop** (`job_shop`) — sequence job tasks on shared machines, minimize
  makespan (interval-schedule shape).
* **Set cover** (`set_cover`) — minimum-cost subsets covering all elements, with a
  set-partition variant.
* **Multidimensional knapsack** — `knapsack` accepts a list of weight columns and
  capacities.
* Example notebooks covering every solver (`assignment_and_flow`, `scheduling`),
  runnable on Binder.

### Changed
* **Docs migrated to Sphinx + furo** (from mkdocs-material): a per-solver guide
  with problem explanations, deployed to GitHub Pages via the artifact flow.

## [0.2.0] - 2026-06-26 - Renamed to `ortidy`, rebuilt on Narwhals

### Added
* **Assignment & facility location** (assignment-matrix shape): `assignment`
  (linear sum assignment) and `facility_location` (uncapacitated).
* **Network flow** (edge-flow shape): `max_flow`, `min_cost_flow`, `shortest_path`.
* **Shift scheduling** (`shift_scheduling`) — the interval-schedule result shape.
* **Routing promises**: VRPTW (time windows) and pickups & deliveries in
  `solve_routing`, plus a `distance_matrix` helper (euclidean / haversine) so
  routing can take locations instead of a precomputed matrix.
* mkdocs-material documentation.

### Changed
* **Renamed `pandas-or` → `ortidy`** ("OR on tidy dataframes"). The importable
  module is now `ortidy`; the old `pandas-or` 0.1.3 on PyPI is left unmaintained.
* **Backend-agnostic** via Narwhals: pandas in → pandas out, Polars in → Polars
  out. pandas remains the reference backend.
* Every solver returns a structured **`SolveResult`** (frame, status, objective,
  metadata) instead of a bare frame / `None`. A `FEASIBLE` solution is a success.
* Rows are identified by **explicit id columns**, never a positional index.

### Fixed
* `knapsack`: migrated to the modern `ortools.algorithms.python.knapsack_solver`
  import and honest return type; added float→int unit-scaling.
* `multi_knapsack` / `bin_packing`: rebuilt on CP-SAT, removing the per-row
  `apply(..BoolVar.., axis=1)` variable-construction anti-pattern.
* `solve_routing`: removed the phantom final route row and the dead
  `"capacity" in column_names` branch; promoted the hardcoded `3000` / `100` /
  `1s` magic numbers to parameters.
* Replaced the always-failing `__version__ == "0.1.0"` test with a real suite
  (correctness, golden-file, infeasible-status, backend-parity).

### Tooling
* Python floor raised to 3.10; **uv** for dependency management (PEP 735
  `[dependency-groups]`) with **hatchling** as the build backend; `ruff`, `mypy`,
  `pre-commit`, and GitHub Actions CI (test matrix + strict docs build).
* Depend on `ortools>=9.12` (current 9.15), supporting Python 3.10–3.14.
* Stripped ~8 MB of embedded notebook output.

## [0.1.3] - 2022-08-07

### Fixed
* Replaced `operations research` with `optimization research` in docs.

## [0.1.2] - 2022-08-07

### Fixed
* Fixed multi_knapsack to assign each item to only one bin.
* Added separate dataset for multi_knapsack and bin_packing compared to knapsack.

### Additions
* Added docstrings.
* Added CITATION.cff

## [0.1.1] - 2022-08-04

### Fixed
* Added binder requirements.
* Filtering of bin_packing with resetting of binId.

## [0.1.0] - 2022-07-31 - Initial release

### Added
* Functions for solving knapsack type problems.
* Basic vehicle routing solving functions.