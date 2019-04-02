from toolz import valmap
from typing import Any, Dict

__all__ = ['Namespace', 'namespacify']

#------------------------------------------------------------------------------
# Attribute-access-supporting dictionaries

# TODO: make a "marked read fields" version

class Namespace(Dict[str, object]):
    'A `dict` that supports accessing items as attributes'

    def __getattr__(self, key: str) -> Any:
        return dict.__getitem__(self, key)

    def __setattr__(self, key: str, val: object) -> None:
        dict.__setitem__(self, key, val)

    def __getattribute__(self, key: str) -> Any:
        if key == '__dict__': return self
        else: return object.__getattribute__(self, key)


def namespacify(obj: object) -> object:
    if isinstance(obj, dict):
        return Namespace(valmap(namespacify, obj))
    elif isinstance(obj, list):
        return list(map(namespacify, obj))
    else:
        return obj
