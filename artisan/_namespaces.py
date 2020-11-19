'''
General-purpose namespaces and JSON compatibility.

Exported definitions:
    Namespace (`SimpleNamespace` subclass):
        A `SimpleNamespace` that prints readably.

Internal definitions:
    dictify (function):
        Deeply convert namespaces in an object to dictionaries.
    namespacify (function):
        Deeply convert mappings in an object to namespaces.
'''

from os import PathLike
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, List, Mapping, Optional, Sequence

__all__ = ['Namespace', 'dictify', 'namespacify']



#-- `Namespace` ----------------------------------------------------------------

class Namespace(SimpleNamespace):
    '''
    A `SimpleNamespace` that prints readably.
    '''
    def __repr__(self) -> str:
        return indented_repr(self, 0, 0)



#-- `Namespace` <-> JSON-like object conversion --------------------------------

def dictify(obj: object,
            path_encoder: Optional[Callable[[PathLike], str]] = None,
            type_encoder: Optional[Callable[[type], str]] = None
            ) -> Any:
    '''
    Deeply convert namespaces in an object to dictionaries.

    If a path encoder is provided, it is used to convert path-like objects to
    strings. Private attributes (attributes whose names start with "_") are
    ignored. If a type encoder is provided, it is used to convert types to
    strings.
    '''
    if isinstance(obj, PathLike) and path_encoder:
        return path_encoder(obj)
    elif isinstance(obj, type) and type_encoder:
        return type_encoder(obj)
    elif isinstance(obj, (type(None), bool, int, float, str, bytes)):
        return obj
    elif isinstance(obj, Sequence):
        return [dictify(v, path_encoder, type_encoder) for v in obj]
    elif isinstance(obj, Mapping):
        return {k: dictify(v, path_encoder, type_encoder)
                for k, v in obj.items()}
    elif hasattr(obj, '__dict__'):
        return {k: dictify(v, path_encoder, type_encoder)
                for k, v in vars(obj).items()
                if not k.startswith('_')}
    else:
        return obj


def namespacify(obj: object,
                path_decoder: Optional[Callable[[str], PathLike]] = None
                ) -> Any:
    '''
    Deeply convert mappings in an object to namespaces.

    If a path decoder is provided, it is used to convert strings starting with
    "@/" to path-like objects.
    '''
    if isinstance(obj, str) and obj.startswith('@/') and path_decoder:
        return path_decoder(obj)
    elif isinstance(obj, (type(None), bool, int, float, str, bytes)):
        return obj
    elif isinstance(obj, Sequence):
        return [namespacify(v, path_decoder) for v in obj]
    elif isinstance(obj, Mapping):
        return Namespace(**{
            k: namespacify(v, path_decoder)
            for k, v in obj.items()})
    else:
        return obj



#-- Formatting -----------------------------------------------------------------

def indented_repr(obj: object, curr_col: int, indent: int) -> str:
    '''
    Return a string representing `obj` to be printed starting at the column
    `curr_col`, indented `indent` spaces, and avoiding extending past column 80
    when possible.
    '''
    sl_repr = single_line_repr(obj)
    if len(sl_repr) <= 80 - curr_col:
        return sl_repr
    elif isinstance(obj, list):
        return (
            '[\n'
            + ' ' * (indent + 2)
            + (',\n' + ' ' * (indent + 2)).join(
                indented_repr(elem, indent + 2, indent + 2)
                for elem in obj)
            + '\n' + ' ' * indent + ']')
    elif isinstance(obj, Namespace):
        return (
            f'{obj.__class__.__qualname__}(\n'
            + ' ' * (indent + 2)
            + (',\n' + ' ' * (indent + 2)).join(
                f'{k} = {indented_repr(v, indent + 5 + len(k), indent + 2)}'
                for k, v in vars(obj).items())
            + '\n' + ' ' * indent + ')')
    else:
        return repr(obj)


def single_line_repr(obj: object) -> str:
    '''
    Return a single-line string representing `obj`.
    '''
    if isinstance(obj, list):
        return '[' + ', '.join(map(single_line_repr, obj)) + ']'
    elif isinstance(obj, Namespace):
        return (
            f'{obj.__class__.__qualname__}('
            + ', '.join(
                f'{k}={single_line_repr(v)}'
                for k, v in vars(obj).items())
            + ')')
    else:
        return repr(obj).replace('\n', ' ')
