'''
Documentation dependencies:
- sphinx
- sphinx_rtd_theme
- sphinx-autobuild
- jsx-lexer
'''

# -- Path setup --------------------------------------------------------------

import sys
sys.path.append('python')

# -- Project information -----------------------------------------------------

project = 'artisan'
language = 'en'
copyright = '2019, Mason McGill'
author = 'Mason McGill'

# -- Source definition -------------------------------------------------------

source_suffix = ['.rst']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
master_doc = 'index'

# -- Rendering configuration -------------------------------------------------

default_role = 'py:obj'
pygments_style = 'friendly'
add_module_names = False

# -- Extension configuration -------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode'
]

autodoc_member_order = 'bysource'
autoclass_content = 'both'

todo_include_todos = True

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_theme_options = {'navigation_depth': 2}
