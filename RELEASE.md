## [0.2.0] - 2026-06-26 - Renamed to `ortidy`, rebuilt on Narwhals

### Changed
* **Renamed `pandas-or` → `ortidy`** ("OR on tidy dataframes"). The importable
  module is now `ortidy`; `pandas-or` continues to resolve via a deprecation shim.
* **Backend-agnostic** via Narwhals: pandas in → pandas out, Polars in → Polars
  out. pandas remains the reference backend.
* Every solver returns a structured **`SolveResult`** (frame, status, objective,
  metadata) instead of a bare frame / `None`. A `FEASIBLE` solution is a success.
* Rows are identified by **explicit id columns**, never a positional index.
* Added the **`.or_` accessor** (`df.or_.knapsack(...)`) on pandas and Polars.

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
* Python floor raised to 3.10; `ruff`, `mypy`, `pre-commit`, GitHub Actions CI;
  stripped ~8 MB of embedded notebook output.

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