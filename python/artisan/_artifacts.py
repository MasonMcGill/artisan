from datetime import datetime
import itertools
from pathlib import Path
import shutil
from time import sleep
from typing import (
    Any, Iterator, Dict, Mapping, MutableMapping,
    Optional as Opt, Tuple, Union, cast
)

import h5py as h5
import numpy as np
from ruamel import yaml

from ._global_conf import conf_stack
from ._configurable import Configurable

__all__ = ['Artifact', 'ArrayFile', 'EncodedFile']

#-- Type aliases --------------------------------------------------------------

Rec = Mapping[str, object]
MutRec = MutableMapping[str, object]
Tuple_ = Tuple[object, ...]

ArrayFile = h5.Dataset; 'An alias for `h5py.Dataset`'
EncodedFile = Path; 'An alias for `pathlib.Path`'

#-- Artifacts -----------------------------------------------------------------

class Artifact(Configurable):
    '''
    An array- and metadata-friendly view into a directory

    Arguments:
        path (Path|str): The path at which the artifact is, or should be,
            stored
        spec (Mapping[str, object]): The subtype-specific configuration,
            optionally including a "type" field indicating what type of
            artifact to construct

    Constructors:
        Artifact(spec: Mapping[str, object])
        Artifact(**spec_elem: object)
        Artifact(path: Path|str)
        Artifact(path: Path|str, spec: Mapping[str, object])
        Artifact(path: Path|str, **spec_elem: object)

    Type lookup is performed in the current scope, which can be modified via
    the global configuration API.

    Reading/writing/extending/deleting `ArrayFile`, `EncodedFile`, and
    `Artifact` fields is supported.

    See the full documentation for more details.
    '''
    path: Path

    def __new__(cls, *args: object, **kwargs: object) -> Any:
        #---------------------------
        # Parse/normalize arguments.
        #---------------------------

        path, spec = _parse_artifact_args(args, kwargs)

        # Resolve `path`, dereferencing "~" and "@".
        if path is not None:
            if str(path).startswith('@/'):
                path = Path(conf_stack.get().root_dir) / str(path)[2:]
            path = path.expanduser().resolve()

        #-----------------------------------
        # Construct and return the artifact.
        #-----------------------------------

        artifact = cast(Artifact, Configurable.__new__(cls, spec or {}))
        object.__setattr__(artifact, 'path', path)

        if path is None:
            assert spec is not None
            _find_or_build(artifact, spec)
        elif spec is not None:
            _ensure_built(artifact, spec)

        return artifact

    def build(self, conf: Any) -> None:
        '''
        Write arrays, encoded files, and subartifacts

        `build` is called during instantiation if a matching existing artifact
        is not found. Override it to construct nontrivial cacheable artifacts.
        '''
        pass

    @property
    def meta(self) -> Rec:
        'The metadata stored in `{self.path}/_meta.yaml`'
        # TODO: Implement caching
        return cast(Rec, _namespacify(_read_meta(self)))

    #-- MutableMapping methods ----------------------------

    def __len__(self) -> int:
        return len([*self.path.glob('[!_]*')])

    def __iter__(self) -> Iterator[str]:
        for p in self.path.glob('[!_]*'):
            yield p.name[:-3] if p.suffix == '.h5' else p.name

    def __getitem__(self, key: str) -> Union['Artifact', np.ndarray, Path]:
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
        path = self.path / key.replace('__', '.')

        # Write an array.
        if isinstance(val, np.ndarray):
            assert path.suffix == ''
            _write_h5(path.with_suffix('.h5'), val)

        # Copy an existing file.
        elif isinstance(val, Path):
            assert path.suffix != ''
            _copy_file(path, val)

        # Write a subartifact.
        elif isinstance(val, Mapping):
            assert path.suffix == ''
            MutRec.update(
                cast(MutRec, Artifact(path)),
                cast(Rec, val)
            )

        else:
            raise TypeError()

    def __delitem__(self, key: str) -> None:
        path = self.path / key.replace('__', '.')
        shutil.rmtree(path, ignore_errors=True)

    def extend(self, key: str, val: object) -> None:
        path = self.path / key

        # Append an array.
        if isinstance(val, np.ndarray):
            assert path.suffix == ''
            _exend_h5(path, val)

        # Copy an existing file.
        elif isinstance(val, Path):
            assert path.suffix != ''
            _extend_file(path, val)

        # Write a subartifact.
        elif isinstance(val, Mapping):
            assert path.suffix == ''
            for k, v in val.items():
                Artifact(path).extend(k, v)

        else:
            raise TypeError()

    #-- Attribute-style element access --------------------

    __getattr__ = __getitem__
    __setattr__ = __setitem__
    __delattr__ = __delitem__

    # [A hack to get REPL autocompletion to work]
    def __getattribute__(self, key: str) -> Any:
        return (
            {k: None for k in self} if key == '__dict__'
            else object.__getattribute__(self, key)
        )

#-- Artifact construction -----------------------------------------------------

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
            'Invalid argument types for the `Artifact` constructor.\n'
            'Valid signatures:\n'
            '\n'
            '    - Artifact(spec: Mapping[str, object])\n'
            '    - Artifact(**spec_elem: object)\n'
            '    - Artifact(path: Path|str)\n'
            '    - Artifact(path: Path|str, spec: Mapping[str, object])\n'
            '    - Artifact(path: Path|str, **spec_elem: object)\n'
        )


def _find_or_build(artifact: Artifact, spec: Rec) -> None:
    for path in Path(conf_stack.get().root_dir).iterdir():
        object.__setattr__(artifact, 'path', path)
        try: return _ensure_built(artifact, spec)
        except FileExistsError: pass
    object.__setattr__(artifact, 'path', _new_artifact_path(spec))
    _build(artifact, spec)


def _ensure_built(artifact: Artifact, spec: Rec) -> None:
    # [Already started]
    if artifact.path.exists():
        if _read_meta(artifact)['spec'] != spec:
            raise FileExistsError(f'"{artifact.path}" (incompatible spec)')
        while _read_meta(artifact)['status'] == 'running':
            sleep(0.001)
        if _read_meta(artifact)['status'] == 'stopped':
            raise FileExistsError(f'"{artifact.path}" was stopped mid-build.')

    # [Starting from scratch]
    else: _build(artifact, spec)


def _build(artifact: Artifact, spec: Rec) -> None:
    artifact.path.mkdir(parents=True)
    _write_meta(artifact, dict(spec=spec, status='running'))

    try:
        n_build_args = artifact.build.__code__.co_argcount
        artifact.build(*([_Namespace(spec)] if n_build_args > 1 else []))
        _write_meta(artifact, dict(spec=spec, status='done'))
    except BaseException as e:
        _write_meta(artifact, dict(spec=spec, status='stopped'))
        raise e


def _new_artifact_path(spec: Rec) -> Path:
    root = Path(conf_stack.get().root_dir)
    date = datetime.now().strftime(r'%Y-%m-%d')
    for i in itertools.count():
        dst = root / f'{spec["type"]}_{date}_{i:04x}'
        if not dst.exists():
            return dst
    assert False # for MyPy

#-- I/O -----------------------------------------------------------------------

def _read_h5(path: Path) -> np.ndarray:
    # TODO: Make this lazy.
    f = h5.File(path, 'r', libver='latest', swmr=True)
    return f['data'][:]


def _write_h5(path: Path, val: np.ndarray) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = h5.File(path, libver='latest')
    f.create_dataset('data', data=np.asarray(val))


def _exend_h5(path: Path, val: np.ndarray) -> None:
    val = np.asarray(val)
    f = h5.File(path, libver='latest')
    dset = f.require_dataset(
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


def _read_meta(a: Artifact) -> Rec:
    try: return cast(Rec, yaml.safe_load((a.path / '_meta.yaml').read_text()))
    except: return dict(spec=None, status='done')


def _write_meta(a: Artifact, meta: Rec) -> None:
    (a.path / '_meta.yaml').write_text(yaml.round_trip_dump(meta))

#-- Namespaces ----------------------------------------------------------------

class _Namespace(Dict[str, object]):
    'A `dict` that supports accessing items as attributes'

    def __getattr__(self, key: str) -> Any:
        return dict.__getitem__(self, key)

    def __setattr__(self, key: str, val: object) -> None:
        dict.__setitem__(self, key, val)

    def __getattribute__(self, key: str) -> Any:
        if key == '__dict__': return self
        else: return object.__getattribute__(self, key)


def _namespacify(obj: object) -> object:
    if isinstance(obj, dict):
        return _Namespace({k: _namespacify(obj[k]) for k in obj})
    elif isinstance(obj, list):
        return [_namespacify(v) for v in obj]
    else:
        return obj
