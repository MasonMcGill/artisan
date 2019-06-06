from pathlib import Path

import h5py as h5
import numpy as np

from artisan._artifacts import Artifact

#------------------------------------------------------------------------------

def test_empty_artifact(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'test')
    assert a.path == tmp_path / 'test'
    assert a.conf == {}
    assert a.meta == {'spec': None, 'status': 'done'}
    assert len(a) == 0
    assert list(a) == []
    assert isinstance(a.nonexistent_entry, Artifact)


def test_artifact_entry_assignment(tmp_path: Path) -> None:
    # Artifact creation
    a = Artifact(tmp_path / 'test')
    assert not (tmp_path / 'test').exists()

    # Number assignment
    a.number = 4.5
    assert (tmp_path / 'test' / 'number.h5').is_file()
    assert isinstance(a.number, h5.Dataset)
    assert np.array_equal(a.number, 4.5)

    # String assignment
    a.string = b'test'
    assert (tmp_path / 'test' / 'string.h5').is_file()
    assert isinstance(a.string, h5.Dataset)
    assert np.array_equal(a.string, b'test')

    # List assignment
    a.list = [1, 2, 3]
    assert (tmp_path / 'test' / 'list.h5').is_file()
    assert isinstance(a.list, h5.Dataset)
    assert np.array_equal(a.list, [1, 2, 3])

    # Array assignment
    a.array = np.ones((5, 4))
    assert (tmp_path / 'test' / 'array.h5').is_file()
    assert isinstance(a.array, h5.Dataset)
    assert np.array_equal(a.array, np.ones((5, 4)))

    # Path assignment
    ...

    # Dictionary assignment
    a.dict = dict(a=[1, 2, 3], b=dict(c=[4], d=[5, 6]))
    assert (tmp_path / 'test' / 'dict/a.h5').is_file()
    assert (tmp_path / 'test' / 'dict/b/c.h5').is_file()
    assert (tmp_path / 'test' / 'dict/b/d.h5').is_file()
    assert isinstance(a.dict, Artifact)
    assert isinstance(a.dict.a, h5.Dataset)
    assert isinstance(a.dict.b, Artifact)
    assert isinstance(a.dict.b.c, h5.Dataset)
    assert isinstance(a.dict.b.d, h5.Dataset)
    assert np.array_equal(a.dict.a, [1, 2, 3])
    assert np.array_equal(a.dict.b.c, [4])
    assert np.array_equal(a.dict.b.d, [5, 6])

    # Artifact assignment
    ...

    # Collection methods
    assert len(a) == 5
    for key in ['number', 'string', 'list', 'array', 'dict']:
        assert key in a
        assert key in list(a)


def test_artifact_subscript_syntax(tmp_path: Path) -> None:
    ...


def test_artifact_entry_extension(tmp_path: Path) -> None:
    ...


def test_artifact_entry_deletion(tmp_path: Path) -> None:
    ...


def test_artifact_build_customization(tmp_path: Path) -> None:
    '''
    - Calling `build`, passing in `conf`
    - Calling `build` without passing in `conf`
    '''


def test_artifact_resolution(tmp_path: Path) -> None:
    '''
    - Case 1: (path_given, exists)
    - Case 2: (path_given, does_not_exists)
    - Case 3: (spec_given, exists)
    - Case 4: (spec_given, does_not_exist)
    - Case 5: (path_given, spec_given, exists_and_matches)
    - Case 6: (path_given, spec_given, exists_and_does_not_match)
    - Case 7: (path_given, spec_given, does_not_exist)
    '''
