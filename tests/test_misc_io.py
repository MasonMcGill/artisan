import json
from pathlib import Path
from string import ascii_letters
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Dict, List

import numpy as np
from hypothesis import given
from hypothesis.strategies import (
    SearchStrategy, binary, booleans, characters,
    dictionaries, floats, integers, lists, none, recursive, text)

from artisan import (
    read_json_file, read_numpy_file,
    read_opaque_file, read_text_file, write_path)
from artisan._namespaces import namespacify



#-- Search strategies ----------------------------------------------------------

def finite_floats() -> SearchStrategy[float]:
    '''
    Return a search strategy that samples floating-point
    numbers other than +/-infinity and NaN.
    '''
    return floats(allow_nan=False, allow_infinity=False)


def json_like_objects() -> SearchStrategy[object]:
    '''
    Return a search strategy that samples JSON-like objects.
    '''
    return recursive(
        base = none() | booleans() | integers() | finite_floats() | text(),
        extend = lambda s: lists(s) | dictionaries(text(ascii_letters), s),
        max_leaves = 16)



#-- Tests ----------------------------------------------------------------------

@given(text(characters(blacklist_categories='C')))
def test_text_file_reading(content: str) -> None:
    '''
    Test `read_text_file`.
    '''
    with NamedTemporaryFile(suffix='.txt') as f:
        Path(f.name).write_text(content)
        assert read_text_file(Path(f.name)) == content


@given(json_like_objects())
def test_json_file_reading(content: object) -> None:
    '''
    Test `read_json_file`.
    '''
    with NamedTemporaryFile(suffix='.json') as f:
        Path(f.name).write_text(json.dumps(content))
        assert read_json_file(Path(f.name)) == namespacify(content)


@given(lists(floats()))
def test_numpy_array_reading(content: List[float]) -> None:
    '''
    Test `read_numpy_file` with ".npy" files.
    '''
    with NamedTemporaryFile(suffix='.npy') as f:
        np.save(f.name, np.array(content))
        loaded_content = read_numpy_file(Path(f.name))
        assert np.array_equal(loaded_content, content, equal_nan=True)


@given(dictionaries(text(ascii_letters), lists(floats()), min_size=1))
def test_numpy_archive_reading(content: Dict[str, List[float]]) -> None:
    '''
    Test `read_numpy_file` with ".npz" files.
    '''
    content = {k: np.array(v) for k, v in content.items()}
    with NamedTemporaryFile(suffix='.npz') as f:
        np.savez(f.name, **content)
        archive: Any = read_numpy_file(Path(f.name))
        assert archive.keys() == content.keys()
        for key in archive.keys():
            assert np.array_equal(archive[key], content[key], equal_nan=True)


def test_opaque_file_reading() -> None:
    '''
    Test `read_opaque_file`.
    '''
    with NamedTemporaryFile(suffix='.bin') as f:
        assert read_opaque_file(Path(f.name)) == Path(f.name)


@given(binary())
def test_path_writing(content: bytes) -> None:
    '''
    Test `write_path`.
    '''
    with TemporaryDirectory() as root:
        src = Path(root, 'src.bin')
        dst = Path(root, 'dst.bin')
        src.write_bytes(content)
        write_path(dst, src)
        assert dst.read_bytes() == content
