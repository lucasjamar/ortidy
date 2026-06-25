# pandas-or → ortidy

**`pandas-or` has been renamed to [`ortidy`](https://pypi.org/project/ortidy/)**
("OR on tidy dataframes") and rebuilt to be backend-agnostic (pandas **and**
Polars, via Narwhals).

This package is a deprecation shim. Installing it installs `ortidy`:

```bash
pip install pandas-or   # pulls in ortidy
```

Please update your dependency to `ortidy` and `import ortidy` directly. The API
has changed — solvers now return a structured `SolveResult` and identify rows by
explicit id columns. See the [migration notes](https://github.com/lucasjamar/ortidy#migrating-from-pandas-or).
