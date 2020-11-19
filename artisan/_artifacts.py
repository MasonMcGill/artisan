'''
Functionality for defining persistent, parameterizable computed asset types.

Exported definitions:
    Artifact (abstract `Target` subclass): A typed view into a directory.
        `Artifact` is intended to be subclassed by application authors.
    DynamicArtifact (`Artifact` subclass): An artifact with dynamic fields.
    ProxyArtifactField (class): An artifact field that does not yet exist.
    build (function): Build a target from a specification.
    recover (function): Recover an existing artifact.

Internal definitions:
    active_builder (context variable): The default directory for artifact
        creation and search.
    active_root (context variable): The function called to write files into
       artifact directories.
'''

from __future__ import annotations

import json, re, shutil
from contextvars import ContextVar
from datetime import datetime
from functools import reduce
from itertools import count
from os import PathLike
from os.path import lexists
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from typing import (
    TYPE_CHECKING, Any, Callable, ClassVar, Iterable,
    Iterator, List, Literal, MutableMapping, Optional,
    Type, TypeVar, Union, cast, final)

import numpy as np

from ._cbor_io import read_cbor_file, write_object_as_cbor
from ._fs_index import DirIndex
from ._misc_io import (
    read_json_file, read_numpy_file, read_opaque_file,
    read_text_file, write_path)
from ._namespaces import Namespace, dictify, namespacify
from ._targets import Target, TargetType, active_scope

__all__ = [
    'Artifact', 'DynamicArtifact', 'ProxyArtifactField',
    'active_builder', 'active_root', 'build', 'recover']

if not TYPE_CHECKING:
    # Redefine `MutableMapping` to make it
    # compatible with artifact types.
    import collections.abc
    class MutableMapping(collections.abc.MutableMapping):
        def __class_getitem__(cls, key: type) -> type:
            return cls



#-- Type variables and aliases -------------------------------------------------

T = TypeVar('T')
SomeTarget = TypeVar('SomeTarget', bound=Target)
SomeArtifact = TypeVar('SomeArtifact', bound='Artifact')

Reader = Callable[[Path], Any]
Writer = Callable[[Path, Any], str]
AccessMode = Literal['read-sync', 'read-async', 'write']



#-- Context-local state --------------------------------------------------------

def default_builder(artifact: Artifact, spec: object) -> None:
    '''
    Call `artifact.__init__` in "write" mode, logging "Start", "Success", and/or
    "Failure" events to `{artifact._path_}/_meta_.json`.
    '''
    prev_mode = artifact._mode_
    artifact._mode_ = 'write'
    log(artifact, 'Start')
    try:
        artifact.__init__(spec) # type: ignore
        log(artifact, 'Success')
    except Exception as e:
        log(artifact, 'Failure', message=str(e))
        raise e
    finally:
        artifact._mode_ = prev_mode


active_root = ContextVar('artisan:root', default=Path('.')); \
    '''
    The default directory for artifact creation, and the directory that will be
    searched for matches when an artifact is instantiated from a specification.
    '''


active_builder = ContextVar('artisan:builder', default=default_builder); \
    '''
    The function called to write files into artifact directories. It accepts two
    arguments, the artifact to construct and its specification.
    '''



#-- `ArtifactType` -------------------------------------------------------------

class ArtifactType(TargetType):
    '''
    `Artifact`'s metaclass.
    '''
    def __call__(cls: Type[T], *args: object, **kwargs: object) -> T:
        '''
        Return a new instance, without calling `__init__`.
        '''
        cls, args = cls._refine_call_args(args) # type: ignore
        return cls.__new__(cls, *args, **kwargs) # type: ignore

    def __matmul__(cls: Type[T], path: Union[PathLike, str]) -> T:
        '''
        Return an artifact corresponding to the directory at the specified path.
        '''
        return recover(cls, path) # type: ignore



#-- `Artifact` -----------------------------------------------------------------

class Artifact(Target, metaclass=ArtifactType):
    '''
    A typed view into a directory.

    **Instantiation**

    When an artifact is instantiated, Artisan will search for a directory with a
    matching `_meta_.json` file in the active context's root directory. The
    search is recursive, but when a directory with a `_meta_.json` file is
    found, its subdirectories will not be searched. If a matching directory does
    not exist, a new directory will be created, and the active context's
    artifact builder will be called to build the artifact there. If `spec` has a
    `_path_` field, the artifact will be located at that path. The "@" operator,
    as in `ArtifactType @ path`, can be used to load an existing artifact
    without requiring it to match a specification. In the default context, the
    root directory is the current working directory, and the artifact builder
    calls `__init__` and logs metadata to `_meta_.json`.

    **Reading and writing files**

    Reading from and writing to an artifact's attributes corresponds to reading
    from and writing to files in the corresponding directory. Support for new
    file types can be added by overriding an artifact type's list of readers
    (`_readers_`) and/or its list of writers (`_writers_`). Readers should be
    functions that accept a path and return an object representing the data
    stored at that path. Writers should accept an extensionless path and a data
    object, write the data to a version of the path with an appropriate
    extension, and return that extension. To support concurrent reading and
    writing, files generated by writers are not moved into the artifact's
    directory until after the writer returns.

    When reading from or writing to files, the first reader/writer not to raise
    an exception when called will be used. For performance, Artisan may skip
    writers whose data argument type does not match the object being stored.
    Similarly, Artisan may skip readers whose path argument type is annotated
    with an incompatible extension requirement, *e.g.* `Annotated[Path, '.txt']`
    or `Annotated[Path, '.jpg', '.jpeg']`. The `Annotated` type constructor can
    be imported from the `typing` module in Python 3.9+ and the
    `typing_extensions` module in earlier versions.

    **Attribute-access modes**

    Artifacts can be instantiated in "read-sync", "read-async", or "write" mode.
    In "read-sync" mode, attribute accesses will only return after the artifact
    has finished building. In "read-async" mode, attribute accesses will return
    as soon as a corresponding file or directory exists. In "write" mode,
    attribute accesses will return immediately, but a `ProxyArtifactField` will
    be returned if no corresponding file or directory is present. Artifacts are
    instantiated in "read-sync" mode by default, but if `spec` has a `_mode_`
    attribute, that mode will be used. The default builder always executes
    artifacts' `__init__` methods in "write" mode (an other builders should as
    well), so it is generally only necessary to specify `_mode_` when
    "read-async" behavior is desired.

    Arguments:
        spec (Artifact.Spec): The artifact's specification.

    :var _readers_:
        The deserialization functions artifacts of this type will
        try to use when their attributes are being accessed.
    :var _writers_:
        The serialization functions artifacts of this type will
        try to use when their attributes are being assigned to.
    :var _path_:
        The artifact's path on the filesystem.
    :var _mode_:
        The artifact's attribute-access mode.

    :vartype _writers_: ClassVar[List[Callable]]
    :vartype _readers_: ClassVar[List[Callable]]
    :vartype _path_: Path
    :vartype _mode_: Literal['read-sync', 'read-async', 'write']
    '''
    _readers_: ClassVar[List[Reader]] = [
        read_cbor_file,
        read_text_file,
        read_json_file,
        read_numpy_file,
        read_opaque_file]

    _writers_: ClassVar[List[Writer]] = [
        write_path,
        write_object_as_cbor]

    _path_: Path
    _mode_: AccessMode
    _index: DirIndex

    def __new__(cls: Type[SomeArtifact], spec: object) -> SomeArtifact:
        '''
        Find or build an artifact with the given specification.
        '''
        # Determine the artifact's path.
        match_path = find_match(cls, spec)
        path = match_path or make_stub(cls, spec)

        # Create an instance.
        instance = Target.__new__(cls, spec)
        instance.__dict__['_path_'] = path
        instance.__dict__['_mode_'] = getattr(spec, '_mode_', 'read-sync')
        instance.__dict__['_index'] = DirIndex(path)

        # Invoke the builder if the artifact is new.
        if match_path is None:
            builder = active_builder.get()
            builder(instance, spec)

        # Return the instance, with building having been
        # initiated, but not necessarily having finished.
        return instance

    def __dir__(self) -> List[str]:
        '''
        Return the names of this artifact's attributes.
        '''
        return (sorted(self._index.get_entry_names())
                + cast(list, super().__dir__()))

    def __getattr__(self, key: str) -> Any:
        '''
        Return the data stored at `{self._path_}/{key}{inferred_extension}`.
        '''
        if self._mode_ == 'read-sync':
            while self._is_building():
                sleep(0.001)
            path = self._index.get_entry_path(key)
            if path is None:
                raise AttributeError(f"Attribute not found: '{key}'")

        elif self._mode_ == 'read-async':
            path = self._index.get_entry_path(key)
            while path is None and self._is_building():
                sleep(0.001)
                path = self._index.get_entry_path(key)
            if path is None:
                raise AttributeError(f"Attribute not found: '{key}'")

        else:
            path = self._index.get_entry_path(key)
            if path is None:
                return ProxyArtifactField(self, key)

        if path.is_dir():
            return recover(Artifact, path, self._mode_)

        for reader in self._readers_:
            try: return reader(path)
            except ValueError: pass

        raise OSError(f'Unsupported content type at "{path}"')

    def __setattr__(self, key: str, value: object) -> None:
        '''
        Write data to `{self._path_}/{key}{inferred_extension}`.

        The extension is determined based on the type of data stored. For
        performance, other entries with matching keys are not deleted. Use
        `__delattr__` to delete those entries.
        '''
        if self._mode_ in ('read-sync', 'read-async') or key in self.__dict__:
            super().__setattr__(key, value)
            return

        if isinstance(value, Artifact):
            (self._path_ / key).symlink_to(
                value._path_, target_is_directory=True)
            return

        with TemporaryDirectory() as temp_root:
            temp_path = Path(temp_root, 'file')
            for writer in self._writers_:
                try:
                    suffix = writer(temp_path, value)
                    dst = (self._path_ / key).with_suffix(suffix)
                    temp_path.replace(dst)
                    self._index.set_entry_path(key, dst)
                    return
                except TypeError:
                    pass

        raise OSError(f'Unsupported content type: {type(value)}')

    def __delattr__(self, key: str) -> None:
        '''
        Delete all entries in `self._path_` with the given stem.
        '''
        for path in list(self._path_.iterdir()):
            if path.stem == key:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

    def __fspath__(self) -> str:
        '''
        Return this artifact's path, as a string.
        '''
        return str(self._path_)

    def __truediv__(self, entry_name: str) -> Path:
        '''
        Return `self._path_ / entry_name`.
        '''
        return self._path_ / entry_name

    def _is_building(self) -> bool:
        '''
        Return whether this artifact is currently being built.
        '''
        meta = self._index.get_meta()
        events = meta['events'] if isinstance(meta, dict) else []
        started = any(e['type'] == 'Start' for e in events)
        finished = any(e['type'] in ('Success', 'Failure') for e in events)
        return started and not finished



#-- `DynamicArtifact` ----------------------------------------------------------

@final
class DynamicArtifact(Artifact, MutableMapping[str, T]):
    '''
    An artifact with dynamically named fields.

    Item access, assignment, deletion, and iteration can be used in place of
    attribute access, assignment, deletion, and iteration
    '''
    def __len__(self) -> int:
        return len(list(self._index.get_entry_names()))

    def __iter__(self) -> Iterator[str]:
        return (name for name in sorted(self._index.get_entry_names())
                if name[0] not in '._')

    def __contains__(self, key: object) -> bool:
        return ((self._index.get_entry_path(key) is not None)
                if isinstance(key, str)
                else False)

    def __getitem__(self, key: str) -> T:
        return self.__getattr__(key)

    def __setitem__(self, key: str, val: object) -> None:
        self.__setattr__(key, val)

    def __delitem__(self, key: str) -> None:
        self.__delattr__(key)



#-- `ProxyArtifactField` -------------------------------------------------------

@final
class ProxyArtifactField:
    '''
    An artifact field that does not yet exist.

    Corresponding files and/or directories will be created when it is written
    to.
    '''
    _root: Artifact
    _keys: List[str]

    def __init__(self, root: Artifact, *keys: str) -> None:
        self.__dict__['_root'] = root
        self.__dict__['_keys'] = keys

    def __getattr__(self, key: str) -> ProxyArtifactField:
        if lexists(self._root._path_.joinpath(*self._keys)):
            return getattr(reduce(getattr, self._keys, self._root), key)
        else:
            return ProxyArtifactField(self._root, *self._keys, key)

    def __setattr__(self, key: str, value: object) -> None:
        Path(self._root._path_, *self._keys).mkdir(parents=True, exist_ok=True)
        setattr(reduce(getattr, self._keys, self._root), key, value)

    def __delattr__(self, key: str) -> None:
        delattr(reduce(getattr, self._keys, self._root), key)

    def __getitem__(self, key: str) -> Any:
        return self.__getattr__(key)

    def __setitem__(self, key: str, val: object) -> None:
        self.__setattr__(key, val)

    def __delitem__(self, key: str) -> None:
        self.__delattr__(key)

    def append(self, item: object) -> None:
        if isinstance(item, np.ndarray):
            self.extend(item[None])
        else:
            self.extend([item])

    def extend(self, items: Iterable[object]) -> None:
        *wrapper_keys, field_key = self._keys
        Path(self._root._path_, *wrapper_keys).mkdir(parents=True, exist_ok=True)
        wrapper = reduce(getattr, wrapper_keys, self._root)
        field = getattr(wrapper, field_key)
        if isinstance(field, ProxyArtifactField):
            setattr(wrapper, field_key, items)
        else:
            field.extend(items)



#-- Artifact/target-creation functions -----------------------------------------

def build(cls: Type[SomeTarget],
          spec: object,
          *args: object,
          **kwargs: object) -> SomeTarget:
    '''
    Build a target from a specification.

    To support using JSON-encodable objects as specifications, mappings in
    `spec` are converted to namespaces and artifact-root-relative path strings
    (strings starting with "@/") are converted to artifacts if they point to an
    existing directory, and `Path` objects otherwise.

    `args` and `kwargs` are forwarded to the target's constructor.
    '''
    return cls(namespacify(spec, decode_path), *args, **kwargs) # type: ignore


def recover(cls: Type[SomeArtifact],
            path: Union[PathLike, str],
            mode: str = 'read-sync') -> SomeArtifact:
    '''
    Recover an existing artifact.

    `mode` must be "read-sync", "read-async", or "write".
    '''
    # Expand "~" and "@" in the path.
    path = resolve(path)

    # Infer the class based on `_meta_.json`.
    refined_cls: Type[SomeArtifact] = DynamicArtifact # type: ignore
    if cls is not DynamicArtifact:
        try:
            meta = DirIndex(path).get_meta()
            cls_spec = meta['spec']['type'] # type: ignore
            refined_cls = active_scope.get()[cls_spec]
        except (TypeError, KeyError):
            pass

    # Check that the inferred class is valid.
    if not issubclass(refined_cls, cls):
        raise ValueError(f'`{refined_cls}` is not a subclass of `{cls}`.')

    # Construct and return an artifact.
    artifact = Target.__new__(refined_cls)
    artifact.__dict__['_path_'] = path
    artifact.__dict__['_mode_'] = mode
    artifact.__dict__['_index'] = DirIndex(path)
    return artifact



#-- Support functions ----------------------------------------------------------

def find_match(cls: Type[Artifact], spec: object) -> Optional[Path]:
    '''
    Return the path to an artifact matching the given specification, or `None`
    if no such artifact exists.
    '''
    root = active_root.get()
    spec_path = getattr(spec, '_path_', None)

    spec_dict = dictify(
        {'type': cls, **vars(spec)},
        path_encoder = encode_path,
        type_encoder = get_type_name)

    candidates = (
        [DirIndex(resolve(spec_path))]
        if spec_path is not None
        else DirIndex(root).get_artifacts())

    for dir_index in candidates:
        meta = dir_index.get_meta()
        if (isinstance(meta, dict)
            and meta['spec'] == spec_dict
            and all(e['type'] != 'Failure' for e in meta['events'])):
            return dir_index.path

    return None


def make_stub(cls: Type[Artifact], spec: object) -> Path:
    '''
    Create a new directory for an artifact with the given type and
    specification, and initialize its `_meta_.json` file.
    '''
    root = active_root.get()
    spec_path = getattr(spec, '_path_', None)
    spec_dict = dictify({'type': cls, **vars(spec)}, encode_path, get_type_name)
    generated_paths = (root / f'{spec_dict["type"]}_{i:04x}' for i in count())
    candidates = [resolve(spec_path)] if spec_path else generated_paths

    for path in candidates:
        try:
            path.mkdir(parents=True)
            meta = {'spec': spec_dict, 'events': []}
            write_json_atomically(path / '_meta_.json', meta)
            return path
        except FileExistsError:
            continue
    else:
        raise FileExistsError(f'Incompatible files exist at `{path}`.')


def resolve(path: Union[PathLike, str]) -> Path:
    '''
    Return an absolute path, dereferencing "~" (the home directory) and "@" (the
    root artifact directory).
    '''
    root = active_root.get()
    path = Path(re.sub('^@', str(root), str(Path(path))))
    path = path.expanduser().resolve()
    return path


def get_type_name(type_: type) -> str:
    '''
    Return the given type's name in the active scope.

    If the given type has multiple name, the lexicographically first name is
    used. If it has no names, a `ValueError` is raised.
    '''
    try:
        scope = active_scope.get()
        return min(k for k, v in scope.items() if v is type_)
    except ValueError:
        raise ValueError(f'{type_} is not in the current Artisan scope.')


def log(artifact: Artifact, type: str, **kwargs: object) -> None:
    '''
    Log a build event (*e.g.* "Start", "Success", or "Failure"). An entry in the
    form `{"type": type, "timestamp": timestamp, **kwargs}` will be added to the
    metadata file's event log.
    '''
    timestamp = datetime.now().isoformat()
    meta = json.loads((artifact / '_meta_.json').read_text())
    meta['events'].append(dict(type=type, timestamp=timestamp, **kwargs))
    write_json_atomically(artifact / '_meta_.json', meta)


def write_json_atomically(dst: Path, obj: dict) -> None:
    '''
    Serialize and object to a JSON file, atomically.
    '''
    with TemporaryDirectory() as temp_root:
        with open(f'{temp_root}/f', 'w') as f:
            json.dump(obj, f, indent=2)
        Path(f'{temp_root}/f').replace(dst)


def encode_path(path: PathLike) -> str:
    '''
    Convert a path-like object to a artifact-root-directory-relative path
    string (a string starting with "@/").
    '''
    root = active_root.get().resolve()
    dots: List[str] = []
    path = Path(path).resolve()

    while root not in (*path.parents, path):
        root = root.parent
        dots.append('..')

    return '@/' + '/'.join(Path(*dots, path.relative_to(root)).parts)


def decode_path(path_str: str) -> PathLike:
    '''
    Convert a root-directory-relative path string (a string starting with "@/")
    to an artifact if it points to an existing directory, or a `Path` object,
    otherwise.
    '''
    root = active_root.get().resolve()
    path = (root / path_str[2:]).resolve()
    return Artifact @ path if path.is_dir() else path # type: ignore
