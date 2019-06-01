from typing import Dict, Mapping, Tuple
from typing_extensions import Protocol, runtime

from ._global_conf import get_conf, default_scope
from ._namespaces import Namespace, namespacify
from ._schemas import conf_schema_from_type

__all__ = ['Configurable', 'NameConflict', 'schema']

#-- Configurable object metaclass ---------------------------------------------

class ConfigurableMeta(type):
    '''
    A type that generates an inner `Conf` class and adds itself to the default
    Artisan scope upon creation

    `ConfigurableMeta` is the metaclass for `Configurable`.
    '''
    def __init__(self,
                 name: str,
                 bases: Tuple[type, ...],
                 dict_: Dict[str, object]) -> None:

        super().__init__(name, bases, dict_)

        # Generate `Conf` if it does not exist.
        if not hasattr(self, 'Conf'):
            self.Conf = runtime(type('Conf', (Protocol,), { # type: ignore
                '__qualname__': self.__qualname__+'.Conf',
                '__module__': self.__module__
            }))

        # Make the configurable class accessable from the configuration class.
        self.Conf.__recipient_type__ = self # type: ignore

        # Add the configurable class to the default scope.
        default_scope[self.__qualname__] = (
            NameConflict if self.__qualname__ in default_scope
            else self
        )


class NameConflict:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise KeyError('[Name conflict in the current Artisan scope]')

#-- Configurable objects ------------------------------------------------------

class Configurable(metaclass=ConfigurableMeta):
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
    resulting type (see `push_conf`/`pop_conf`/`get_conf`).
    '''

    class Conf(Protocol):
        '''
        A configuration

        If its definition is inline, it will be translated into a JSON-Schema to
        validate configurations passed into the outer class' constructor.

        `Conf` classes are intended to be interface definitions. They can extend
        `typing_extensions.Protocol` to support static analysis and `isinstance`
        calls (with the `typing_extensions.runtime` decorator).

        An empty `Conf` definition is created for every `Configurable` subclass
        defined without one.
        '''
        pass

    conf: Namespace; '''
        The configuration passed into the constructer, coerced to a `Namespace`
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
            try: cls = get_conf().scope[cls_override]
            except: raise KeyError(f'"{cls_override}" can\'t be resolved.')

        # Construct and return a `Configurable` instance.
        obj = object.__new__(cls)
        object.__setattr__(obj, 'conf', namespacify(conf))
        return obj

#-- Schema generation ---------------------------------------------------------

def schema() -> dict:
    '''
    Return a schema with a definition for each exposed type.
    '''
    conf_types = {
        sym: type_.Conf # type: ignore
        for sym, type_ in get_conf().scope.items()
        if hasattr(type_, 'Conf')
    }
    return {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'definitions': {
            sym: conf_schema_from_type(type_, conf_types)
            for sym, type_ in get_conf().scope.items()
        },
        '$ref': '#/definitions/Configurable'
    }
