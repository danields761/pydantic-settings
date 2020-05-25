# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

from datetime import datetime
from pathlib import Path
from packaging.version import Version
import toml


# -- Project information -----------------------------------------------------
proj_meta = toml.load(Path(__file__).parents[1] / 'pyproject.toml')['tool']['poetry']

author = ', '.join(proj_meta['authors'])
project = 'Pydantic Settings'
copyright = f'{datetime.now()}, {author}'
release = proj_meta['version']
version = Version(release).base_version if release else ''


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['autoapi.extension', 'm2r']
source_suffix = ['.rst', '.md']


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Configure AutoAPI
autoapi_dirs = ['../pydantic_settings']
autoapi_add_toctree_entry = False
autoapi_options = ['members', 'undoc-members']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

html_theme_options = {'display_version': True, 'collapse_navigation': True}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
