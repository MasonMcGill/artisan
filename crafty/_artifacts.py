from datetime import datetime
from importlib import import_module
from itertools import count
from pathlib import Path
import shutil
from time import sleep
from typing import (
    Any, Dict, Iterator, Mapping, MutableMapping,
    Optional as Opt, Tuple, Union, cast
)

import h5py as h5
import numpy as np
from ruamel import yaml

from ._global_conf import get_conf
from ._namespaces import Namespace, namespacify

__all__ = ['Component', 'Artifact']

#------------------------------------------------------------------------------
# Type aliases

Rec = Dict[str, object]
Tuple_ = Tuple[object, ...]

#------------------------------------------------------------------------------
# I/O

class _HDF5Entry:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.dset: Opt[h5.Dataset] = None

    def get(self) -> np.ndarray:
        f = h5.File(self.path, 'r', libver='latest', swmr=True)
        return f['data'][()]

    def put(self, val: object) -> None:
        val = np.asarray(val)
        f = h5.File(self.path, libver='latest')
        f.create_dataset('data', data=val)

    def append(self, val: object) -> None:
        val = np.asarray(val)
        if self.dset is None:
            f = h5.File(self.path, libver='latest')
            self.dset = f.require_dataset(
                name='data',
                shape=None,
                maxshape=(None, *val.shape[1:]),
                dtype=val.dtype,
                data=np.empty((0, *val.shape[1:]), val.dtype),
                chunks=(
                    int(np.ceil(2**12 / np.prod(val.shape[1:]))),
                    *val.shape[1:]
                )
            )
            f.swmr_mode = True
        self.dset.resize(self.dset.len() + len(val), 0)
        self.dset[-len(val):] = val
        self.dset.flush()

#------------------------------------------------------------------------------
# Components

class Component:
    class Conf:
        pass

    def __new__(cls, conf: Any = None, **updates: object) -> Any:
        type_name = cast(str, updates.get('type', None) or getattr(conf, 'type', None))
        type_ = cast(type, cls if type_name is None else _resolve(type_name))
        return super().__new__(type_)

    def __init__(self, conf: Any = None, **updates: object):
        self.conf = dict((conf or {}), **updates)

#------------------------------------------------------------------------------
# Artifacts

class Artifact(Component, MutableMapping[str, object]):
    path: Path

    def __new__(cls, *args: object, **kwargs: object) -> Any:
        '''
        Valid signatures:
            __new__(cls, spec)
            __new__(cls, **spec)
            __new__(cls, path)
            __new__(cls, path, spec)
            __new__(cls, path, **spec)
        '''
        #---------------------------
        # Parse/normalize arguments.
        #---------------------------

        path, spec = _parse_artifact_args(args, kwargs)

        # Resolve `path`, dereferencing "~" and "@".
        if path is not None:
            if str(path).startswith('@/'):
                path = Path(get_conf().root_dir) / str(path)[2:]
            path = path.expanduser().resolve()

        #----------------------------
        # Refine `cls`, if necessary.
        #----------------------------

        if spec is not None and 'type' in spec:
            assert isinstance(spec['type'], str)
            subclass = _resolve(spec['type'])
            assert isinstance(subclass, type)
            cls = subclass

        if spec is not None and 'type' not in spec:
            spec['type'] = _identify(cls)

        #-----------------------------------
        # Construct and return the artifact.
        #-----------------------------------

        artifact = object.__new__(cls)
        artifact.__dict__['path'] = path

        if path is None:
            assert spec is not None
            _find_or_build(artifact, spec)
        elif spec is not None:
            _ensure_built(artifact, spec)

        return artifact

    def build(self, spec: Rec) -> None:
        pass

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._cache: Dict[str, Union['Artifact', _HDF5Entry]]
        self.__dict__['_cache'] = {}

    def _get_entry(self, key: str) -> _HDF5Entry:
        if key not in self._cache:
            self._cache[key] = _HDF5Entry(self.path/f'{key}.h5')
        return cast(_HDF5Entry, self._cache[key])

    def _get_artifact(self, key: str) -> 'Artifact':
        if key not in self._cache:
            self._cache[key] = Artifact(self.path/key)
        return cast(Artifact, self._cache[key])

    def _forget(self, key: str) -> None:
        self._cache.pop(key, None)

    def __len__(self) -> int:
        return len([
            p for p in self.path.iterdir()
            if not p.name.startswith('_')
        ])

    def __iter__(self) -> Iterator[str]:
        for p in self.path.iterdir():
            if not p.name.startswith('_'):
                if p.suffix == '.h5': yield p.name[:-3]
                else: yield p.name

    def __getitem__(self, key: str) -> Union['Artifact', np.ndarray, Path]:
        key = Path(key)
        path = self.path/key
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_artifact(key.parts[0])
            return subrec['/'.join(key.parts[1:])]
        elif path.with_suffix('.h5').is_file(): # Return an array
            return self._get_entry(str(key)).get()
        elif path.is_file(): # Return a file path
            return path
        else: # Return a subrecord
            return self._get_artifact(str(key))

    def __setitem__(self, key: str, val: object) -> None:
        key = Path(key)
        path = self.path/key
        assert key.suffix == '', 'Can\'t write to encoded files'
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_artifact(key.parts[0])
            subrec['/'.join(key.parts[1:])] = val
        elif isinstance(val, (dict, Artifact)): # Forward to all subrecords
            for subkey, subval in val.items():
                self[f'{key}/{subkey}'] = subval
        else: # Write an array
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.with_suffix('.h5').exists():
                path.with_suffix('.h5').unlink()
            self._get_entry(str(key)).put(val)

    def __delitem__(self, key: str) -> None:
        key = Path(key)
        path = self.path/key
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_artifact(key.parts[0])
            del subrec['/'.join(key.parts[1:])]
        elif path.is_dir(): # Delete a subrecord
            rec = self._get_artifact(str(key))
            for k in rec: del rec[k]
            shutil.rmtree(path, True)
        elif path.with_suffix('.h5').is_file(): # Delete an array
            path.with_suffix('.h5').unlink()
        elif path.is_file(): # Delete a non-array file
            path.unlink()
        else:
            raise FileNotFoundError()
        self._forget(str(key))
        if self.path.stat().st_nlink == 0:
            self.path.rmdir()

    __getattr__ = __getitem__
    __setattr__ = __setitem__

    def append(self, key: str, val: object) -> None:
        key = Path(key)
        path = self.path/key
        assert key.suffix == '', 'Can\'t write to encoded files'
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_artifact(key.parts[0])
            subrec.append('/'.join(key.parts[1:]), val)
        elif isinstance(val, (dict, Artifact)): # Forward to all subrecords
            for subkey, subval in val.items():
                self.append(f'{key}/{subkey}', subval)
        else: # Append to an array
            path.parent.mkdir(parents=True, exist_ok=True)
            self._get_entry(str(key)).append(val)

    @property
    def meta(self) -> Namespace:
        # TODO: Implement caching
        return cast(Namespace, namespacify(_read_meta(self.path)))

#------------------------------------------------------------------------------
# Support functions

def _parse_artifact_args(args: Tuple_, kwargs: Rec) -> Tuple[Opt[Path], Opt[Rec]]:
    # (spec)
    if (len(args) == 1
        and isinstance(args[0], Mapping)
        and len(kwargs) == 0):
        return None, dict(args[0])

    # (**spec)
    elif (len(args) == 0
          and len(kwargs) > 0):
        return None, kwargs

    # (path)
    elif (len(args) == 1
          and isinstance(args[0], (str, Path))
          and len(kwargs) == 0):
        return Path(args[0]), None

    # (path, spec)
    elif (len(args) == 2
          and isinstance(args[0], (str, Path))
          and isinstance(args[1], Mapping)
          and len(kwargs) == 0):
        return Path(args[0]), dict(args[1])

    # (path, **spec)
    elif (len(args) == 1
          and isinstance(args[0], (str, Path))
          and len(kwargs) > 0):
        return Path(args[0]), kwargs

    # <invalid signature>
    else:
        raise TypeError(
            'Invalid argument types for the `Target` constructor.\n'
            'Valid signatures:\n'
            '\n'
            '    - Target(spec: Mapping[str, object])\n'
            '    - Target(**spec: object)\n'
            '    - Target(path: Path|str)\n'
            '    - Target(path: Path|str, spec: Mapping[str, object])\n'
            '    - Target(path: Path|str, **spec: object)\n'
        )


def _find_or_build(artifact: Artifact, spec: Rec) -> None:
    for path in Path(get_conf().root_dir).iterdir():
        if _was_built(path, spec):
            artifact.path = path
            return
    artifact.path = _new_artifact_path(spec)
    _build(artifact, spec)


def _ensure_built(artifact: Artifact, spec: Rec) -> None:
    if artifact.path.exists():
        if not _was_built(artifact.path, spec):
            raise FileExistsError(
                f'The contents of "{artifact.path}" do not '
                f'match the provided spec.'
            )
    else:
        _build(artifact, spec)


def _was_built(path: Path, spec: Rec) -> bool:
    if _read_meta(path)['spec'] == spec:
        while _read_meta(path)['status'] == 'running':
            sleep(0.001)
        return _read_meta(path)['status'] == 'done'
    else:
        return False


def _build(artifact: Artifact, spec: Rec) -> None:
    artifact.path.mkdir(parents=True)
    _write_meta(artifact.path, dict(spec=spec, status='running'))

    try:
        n_build_args = artifact.build.__code__.co_argcount
        artifact.build(*([Namespace(spec)] if n_build_args > 1 else []))
        _write_meta(artifact.path, dict(spec=spec, status='done'))
    except BaseException as e:
        _write_meta(artifact.path, dict(spec=spec, status='stopped'))
        raise e


def _new_artifact_path(spec: Rec) -> Path:
    root = get_conf().root_dir
    date = datetime.now().strftime(r'%Y-%m-%d')
    for i in count():
        try:
            dst = Path(f'{root}/{spec["type"]}_{date}-{i:04x}')
            dst.mkdir(parents=True)
            return dst
        except FileExistsError:
            pass
    assert False # for MyPy


def _read_meta(path: Path) -> Rec:
    try:
        return cast(Rec, yaml.safe_load((path/'_meta.yaml').read_text()))
    except:
        return dict(spec=None, status='done')


def _write_meta(path: Path, meta: Rec) -> None:
    (path/'_meta.yaml').write_text(yaml.round_trip_dump(meta))


def _resolve(sym: str) -> object:
    'Search the current scope for an object.'
    if sym in get_conf().scope:
        return get_conf().scope[sym]
    try:
        mod_name, type_name = sym.split('$')
        mod = import_module(mod_name)
        return cast(object, getattr(mod, type_name))
    except:
        raise KeyError(f'"{sym}" is not present in the current scope')


def _identify(obj: object) -> str:
    'Search the current scope for an object\'s name.'
    for sym, val in get_conf().scope.items():
        if val is obj: return sym
    return f'{obj.__module__}${cast(Any, obj).__qualname__}'