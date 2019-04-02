from pathlib import Path
from setuptools import setup

setup(
    py_modules = ['artisan'],
    name = 'artisan',
    version = '0.2.0',
    description = 'A build system for explainable science',
    long_description = Path('readme.md').read_text(),
    long_description_content_type = 'text/markdown',
    url = 'http://github.com/MasonMcGill/cmdgraph',
    author = 'Mason McGill',
    author_email = 'mmcgill@caltech.edu',
    license = 'MIT',
    platforms = 'any',
    zip_safe = False
)
