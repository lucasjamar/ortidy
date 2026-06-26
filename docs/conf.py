"""Sphinx configuration for ortidy."""

from __future__ import annotations

import importlib.metadata
import os
import sys

# Make the package importable for autodoc without requiring an install.
sys.path.insert(0, os.path.abspath(".."))

project = "ortidy"
author = "Lucas Jamar"
release = importlib.metadata.version("ortidy")
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

autosummary_generate = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {"members": True, "show-inheritance": True}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "narwhals": ("https://narwhals-dev.github.io/narwhals/", None),
}

myst_enable_extensions = ["colon_fence", "deflist"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

html_theme = "furo"
html_title = f"ortidy {version}"
html_static_path = ["_static"]
html_theme_options = {
    "source_repository": "https://github.com/lucasjamar/ortidy",
    "source_branch": "main",
    "source_directory": "docs/",
}
