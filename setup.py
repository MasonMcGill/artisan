from pathlib import Path
from setuptools import setup

short_desc = (
    'A small set of complimentary tools for '
    'exploratory computational research')
long_desc = Path('readme.md').read_text()

setup(
    py_modules=['cmdgraph'],
    name='cmdgraph',
    version='0.1.2',
    description=short_desc,
    long_description=long_desc,
    long_description_content_type='text/markdown',
    url='http://github.com/MasonMcGill/cmdgraph',
    author='Mason McGill',
    author_email='mmcgill@caltech.edu',
    license='MIT',
    platforms='any',
    zip_safe=False)
