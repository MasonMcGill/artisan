import json, gc, pickle, shutil
from glob import glob
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Callable, Dict, List, NamedTuple, Type, Union
from typing_extensions import Protocol

import pytest
from hypothesis import given
from hypothesis.strategies import (
    SearchStrategy, binary, builds,
    lists, one_of, sampled_from)

from artisan import (
    Artifact, DynamicArtifact, Namespace as Ns,
    ProxyArtifactField, recover)
from artisan._targets import active_scope
from artisan._artifacts import active_builder, active_root, default_builder


#-- File operations ------------------------------------------------------------

FileOperation = Callable[[Path, Artifact], None]; \
    '''
    An operation that can be performed on a `Path` object corresponding to a
    directory, and an artifact corresponding to a different directory. The
    operation should have the same effect on both directories.
    '''


class Write(NamedTuple):
    '''
    An operation that writes bytes to a file.
    '''
    key: str
    ext: str
    content: bytes

    def __call__(self, raw_path: Path, artifact: Artifact) -> None:
        dst = raw_path / (self.key + self.ext)
        if dst.exists(): dst.unlink()
        dst.write_bytes(self.content)
        setattr(artifact, self.key, dst)


class FullDeletion(NamedTuple):
    '''
    An operation that deletes all files matching `{dir_path}/{key}*`.
    '''
    key: str

    def __call__(self, raw_path: Path, artifact: Artifact) -> None:
        for path in glob(f'{raw_path}/{self.key}*'):
            Path(path).unlink()
        delattr(artifact, self.key)


class PartialDeletion(NamedTuple):
    '''
    An operation that deletes a single file, if it exists.
    '''
    key: str
    ext: str

    def __call__(self, raw_path: Path, artifact: Artifact) -> None:
        for path in glob(f'{raw_path}/{self.key}{self.ext}'):
            Path(path).unlink()
        for path in glob(f'{artifact._path_}/{self.key}{self.ext}'):
            Path(path).unlink()


def file_operations() -> SearchStrategy[FileOperation]:
    '''
    Return a search strategy that samples file operations.
    '''
    return one_of(
        builds(Write,
            key = sampled_from(['f0', 'f1', 'f2']),
            ext = sampled_from(['', '.bin', '.data']),
            content = binary()),
        builds(FullDeletion,
            key = sampled_from(['f0', 'f1', 'f2'])),
        builds(PartialDeletion,
            key = sampled_from(['f0', 'f1', 'f2']),
            ext = sampled_from(['', '.bin', '.data'])))



#-- Artifact content checking --------------------------------------------------

def assert_matches(artifact: Artifact,
                   path: Path,
                   spec: Ns,
                   event_types: List[str],
                   mode: str,
                   **attrs: object) -> None:
    '''
    Assert that an artifact matches the given criteria.
    '''
    assert artifact._path_ == path
    assert artifact.__fspath__() == str(path)
    assert artifact._meta_.spec == spec
    assert [e.type for e in artifact._meta_.events] == event_types
    assert artifact._mode_ == mode
    assert set(public_attrs(artifact)) == set(attrs)

    for key, value in attrs.items():
        assert len(glob(f'{path}/{key}*')) > 0
        assert getattr(artifact, key) == value


def public_attrs(obj: object) -> List[str]:
    '''
    Return a list of an object's public attributes.
    '''
    attrs = set(dir(obj)) - set(dir(type(obj)))
    return [name for name in attrs if name[0] != '_']



#-- Tests ----------------------------------------------------------------------

@given(lists(file_operations()))
def test_file_operations(ops: List[FileOperation]) -> None:
    '''
    Test reading, writing, and deleting binary files.
    '''
    with TemporaryDirectory() as root:
        Path(root, 'artifact').mkdir()
        Path(root, 'raw_path').mkdir()
        artifact = recover(Artifact, Path(root, 'artifact'), 'write')
        raw_path = Path(root, 'raw_path')

        for op in ops:
            op(raw_path, artifact)

            for entry in raw_path.iterdir():
                assert hasattr(artifact, entry.stem)
                assert entry.stem in dir(artifact)

            for key in public_attrs(artifact):
                entry = getattr(artifact, key)
                target = raw_path / (key + entry.suffix)
                assert (entry.read_bytes() == target.read_bytes())


def test_recovery(tmp_path) -> None:
    '''
    Test `recover`.
    '''
    path = tmp_path / 'artifact'
    path.mkdir()
    assert type(recover(Artifact, path)) is DynamicArtifact
    assert type(recover(DynamicArtifact, path)) is DynamicArtifact
    assert recover(Artifact, path)._path_ == path
    assert recover(Artifact, path)._mode_ == 'read-sync'
    assert recover(Artifact, path, 'write')._mode_ == 'write'


def test_artifact_creation_and_search() -> None:
    '''
    Test that creating an artifact stores its attributes persistently, and that
    existing artifacts are found, rather than rebuilt, when they are
    instantiated.
    '''
    gc.collect()

    class Parent(Artifact, abstract=True):
        x: int
        y: float

    class ChildA(Parent):
        class Spec(Protocol):
            scale: int

        def __init__(self, spec: Spec) -> None:
            self.x = spec.scale * 1
            self.y = spec.scale * 2.3

    class ChildB(Parent):
        class Spec(Protocol):
            x_scale: int
            y_scale: float

        def __init__(self, spec: Spec) -> None:
            self.x = spec.x_scale * 4
            self.y = spec.y_scale * 5.6

    scope = dict(
        Parent = Parent,
        ChildA = ChildA,
        ChildB = ChildB)

    with TemporaryDirectory() as root:
        root_token = active_root.set(Path(root))
        scope_token = active_scope.set(scope)
        try:
            assert_matches(
                artifact = Parent(Ns(type='ChildA', scale=1)),
                path = Path(root, 'ChildA_0000'),
                spec = Ns(type='ChildA', scale=1),
                event_types = ['Start', 'Success'],
                mode = 'read-sync',
                x = 1,
                y = 2.3)

            assert_matches(
                artifact = ChildA(Ns(scale=2)),
                path = Path(root, 'ChildA_0001'),
                spec = Ns(type='ChildA', scale=2),
                event_types = ['Start', 'Success'],
                mode = 'read-sync',
                x = 2,
                y = 4.6)

            assert_matches(
                artifact = ChildA(Ns(scale=1)),
                path = Path(root, 'ChildA_0000'),
                spec = Ns(type='ChildA', scale=1),
                event_types = ['Start', 'Success'],
                mode = 'read-sync',
                x = 1,
                y = 2.3)

            assert_matches(
                artifact = Parent(Ns(type='ChildB', x_scale=1, y_scale=2.0)),
                path = Path(root, 'ChildB_0000'),
                spec = Ns(type='ChildB', x_scale=1, y_scale=2.0),
                event_types = ['Start', 'Success'],
                mode = 'read-sync',
                x = 4,
                y = 11.2)

            assert_matches(
                artifact = ChildB(Ns(x_scale=1, y_scale=1.0)),
                path = Path(root, 'ChildB_0001'),
                spec = Ns(type='ChildB', x_scale=1, y_scale=1.0),
                event_types = ['Start', 'Success'],
                mode = 'read-sync',
                x = 4,
                y = 5.6)

            assert_matches(
                artifact = Parent(Ns(type='ChildB', x_scale=1, y_scale=1.0)),
                path = Path(root, 'ChildB_0001'),
                spec = Ns(type='ChildB', x_scale=1, y_scale=1.0),
                event_types = ['Start', 'Success'],
                mode = 'read-sync',
                x = 4,
                y = 5.6)
        finally:
            active_root.reset(root_token)
            active_scope.reset(scope_token)


def test_access_modes() -> None:
    '''
    Test using artifacts in "read-sync", "read-async", and "write" mode.
    '''
    def log(artifact: Artifact, event: str) -> None:
        meta_path = artifact / '_meta_.json'
        meta = (json.loads(meta_path.read_text())
                if meta_path.exists()
                else {'events': []})
        meta['events'].append({'type': event})
        meta_path.write_text(json.dumps(meta))

    with TemporaryDirectory() as root:
        Path(root, 'rs').mkdir()
        Path(root, 'ra').mkdir()
        Path(root, 'w').mkdir()

        rs_artifact = recover(Artifact, f'{root}/rs', 'write')
        ra_artifact = recover(Artifact, f'{root}/ra', 'write')
        w_artifact = recover(Artifact, f'{root}/w', 'write')

        log(rs_artifact, 'Start')
        rs_artifact.x = 1
        log(rs_artifact, 'Success')
        rs_artifact._mode_ = 'read-sync'
        assert rs_artifact.x == 1
        with pytest.raises(AttributeError):
            rs_artifact.y

        log(ra_artifact, 'Start')
        ra_artifact.x = 2
        ra_artifact._mode_ = 'read-async'
        assert ra_artifact.x == 2
        log(ra_artifact, 'Success')
        with pytest.raises(AttributeError):
            ra_artifact.y

        log(w_artifact, 'Start')
        w_artifact.x = 3
        assert w_artifact.x == 3
        assert isinstance(w_artifact.y, ProxyArtifactField)


def test_custom_readers_and_writers() -> None:
    '''
    Test overriding `<cls>._readers_` and `<cls>._writers_`.
    '''
    gc.collect()

    def read_pickle_file(path: Path) -> object:
        with open(path, 'rb') as f:
            return pickle.load(f)

    def write_object_as_pickle(path: Path, data: object) -> str:
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        return '.pickle'

    class TestArtifact(Artifact):
        _readers_ = [read_pickle_file]
        _writers_ = [write_object_as_pickle]

        def __init__(self, spec: object) -> None:
            self.x = (('ex',),)
            self.y = {'why'}

    with TemporaryDirectory() as root:
        artifact = TestArtifact(Ns(_path_=f'{root}/artifact'))
        assert artifact.x == (('ex',),)
        assert artifact.y == {'why'}


def test_custom_builders() -> None:
    '''
    Test using a custom artifact builder.
    '''
    gc.collect()

    def build(artifact: Artifact, spec: object) -> None:
        default_builder(artifact, spec)
        mode = artifact._mode_
        artifact._mode_ = 'write'
        artifact.c = 'see'
        artifact._mode_ = mode

    class TestArtifact(Artifact):
        def __init__(self, spec: object) -> None:
            self.a = 'eh'
            self.b = 'be'

    with TemporaryDirectory() as root:
        root_token = active_root.set(Path(root))
        scope_token = active_scope.set({'TestArtifact': TestArtifact})
        builder_token = active_builder.set(build)
        try:
            assert_matches(
                artifact = TestArtifact(Ns()),
                path = Path(root, 'TestArtifact_0000'),
                spec = Ns(type='TestArtifact'),
                event_types = ['Start', 'Success'],
                mode = 'read-sync',
                a = 'eh',
                b = 'be',
                c = 'see')
        finally:
            active_root.reset(root_token)
            active_scope.reset(scope_token)
            active_builder.reset(builder_token)


def test_dynamic_artifacts() -> None:
    '''
    Test the `DynamicArtifact` class.
    '''
    with TemporaryDirectory() as root:
        artifact = recover(DynamicArtifact[Any], root, 'write')
        assert list(artifact) == []

        artifact['a'] = 0.1
        assert 'a' in artifact
        assert len(artifact) == 1
        assert list(artifact) == ['a']
        assert artifact['a'] == 0.1

        del artifact['a']
        assert 'a' not in artifact
        assert len(artifact) == 0
        assert list(artifact) == []

        artifact['b'] = 'bee'
        assert 'b' in artifact
        assert len(artifact) == 1
        assert list(artifact) == ['b']
        assert artifact['b'] == 'bee'


def test_proxy_fields() -> None:
    '''
    Test the `ProxyArtifactField` class.
    '''
    with TemporaryDirectory() as root:
        artifact = recover(Artifact, root, 'write')
        assert isinstance(artifact.a, ProxyArtifactField)

        a_proxy = artifact.a
        artifact.a.b = 12
        assert artifact.a.b == 12

        del a_proxy.b
        assert public_attrs(artifact.a) == []

        artifact.x.append(10)
        assert artifact.x == [10]

        artifact.y.z.extend([2, 4, 6])
        assert artifact.y.z == [2, 4, 6]
