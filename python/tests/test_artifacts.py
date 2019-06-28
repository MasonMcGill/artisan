from pathlib import Path
from typing import List

import h5py as h5
import numpy as np
import pytest

from artisan._artifacts import Artifact, set_root_dir

#-- Helper functions ----------------------------------------------------------

def data_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(np.random.rand(3).tostring())
    return path


def data_file_concat(path: Path, args: List[Path]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b''.join(a.read_bytes() for a in args))
    return path


def assert_artifact_equals(artifact: Artifact, target: dict) -> None:
    if '__type__' in target:
        assert isinstance(artifact, target.pop('__type__'))
    if '__path__' in target:
        assert artifact.path == target.pop('__path__')
    if '__conf__' in target:
        assert artifact.conf == target.pop('__conf__')
    if '__meta__' in target:
        assert artifact.meta == target.pop('__meta__')

    assert len(artifact) == len(target)
    assert len(list(artifact)) == len(target)

    for k, v in target.items():
        assert k in artifact
        assert k in list(artifact)
        assert hasattr(artifact, k)

        if isinstance(v, dict):
            assert isinstance(artifact[k], Artifact)
            assert isinstance(getattr(artifact, k), Artifact)
            assert_artifact_equals(artifact[k], v)
            assert_artifact_equals(getattr(artifact, k), v)

        elif isinstance(v, Path):
            k_mod = k.replace('.', '__')
            assert (artifact.path / k).is_file()
            assert isinstance(artifact[k], Path)
            assert isinstance(getattr(artifact, k), Path)
            assert artifact[k].read_bytes() == v.read_bytes()
            assert getattr(artifact, k).read_bytes() == v.read_bytes()
            assert getattr(artifact, k_mod).read_bytes() == v.read_bytes()

        else:
            assert (artifact.path / k).with_suffix('.h5').is_file()
            assert isinstance(artifact[k], h5.Dataset)
            assert isinstance(getattr(artifact, k), h5.Dataset)
            assert np.array_equal(artifact[k][()], v)
            assert np.array_equal(getattr(artifact, k)[()], v)
            assert artifact[k].dtype == np.asarray(v).dtype
            assert getattr(artifact, k).dtype == np.asarray(v).dtype

#-- [Base class tests] Empty artifacts ----------------------------------------

def test_empty_artifact_with_existing_dir(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    assert_artifact_equals(a, dict(
        __path__ = tmp_path,
        __conf__ = {},
        __meta__ = {'spec': None, 'status': 'done'}
    ))
    assert isinstance(a.nonexistent_entry, Artifact)


def test_empty_artifact_with_nonexistent_dir(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'new_dir')
    assert_artifact_equals(a, dict(
        __path__ = tmp_path / 'new_dir',
        __conf__ = {},
        __meta__ = {'spec': None, 'status': 'done'}
    ))
    assert isinstance(a.nonexistent_entry, Artifact)
    assert not (tmp_path / 'new_dir').exists()

#-- [Base class tests] Entry assignment ---------------------------------------

def test_float_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = 1.5
    a.b = 2.5
    a['c'] = 3.5
    a['c'] = 4.5
    assert_artifact_equals(a, {'b': 2.5, 'c': 4.5})


def test_byte_string_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = b'bee'
    a.b = b'buzz'
    a['c'] = b'sea'
    a['c'] = b'ahoy!'
    assert_artifact_equals(a, {'b': b'buzz', 'c': b'ahoy!'})


def test_list_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = [1, 2, 3]
    a.b = [4, 5, 6]
    a['c'] = [[7, 8], [9, 10]]
    a['c'] = [[11, 12, 13], [14, 15, 16]]
    assert_artifact_equals(a, {
        'b': [4, 5, 6],
        'c': [[11, 12, 13], [14, 15, 16]]
    })


def test_array_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = np.ones((2, 3), dtype='float32')
    a.b = np.zeros((4, 5, 6), dtype='float32')
    a['c'] = np.ones((4, 5, 6), dtype='float32')
    a['c'] = np.ones((2, 3), dtype='uint16')
    assert_artifact_equals(a, {
        'b': np.zeros((4, 5, 6), dtype='float32'),
        'c': np.ones((2, 3), dtype='uint16')
    })


def test_path_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'artifact')
    a.b__bin = data_file(tmp_path / 'b0.bin')
    a.b__bin = data_file(tmp_path / 'b1.bin')
    a['c.bin'] = data_file(tmp_path / 'c0.bin')
    a['c.bin'] = data_file(tmp_path / 'c1.bin')
    assert_artifact_equals(a, {
        'b.bin': tmp_path / 'b1.bin',
        'c.bin': tmp_path / 'c1.bin'
    })


def test_dict_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.dict = dict(a=[1, 2, 3], b=dict(c=[4], d=[5, 6]))
    assert_artifact_equals(a, {
        'dict': {
            'a': [1, 2, 3],
            'b': {'c': [4], 'd': [5, 6]}
        }
    })


def test_artifact_assignment(tmp_path: Path) -> None:
    a_src = Artifact(tmp_path / 'a_src')
    a_src.b.c = b'bee sea'
    a_src.d.e = [1, 2, 3, 4]
    a_src.f.g__bin = data_file(tmp_path / 'effigy.bin')
    a_dst = Artifact(tmp_path / 'a_dst')
    a_dst.a = a_src
    assert_artifact_equals(a_dst, {
        'a': {
            'b': {'c': b'bee sea'},
            'd': {'e': [1, 2, 3, 4]},
            'f': {'g.bin': tmp_path / 'effigy.bin'}
        }
    })

#-- [Base class tests] Entry extension ----------------------------------------

def test_list_extension(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.extend('b', [[7, 8], [9, 10]])
    a.extend('b', [[11, 12]])
    assert_artifact_equals(a, {
        'b': [[7, 8], [9, 10], [11, 12]]
    })


def test_array_extension(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.extend('b', np.uint16([[7, 8], [9, 10]]))
    a.extend('b', np.uint16([[11, 12]]))
    assert_artifact_equals(a, {
        'b': np.uint16([[7, 8], [9, 10], [11, 12]])
    })


def test_path_extension(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'a')
    a.extend('b.bin', data_file(tmp_path / 'b0.bin'))
    a.extend('b.bin', data_file(tmp_path / 'b1.bin'))
    assert_artifact_equals(a, {
        'b.bin': data_file_concat(tmp_path / 'b2.bin', [
            tmp_path / 'b0.bin', tmp_path / 'b1.bin'
        ])
    })


def test_dict_extension(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'a')
    a.extend('b', {
        'c': np.empty((0, 2), dtype='uint16'),
        'd.bin': data_file(tmp_path / 'd0.bin'),
        'e': {'f': [0.1, 0.2]}
    })
    a.extend('b', {
        'c': np.uint16([[1, 2], [3, 4]]),
        'd.bin': data_file(tmp_path / 'd1.bin'),
        'e': {'f': [0.3, 0.4, 0.5]}
    })
    assert_artifact_equals(a, {
        'b': {
            'c': np.uint16([[1, 2], [3, 4]]),
            'd.bin': data_file_concat(tmp_path / 'd2.bin', [
                tmp_path / 'd0.bin', tmp_path / 'd1.bin']
            ),
            'e': {'f': [0.1, 0.2, 0.3, 0.4, 0.5]}
        }
    })


def test_artifact_extension(tmp_path: Path) -> None:
    a0 = Artifact(tmp_path / 'a0')
    a0.b = [b'hello']
    a0.c__bin = data_file(tmp_path / 'c0.bin')
    a0.d = {'e': [[0.0, 1.0]], 'f.bin': data_file(tmp_path / 'f0.bin')}

    a1 = Artifact(tmp_path / 'a1')
    a1.b = [b'good', b'bye']
    a1.c__bin = data_file(tmp_path / 'c1.bin')
    a1.d = {'e': np.empty((0, 2)), 'f.bin': data_file(tmp_path / 'f1.bin')}

    a2 = Artifact(tmp_path / 'a2')
    a2.extend('subartifact', a0)
    a2.extend('subartifact', a1)

    assert_artifact_equals(a2, {
        'subartifact': {
            'b': [b'hello', b'good', b'bye'],
            'c.bin': data_file_concat(tmp_path / 'c2.bin', [
                tmp_path / 'c0.bin', tmp_path / 'c1.bin']
            ),
            'd': {
                'e': [[0.0, 1.0]],
                'f.bin': data_file_concat(tmp_path / 'f2.bin', [
                    tmp_path / 'f0.bin', tmp_path / 'f1.bin']
                )
            }
        }
    })

#-- [Base class tests] Entry deletion -----------------------------------------

def test_array_file_deletion(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'a')
    a.b = [1, 2, 3]
    a.c = b'four five six'
    a.d = [7, 8]
    a.e = {'blue': b'jeans'}
    a.f__bin = data_file(tmp_path / 'data.bin')
    del a.b
    del a['c']
    assert_artifact_equals(a, {
        'd': [7, 8],
        'e': {'blue': b'jeans'},
        'f.bin': tmp_path / 'data.bin'
    })


def test_opaque_file_deletion(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'a')
    a.b__bin = data_file(tmp_path / 'b.bin')
    a.c__bin = data_file(tmp_path / 'c.bin')
    a.d = [7, 8]
    a.e = {'blue': b'jeans'}
    a.f__bin = data_file(tmp_path / 'data.bin')
    del a.b__bin
    del a['c.bin']
    assert_artifact_equals(a, {
        'd': [7, 8],
        'e': {'blue': b'jeans'},
        'f.bin': tmp_path / 'data.bin'
    })


def test_artifact_deletion(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'a')
    a.b = {'aa': {'bb': 0, 'cc': 1}}
    a.c = {'dd': {'ee': [2, 3, 4]}}
    a.d = [7, 8]
    a.e = {'blue': b'jeans'}
    a.f__bin = data_file(tmp_path / 'data.bin')
    del a.b
    del a['c']
    assert_artifact_equals(a, {
        'd': [7, 8],
        'e': {'blue': b'jeans'},
        'f.bin': tmp_path / 'data.bin'
    })

#-- [Subclass tests] Construction ---------------------------------------------

class CustomArtifact(Artifact):
    n_calls = 0
    def build(self, conf) -> None:
        CustomArtifact.n_calls += 1
        self.zeros = np.zeros(conf.n_zeros)
        self.ones = np.ones(conf.n_ones)


def test_construction_from_path(tmp_path: Path) -> None:
    # Setup
    set_root_dir(tmp_path)
    CustomArtifact.n_calls = 0
    a0 = CustomArtifact(n_zeros=2, n_ones=3)

    # Case 1: (path_given, exists)
    a1 = CustomArtifact(a0.path)
    a2 = CustomArtifact(f'{a0.path}')
    a3 = CustomArtifact(f'@/{a0.path.name}')
    assert_artifact_equals(a1, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert_artifact_equals(a2, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert_artifact_equals(a3, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert CustomArtifact.n_calls == 1

    # Case 2: (path_given, does_not_exists)
    with pytest.raises(FileNotFoundError):
        CustomArtifact(tmp_path / 'invalid_path')

    # Cleanup
    set_root_dir(Path('.'))


def test_construction_from_conf(tmp_path: Path) -> None:
    # Setup
    set_root_dir(tmp_path)
    CustomArtifact.n_calls = 0
    a0 = CustomArtifact(n_zeros=2, n_ones=3)

    # Case 1: (conf_given, exists)
    a1 = CustomArtifact(n_zeros=2, n_ones=3)
    a2 = CustomArtifact(dict(n_zeros=2, n_ones=3))
    assert_artifact_equals(a1, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert_artifact_equals(a2, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert a1.path == a0.path
    assert a2.path == a0.path
    assert CustomArtifact.n_calls == 1

    # Case 2: (conf_given, does_not_exist)
    a3 = CustomArtifact(n_zeros=2, n_ones=4)
    a4 = CustomArtifact(dict(n_zeros=1, n_ones=3))
    assert_artifact_equals(a3, {'zeros': np.zeros(2), 'ones': np.ones(4)})
    assert_artifact_equals(a4, {'zeros': np.zeros(1), 'ones': np.ones(3)})
    assert CustomArtifact.n_calls == 3

    # Cleanup
    set_root_dir(Path('.'))


def test_construction_from_path_and_conf(tmp_path: Path) -> None:
    # Setup
    set_root_dir(tmp_path)
    CustomArtifact.n_calls = 0
    a0 = CustomArtifact(n_zeros=2, n_ones=3)

    # Case 1: (path_given, conf_given, exists_and_matches)
    a1 = CustomArtifact(a0.path, n_zeros=2, n_ones=3)
    a2 = CustomArtifact(a0.path, dict(n_zeros=2, n_ones=3))
    a3 = CustomArtifact(f'@/{a0.path.name}', n_zeros=2, n_ones=3)
    assert_artifact_equals(a1, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert_artifact_equals(a2, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert_artifact_equals(a3, {'zeros': np.zeros(2), 'ones': np.ones(3)})
    assert a1.path == a0.path
    assert a2.path == a0.path
    assert a3.path == a0.path
    assert CustomArtifact.n_calls == 1

    # Case 2: (path_given, conf_given, exists_and_does_not_match)
    with pytest.raises(FileExistsError):
        CustomArtifact(a0.path, n_zeros=1, n_ones=3)
    with pytest.raises(FileExistsError):
        CustomArtifact(a0.path, dict(n_zeros=1, n_ones=4))
    with pytest.raises(FileExistsError):
        CustomArtifact(f'@/{a0.path.name}', n_zeros=2, n_ones=4)
    assert CustomArtifact.n_calls == 1

    # Case 3: (path_given, conf_given, does_not_exist)
    a4 = CustomArtifact(tmp_path / 'a4', n_zeros=1, n_ones=3)
    a5 = CustomArtifact(tmp_path / 'a5', dict(n_zeros=1, n_ones=4))
    a6 = CustomArtifact('@/a6', n_zeros=2, n_ones=4)
    assert_artifact_equals(a4, {'zeros': np.zeros(1), 'ones': np.ones(3)})
    assert_artifact_equals(a5, {'zeros': np.zeros(1), 'ones': np.ones(4)})
    assert_artifact_equals(a6, {'zeros': np.zeros(2), 'ones': np.ones(4)})
    assert a4.path == tmp_path / 'a4'
    assert a5.path == tmp_path / 'a5'
    assert a6.path == tmp_path / 'a6'
    assert CustomArtifact.n_calls == 4

    # Cleanup
    set_root_dir(Path('.'))

#-- [Subclass tests] Build customization --------------------------------------

class ArtifactWithUnaryBuild(Artifact):
    def build(self) -> None:
        self.field = self.conf.prop


class ArtifactWithBinaryBuild(Artifact):
    def build(self, conf) -> None:
        self.field = conf.prop


def test_build_customization(tmp_path: Path) -> None:
    a_unary = ArtifactWithUnaryBuild(tmp_path / 'unary', prop=10)
    a_binary = ArtifactWithUnaryBuild(tmp_path / 'binary', prop=10)
    assert a_unary.field[()] == 10
    assert a_binary.field[()] == 10
