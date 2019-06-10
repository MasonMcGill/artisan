import itertools
import json
from pathlib import Path
import shutil
from time import sleep
from typing import (
    Any, Iterator, List, Mapping, MutableMapping,
    Optional, Tuple, cast
)
from typing_extensions import Protocol

import h5py as h5
import numpy as np
from ruamel import yaml

from ._configurables import Configurable, schema
from ._global_conf import get_conf
from ._namespaces import namespacify, Namespace

__all__ = ['Artifact', 'ArrayFile', 'EncodedFile', 'write_global_meta']

#-- Static type definitions ---------------------------------------------------

from pathlib import Path as EncodedFile

class ArrayFile(Protocol):
    def __get__(self, obj: object, type_: Optional[type]) -> h5.Dataset: ...
    def __set__(self, obj: object, val: object) -> None: ...

#-- Artifacts -----------------------------------------------------------------

class Artifact(Configurable):
    '''
    An array- and metadata-friendly view into a directory

    Arguments:
        path (Path|str): The path at which the artifact is, or should be,
            stored
        conf (Mapping[str, object]): The subtype-specific configuration,
            optionally including a "type" field indicating what type of
            artifact to construct

    Constructors:
        - Artifact(conf: *Mapping[str, object]*)
        - Artifact(**conf_elem: *object*)
        - Artifact(path: *Path|str*)
        - Artifact(path: *Path|str*, conf: *Mapping[str, object]*)
        - Artifact(path: *Path|str*, **conf_elem: *object*)

    Fields:
        - **path** (*Path*): The path to the root of the file tree backing this \
            artifact
        - **meta** (*Mapping[str, object]*): The metadata stored in \
            `{self.path}/_meta.yaml`

    Type lookup is performed in the current scope, which can be modified via
    the global configuration API.

    Reading/writing/extending/deleting `ArrayFile`, `EncodedFile`, and
    `Artifact` fields is supported.
    '''
    path: Path

    def __new__(cls, *args: object, **kwargs: object) -> Any:
        path, conf = _parse_artifact_args(args, kwargs)
        if path is not None and conf is None:
            return _artifact_from_path(cls, _resolve_path(path))
        elif path is None and conf is not None:
            return _artifact_from_conf(cls, conf)
        elif path is not None and conf is not None:
            return _artifact_from_path_and_conf(cls, _resolve_path(path), conf)

    @property
    def meta(self) -> Namespace:
        '''
        The metadata stored in `{self.path}/_meta.yaml`
        '''
        return _read_meta(self.path)

    #-- MutableMapping methods ----------------------------

    def __len__(self) -> int:
        '''
        Returns the number of public files in `self.path`

        Non-public files (files whose names start with "_") are not counted.
        '''
        return sum(1 for _ in self.path.glob('[!_]*'))

    def __iter__(self) -> Iterator[str]:
        '''
        Yields field names corresponding to the public files in `self.path`

        Entries Artisan understands (subdirectories and HDF5 files) are yielded
        without extensions. Non-public files (files whose names start with "_")
        are ignored.
        '''
        for p in self.path.glob('[!_]*'):
            yield p.name[:-3] if p.suffix == '.h5' else p.name

    def keys(self) -> Iterator[str]:
        return self.__iter__()

    def __getitem__(self, key: str) -> Any:
        '''
        Returns an `ArrayFile`, `EncodedFile`, or `Artifact` corresponding to
        `self.path/key`

        HDF5 files are returned as `ArrayFile`s, other files are returned as
        `EncodedFile`s, and directories and nonexistent entries are returned as
        (possibly empty) `Artifact`s.

        Attribute access syntax is also supported, and occurrences of "__" in
        `key` are transformed into ".", to support accessing encoded files as
        attributes (i.e. `artifact['name.ext']` is equivalent to
        `artifact.name__ext`).
        '''
        path = self.path / key.replace('__', '.')

        # Return an array.
        if Path(f'{path}.h5').is_file():
            return _read_h5(path.with_suffix('.h5'))

        # Return the path to a file.
        elif path.is_file():
            return path

         # Return a subrecord
        else:
            return Artifact(path)

    def __setitem__(self, key: str, val: object) -> None:
        '''
        Writes an `ArrayFile`, `EncodedFile`, or `Artifact` to `self.path/key`

        `np.ndarray`-like objects are written as `ArrayFiles`, `Path`-like
        objects are written as `EncodedFile`s, and string-keyed mappings are
        written as subartifacts.

        Attribute access syntax is also supported, and occurrences of "__" in
        `key` are transformed into ".", to support accessing encoded files as
        attributes (i.e. `artifact['name.ext'] = val` is equivalent to
        `artifact.name__ext = val`).
        '''
        path = self.path / key.replace('__', '.')

        # Copy an existing file.
        if isinstance(val, Path):
            assert path.suffix != ''
            _copy_file(path, val)

        # Write a subartifact.
        elif isinstance(val, (Mapping, Artifact)):
            assert path.suffix == ''
            MutableMapping.update(Artifact(path), val) # type: ignore

        # Write an array.
        else:
            assert path.suffix == ''
            _write_h5(path.with_suffix('.h5'), val)

    def __delitem__(self, key: str) -> None:
        '''
        Deletes the entry at `self.path/key`

        Attribute access syntax is also supported, and occurrences of "__" in
        `key` are transformed into ".", to support accessing encoded files as
        attributes (i.e. `del artifact['name.ext']` is equivalent to
        `del artifact.name__ext`).
        '''
        path = self.path / key.replace('__', '.')
        shutil.rmtree(path, ignore_errors=True)

    def extend(self, key: str, val: object) -> None:
        '''
        Extends an `ArrayFile`, `EncodedFile`, or `Artifact` at `self.path/key`

        Extending `ArrayFile`s performs concatenation along the first axis,
        extending `EncodedFile`s performs byte-level concatenation, and
        extending subartifacts extends their fields.

        Files corresponding to `self[key]` are created if they do not already
        exist.
        '''
        path = self.path / key

        # Append an existing file.
        if isinstance(val, Path):
            assert path.suffix != ''
            _extend_file(path, val)

        # Append a subartifact.
        elif isinstance(val, (Mapping, Artifact)):
            assert path.suffix == ''
            for k, v in val.items():
                Artifact(path).extend(k, v)

        # Append an array.
        else:
            assert path.suffix == ''
            _extend_h5(path.with_suffix('.h5'), val)

    #-- Attribute-style element access --------------------

    def __getattr__(self, key: str) -> Any:
        return self.__getitem__(key)

    def __setattr__(self, key: str, value: object) -> None:
        self.__setitem__(key, value)

    def __delattr__(self, key: str) -> None:
        self.__delitem__(key)

    #-- Attribute preemption, for REPL autocompletion -----

    def __getattribute__(self, key: str) -> Any:
        if key in object.__getattribute__(self, '_cached_keys'):
            try:
                object.__setattr__(self, key, self[key])
            except KeyError:
                object.__delattr__(self, key)
                object.__getattribute__(self, '_cached_keys').remove(key)
        return object.__getattribute__(self, key)

    def __dir__(self) -> List[str]:
        for key in self._cached_keys:
            object.__delattr__(self, key)
        self._cached_keys.clear()

        for key in set(self).difference(object.__dir__(self)):
            object.__setattr__(self, key, self[key])
            self._cached_keys.add(key)

        return cast(list, object.__dir__(self))

#-- Artifact construction -----------------------------------------------------

def _parse_artifact_args(
        args: Tuple[object, ...],
        kwargs: Mapping[str, object]
    ) -> Tuple[
        Optional[Path],
        Optional[Mapping[str, object]]
    ]:
    '''
    Return `(path, conf)` or raise an error.
    '''
    # (conf)
    if (len(args) == 1
        and isinstance(args[0], Mapping)
        and len(kwargs) == 0):
        return None, dict(args[0])

    # (**conf)
    elif (len(args) == 0
          and len(kwargs) > 0):
        return None, kwargs

    # (path)
    elif (len(args) == 1
          and isinstance(args[0], (str, Path))
          and len(kwargs) == 0):
        return Path(args[0]), None

    # (path, conf)
    elif (len(args) == 2
          and isinstance(args[0], (str, Path))
          and isinstance(args[1], Mapping)
          and len(kwargs) == 0):
        return Path(args[0]), dict(args[1])

    # (path, **conf)
    elif (len(args) == 1
          and isinstance(args[0], (str, Path))
          and len(kwargs) > 0):
        return Path(args[0]), kwargs

    # <invalid signature>
    else:
        raise TypeError(
            'Invalid argument types for the `Artifact` constructor.\n'
            'Valid signatures:\n'
            '\n'
            '    - Artifact(conf: Mapping[str, object])\n'
            '    - Artifact(**conf_elem: object)\n'
            '    - Artifact(path: Path|str)\n'
            '    - Artifact(path: Path|str, conf: Mapping[str, object])\n'
            '    - Artifact(path: Path|str, **conf_elem: object)\n'
        )


def _artifact_from_path(cls: type, path: Path) -> Artifact:
    '''
    Return an artifact corresponding to the file tree at `path`.

    An error is raised if the type recorded in `_meta.yaml`, if any, is not a
    subtype of `cls`.
    '''
    spec = _read_meta(path).spec or {}
    written_type = get_conf().scope.get(spec.get('type', None), None)

    if written_type is not None and not issubclass(written_type, cls):
        raise FileExistsError(
            f'{path} is a {written_type.__module__}.{written_type.__qualname__}'
            f', not a {cls.__module__}.{cls.__qualname__}.'
        )

    artifact = cast(Artifact, Configurable.__new__(cls, spec))
    object.__setattr__(artifact, '_cached_keys', set())
    object.__setattr__(artifact, 'path', path)
    return artifact


def _artifact_from_conf(cls: type, conf: Mapping[str, object]) -> Artifact:
    '''
    Find or build an artifact with the given type and configuration.
    '''
    artifact = cast(Artifact, Configurable.__new__(cls, conf))
    object.__setattr__(artifact, '_cached_keys', set())
    spec = Namespace(type=_identify(type(artifact)), **artifact.conf)

    for path in Path(get_conf().root_dir).glob('*'):
        meta = _read_meta(path)
        if meta.spec == spec:
            while meta.status == 'running':
                sleep(0.01)
                meta = _read_meta(path)
            if meta.status == 'done':
                object.__setattr__(artifact, 'path', path)
                return artifact
    else:
        object.__setattr__(artifact, 'path', _new_artifact_path(type(artifact)))
        _build(artifact)
        return artifact


def _artifact_from_path_and_conf(cls: type,
                                 path: Path,
                                 conf: Mapping[str, object]) -> Artifact:
    '''
    Find or build an artifact with the given type, path, and configuration.
    '''
    artifact = cast(Artifact, Configurable.__new__(cls, conf))
    object.__setattr__(artifact, '_cached_keys', set())
    object.__setattr__(artifact, 'path', path)

    if path.exists():
        meta = _read_meta(path)
        if meta.spec != {'type': _identify(type(artifact)), **artifact.conf}:
            raise FileExistsError(f'"{artifact.path}" (incompatible spec)')
        while meta.status == 'running':
            sleep(0.01)
            meta = _read_meta(path)
        if artifact.meta.status == 'stopped':
            raise FileExistsError(f'"{artifact.path}" was stopped mid-build.')
    else:
        _build(artifact)

    return artifact


def _build(artifact: Artifact) -> None:
    '''
    Create parent directories, invoke `artifact.build`, and store metadata.
    '''
    if Path(get_conf().root_dir) in artifact.path.parents:
        write_global_meta()

    # TODO: Fix YAML generation.
    meta_path = artifact.path / '_meta.yaml'
    spec = Namespace(type=_identify(type(artifact)), **artifact.conf)
    write_meta = lambda **kwargs: meta_path.write_text(json.dumps(kwargs))

    artifact.path.mkdir(parents=True)
    write_meta(spec=spec, status='running')

    try:
        if callable(getattr(type(artifact), 'build', None)):
            n_build_args = artifact.build.__code__.co_argcount
            build_args = [artifact.conf] if n_build_args > 1 else []
            artifact.build(*build_args)
        write_meta(spec=spec, status='done')
    except BaseException as e:
        write_meta(spec=spec, status='stopped')
        raise e


def _resolve_path(path: Path) -> Path:
    '''
    Dereference ".", "..", "~", and "@".
    '''
    if str(path).startswith('@/'):
        path = Path(get_conf().root_dir) / str(path)[2:]
    return path.expanduser().resolve()


def _new_artifact_path(type_: type) -> Path:
    '''
    Generate an unused path in the artifact root directory.
    '''
    root = Path(get_conf().root_dir)
    type_name = _identify(type_)
    for i in itertools.count():
        dst = root / f'{type_name}_{i:04x}'
        if not dst.exists():
            return dst
    assert False # for MyPy

#-- I/O -----------------------------------------------------------------------

def _read_h5(path: Path) -> ArrayFile:
    f = h5.File(path, 'r', libver='latest', swmr=True)
    return f['data']


def _write_h5(path: Path, val: object) -> None:
    val = np.asarray(val)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir(): path.rmdir()
    elif path.exists(): path.unlink()
    f = h5.File(path, libver='latest')
    f.create_dataset('data', data=np.asarray(val))


def _extend_h5(path: Path, val: object) -> None:
    val = np.asarray(val)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = h5.File(path, libver='latest')
    if 'data' not in f:
        dset = f.require_dataset(
            name = 'data',
            shape = None,
            maxshape = (None, *val.shape[1:]),
            dtype = val.dtype,
            data = np.empty((0, *val.shape[1:]), val.dtype),
            chunks = (
                int(np.ceil(2**12 / np.prod(val.shape[1:]))),
                *val.shape[1:]
            )
        )
        f.swmr_mode = True
    else:
        dset = f['data']
    dset.resize(dset.len() + len(val), 0)
    dset[-len(val):] = val
    dset.flush()


def _copy_file(dst: Path, src: Path) -> None:
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copy(src, dst)


def _extend_file(dst: Path, src: Path) -> None:
    with open(src, 'r') as f_src:
        with open(dst, 'a+') as f_dst:
            f_dst.write(f_src.read())


def _read_meta(path: Path) -> Namespace:
    # TODO: Implement caching
    try:
        meta = namespacify(yaml.safe_load((path/'_meta.yaml').read_text()))
        assert isinstance(meta, Namespace)
        assert isinstance(meta.spec, Namespace)
        assert isinstance(meta.status, str)
        return meta
    except:
        return Namespace(spec=None, status='done')


def write_global_meta() -> None:
    '''
    Write global config information to `{root_path}/_meta.yaml`.
    '''
    meta = {'spec': None, 'schema': schema()}
    meta_text = yaml.round_trip_dump(meta)
    Path(get_conf().root_dir).mkdir(parents=True, exist_ok=True)
    Path(f'{get_conf().root_dir}/_meta.yaml').write_text(meta_text)

#-- Scope search --------------------------------------------------------------

def _identify(type_: type) -> str:
    return next(sym for sym, t in get_conf().scope.items() if t == type_)
