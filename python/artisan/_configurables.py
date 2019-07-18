'''
This module defines `Configurable`, a class of objects whose constructors accept
a JSON-like configuration as their first argument. Configurable objects provide
the following features:

- A `conf` field that stores the configuration passed into the constructor
- The ability to define a `Conf` class (which is converted to a JSON-Schema)
  that documents/validates the expected form of the configuration
- Subclass forwarding — If the configuration contains a "type" field, it
  determines the class of `Configurable` that is constructed. This is useful
  e.g. when constructing objects from deserialized configurations.
'''
from itertools import chain
import threading
from typing import (
    DefaultDict, Dict, Iterator, Mapping, Optional, Tuple, Type
)
from typing_extensions import Protocol

from ._namespaces import Namespace, namespacify
from ._schemas import conf_schema_from_type

__all__ = [
    'Configurable', 'get_default_scope',
    'get_schema', 'get_scope', 'set_scope'
]

#-- Scope management ----------------------------------------------------------

context = threading.local()

def set_scope(scope: Optional[Dict[str, type]]) -> None:
    '''
    Set the scope used for "type" field resolution.
    '''
    if hasattr(context, 'scope'):
        del context.scope
    if scope is not None:
        context.scope = scope


def get_scope() -> Dict[str, type]:
    '''
    Return the scope used for "type" field resolution.
    '''
    return context.scope if hasattr(context, 'scope') else get_default_scope()


def get_default_scope() -> Dict[str, type]:
    '''
    Return the default scope used for "type" field resolution.
    '''
    def subclasses(t: type) -> Iterator[type]:
        yield from chain([t], *map(subclasses, t.__subclasses__()))
    scope: Dict[str, type] = {}
    for t in subclasses(Configurable):
        if t.__qualname__ in scope:
            t1 = scope.pop(t.__qualname__)
            scope[f'{t.__module__}.{t.__qualname__}'] = t
            scope[f'{t1.__module__}.{t1.__qualname__}'] = t1
        else:
            scope[t.__qualname__] = t
    return scope

#-- Schema generation ---------------------------------------------------------

def get_schema() -> dict:
    '''
    Return a schema with a definition for each exposed type.
    '''
    scope = get_scope()
    return {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'definitions': {
            sym: conf_schema_from_type(type_, scope)
            for sym, type_ in scope.items()
        },
        '$ref': '#/definitions/Configurable'
    }

#-- Configurable objects ------------------------------------------------------

class GenericConf(Protocol):
    '''
    [A descriptor type that enables Jedi autocompletion support for conf fields]
    '''
    def __get__(self, obj, type_):
        return obj.Conf()


class Configurable:
    '''
    An object whose behavior is configured via a JSON-object-like configuration
    passed as the first argument to its constructor

    Parameters:
        conf: a mapping/namespace composed of arbitrarily nested `bool`, `int`,
            `float`, `str`, `NoneType`, sequence, and mapping/namespace
            instances (namespace := an object with a `__dict__` attribute).

    If `conf` contains a "type" field that is a `type`, `__new__` returns an
    instance of that type.

    Similarly, if `conf` contains a "type" field that is a string, `__new__`
    dereferences it in the current type scope and returns an instance of the
    resulting type (the `Artisan` class can be used to manipulate the type
    scope).
    '''

    class Conf(Protocol):
        '''
        A configuration

        If its definition is inline (lexically within the containing class'
        definition), it will be translated into a JSON-Schema to validate
        configurations passed into the outer class' constructor.

        `Conf` classes are intended to be interface definitions. They can extend
        `typing_extensions.Protocol` to support static analysis.

        An empty `Conf` definition is created for every `Configurable` subclass
        defined without one.
        '''
        pass

    conf: GenericConf; '''
        The configuration passed into the constructor, coerced to a `Namespace`
    '''

    def __new__(cls,
                conf: object,
                *args: object,
                **kwargs: object) -> 'Configurable':

        # Coerce `conf` to a `dict`.
        conf = dict(
            conf if isinstance(conf, Mapping)
            else getattr(conf, '__dict__', {})
        )

        # Perform subclass forwarding.
        cls_override = conf.pop('type', None)
        if isinstance(cls_override, type):
            cls = cls_override
        elif isinstance(cls_override, str):
            try: cls = get_scope()[cls_override]
            except: raise KeyError(f'"{cls_override}" can\'t be resolved.')

        # Construct and return a `Configurable` instance.
        obj = object.__new__(cls)
        object.__setattr__(obj, 'conf', namespacify(conf))
        return obj

#------------------------------------------------------------------------------
# Monkey-patch `Configurable` to generate `Conf` types for its subclasses.

class ConfAccessor:
    def __get__(self, obj: object, type_: type) -> type:
        type_.Conf = type('Conf', (Protocol,), {}) # type: ignore
        return type_.Conf # type: ignore

setattr(Configurable, 'Conf', ConfAccessor())