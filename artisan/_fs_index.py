'''
Filesystem indexing.

Internal definitions:
    DirIndex (class): An index of entries in a directory.
    TreeIndex (class): An index of entries in a directory tree.
'''

from __future__ import annotations

import json
from os.path import lexists
from pathlib import Path
from time import time
from typing import Any, Dict, Iterator, MutableMapping, Optional, Set, Union
from weakref import WeakSet, WeakValueDictionary

__all__ = ['DirIndex', 'TreeIndex']



#-- Module-level constants/data structures -------------------------------------

TIMESTAMP_PADDING = 1.0; \
    '''
    The minimum age of a file or directory (as measured by its `st_mtime`), in
    seconds, for a cached version to be used instead of reading it.
    '''


dir_indices: MutableMapping[Path, DirIndex] = WeakValueDictionary(); \
    '''
    All instantiated `DirIndex` objects, by path.
    '''


tree_indices: MutableMapping[Path, TreeIndex] = WeakValueDictionary(); \
    '''
    All instantiated `TreeIndex` objects, by path.
    '''



#-- `DirIndex` and `TreeIndex` -------------------------------------------------

class DirIndex:
    '''
    An index of entries in a directory.

    The `DirIndex` constructor is written such that no more than one instance
    will ever exist for a given directory at a given time.
    '''
    path: Path; "The path to the directory."
    parent: Optional[DirIndex]; "The parent directory's `DirIndex`."
    children: Set[DirIndex]; "`DirIndices` for subdirectories (non-exhaustive)."

    _ino: int; "The directory's inode number."
    _mtime: float; "The directory's modification timestamp."
    _entry_paths: Dict[str, Path]; "Entry paths, by stem."

    _meta_ino: int; "The `_meta_.json` file's inode number."
    _meta_mtime: float; "The `_meta_.json` file's modification timestamp."
    _meta: Union[None, Exception, Dict[str, Any]]; "Artifact metadata."

    def __new__(cls, path: Path) -> DirIndex:
        path = path.expanduser().resolve()
        try:
            return dir_indices[path]
        except KeyError:
            instance: DirIndex = object.__new__(cls)
            instance.path = path
            instance.parent = None
            instance.children = WeakSet() # type: ignore

            if path != path.parent:
                instance.parent = DirIndex(path.parent)
                instance.parent.children.add(instance)

            instance._ino = -1
            instance._mtime = -1.0
            instance._entry_paths = {}

            instance._meta_ino = -1
            instance._meta_mtime = -1.0
            instance._meta = None

            dir_indices[path] = instance
            for parent_path in path.parents:
                tree_index = tree_indices.get(parent_path, None)
                if tree_index is not None:
                    tree_index._descendants.add(instance)

            return instance

    def get_meta(self) -> Union[None, Exception, Dict[str, Any]]:
        '''
        Return a metatata dictionary if a valid metadata exists at
        `{self.path}/_meta_.json`, `None`, if the file doesn't exist, and an
        exception if it is invalid.
        '''
        self._refresh_meta()
        return self._meta

    def get_entry_names(self) -> Iterator[str]:
        '''
        Yield all of the entry names such that a file or directory matching
        `{self.path}/{entry_name}*` exists.
        '''
        self._refresh_entry_paths()
        return iter(self._entry_paths)

    def get_entry_path(self, entry_name: str) -> Optional[Path]:
        '''
        Return the path to an entry matching `{self.path}/{entry_name}*`, if
        one exists, or `None`, otherwise.
        '''
        path = self._entry_paths.get(entry_name, None)
        if path is None or not lexists(path):
            self._refresh_entry_paths()
            path = self._entry_paths.get(entry_name, None)
        return path

    def set_entry_path(self, entry_name: str, entry_path: Path) -> None:
        '''
        Associate the file's stem with its full path (including the extension).
        '''
        self._entry_paths[entry_name] = entry_path

    def get_artifacts(self) -> Iterator[DirIndex]:
        '''
        Yield `DirIndex` objects corresponding to the top-level artifacts
        contained in this directory.
        '''
        meta = self.get_meta()
        if isinstance(meta, dict):
            yield self
        elif meta is None:
            self._refresh_entry_paths()
            for path in self._entry_paths.values():
                if path.is_dir():
                    yield from DirIndex(path).get_artifacts()

    def _refresh_meta(self) -> None:
        '''
        Ensure that `self._meta` is up-to-date.
        '''
        try:
            stat = (self.path / '_meta_.json').stat()
        except FileNotFoundError:
            self._meta_ino = -1
            self._meta_mtime = time() - TIMESTAMP_PADDING
            self._meta = None
            return

        if stat.st_ino != self._meta_ino or stat.st_mtime > self._meta_mtime:
            self._meta_ino = stat.st_ino
            self._meta_mtime = time() - TIMESTAMP_PADDING
            try:
                meta_json = (self.path / '_meta_.json').read_bytes()
                self._meta = validate_meta(json.loads(meta_json))
            except Exception as e:
                self._meta = e

    def _refresh_entry_paths(self) -> None:
        '''
        Ensure that `self._entry_paths` is up-to-date.
        '''
        stat = self.path.stat()
        if stat.st_ino != self._ino or stat.st_mtime > self._mtime:
            self._ino = stat.st_ino
            self._mtime = time() - TIMESTAMP_PADDING
            self._entry_paths = {p.stem: p for p in self.path.iterdir()}
            for child in tuple(self.children):
                if not child.path.is_dir():
                    child._prune()

    def _prune(self) -> None:
        '''
        Remove this `DirIndex` and its children from their parents' lists of
        children and all `TreeIndex` objects' lists of descendants.
        '''
        for child in tuple(self.children):
            child._prune()
        if self.parent is not None:
            self.parent.children.remove(self)
        for parent_path in self.path.parents:
            tree_index = tree_indices.get(parent_path, None)
            if tree_index is not None:
                tree_index._descendants.remove(self)

    def _descendants(self) -> Iterator[DirIndex]:
        '''
        Yield all instantiated `DirIndex` objects corresponding to the
        directory's direct and indirect subdirectories.
        '''
        yield self
        for child in self.children:
            yield from child._descendants()


class TreeIndex:
    '''
    An index of entries in a directory tree.

    A `TreeIndex` can be constructed to keep its descendants from being
    garbage-collected. Search operations can be performed by calling methods on
    its `root` attribute.
    '''
    root: DirIndex; (
        'The `DirIndex` for the root of the tree.')
    _descendants: Set[DirIndex]; (
        'All instantiated `DirIndex` objects '
        'corresponding to directories in the tree.')

    def __new__(cls, path: Path) -> TreeIndex:
        try:
            return tree_indices[path]
        except KeyError:
            instance = object.__new__(cls)
            instance.root = DirIndex(path)
            instance._descendants = set(instance.root._descendants())
            tree_indices[path] = instance
            return instance


def validate_meta(meta: object) -> Dict[str, Any]:
    '''
    Return an object unchanged if it is a valid artifact metadata `dict`, and
    raise a `TypeError` if it is not.
    '''
    if (isinstance(meta, dict)
        and isinstance(meta.get('spec', None), dict)
        and isinstance(meta.get('events', None), list)
        and all(isinstance(e, dict)
                and isinstance(e.get('type', None), str)
                and isinstance(e.get('timestamp', None), str)
                for e in meta['events'])):
        return meta
    else:
        raise TypeError()
