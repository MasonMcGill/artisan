'''
Non-CBOR readers and writers used by the `Artifact` class.

Exported definitions:
    read_text_file (function): Read a text file using `Path.read_text`.
    read_json_file (function): Read a JSON file using `json.load`.
    read_numpy_file (function): Read a NumPy array file using `numpy.load`.
    read_opaque_file (function): Return the given path, unchanged.
    write_path (function): Create a symbolic link.
'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing_extensions import Annotated

import numpy as np

from ._namespaces import namespacify

__all__ = [
    'read_json_file', 'read_numpy_file', 'read_opaque_file',
    'read_text_file', 'write_artifact', 'write_path']



#-- Readers --------------------------------------------------------------------

def read_text_file(path: Annotated[Path, '.txt']) -> str:
    '''
    Read a text file using `Path.read_text`.
    '''
    if path.suffix != '.txt':
        raise ValueError()
    return path.read_text()


def read_json_file(path: Annotated[Path, '.json']) -> Any:
    '''
    Read a JSON file using `json.load`.

    JSON objects are read as namespaces.
    '''
    if path.suffix != '.json':
        raise ValueError()
    with open(path) as f:
        return namespacify(json.load(f))


def read_numpy_file(path: Annotated[Path, '.npy', '.npz']) -> Any:
    '''
    Read a NumPy array file or a NumPy archive using `numpy.load`.
    '''
    if path.suffix not in ['.npy', '.npz']:
        raise ValueError()
    return np.load(path, allow_pickle=True)


def read_opaque_file(path: Path) -> Path:
    '''
    Return the given path, unchanged.
    '''
    return path



#-- Writers --------------------------------------------------------------------

def write_path(path: Path, val: Path) -> str:
    '''
    Create a symbolic link.
    '''
    if not isinstance(val, Path):
        raise TypeError()
    path.symlink_to(val)
    return val.suffix
