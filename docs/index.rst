ortidy
======

**OR** (operations research) on **tidy** dataframes — a backend-agnostic dataframe
façade over `Google OR-Tools <https://developers.google.com/optimization>`_.

Pass a dataframe in, get a dataframe back. Built on
`Narwhals <https://narwhals-dev.github.io/narwhals/>`_, so **pandas in → pandas out,
Polars in → Polars out**. Every solver returns a :class:`~ortidy.result.SolveResult`
carrying the result frame, a status, the objective, and solve metadata.

.. code-block:: bash

   pip install ortidy

.. code-block:: python

   import pandas as pd
   import ortidy

   items = pd.DataFrame({"value": [60, 100, 120], "weight": [10, 20, 30]})
   result = ortidy.knapsack(items, capacity=50)
   result.objective   # 220
   result.frame       # items + an isIncluded column

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting-started
   concepts/result-shapes
   examples

.. toctree::
   :maxdepth: 2
   :caption: Solver guide

   guide/assignment-packing
   guide/network-flow-routing
   guide/scheduling

.. toctree::
   :maxdepth: 2
   :caption: API reference

   api/result
   api/assignment-matrix
   api/edge-flow
   api/interval-schedule

Try the examples on Binder:

.. image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/lucasjamar/ortidy/main?labpath=examples
