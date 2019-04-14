from typing import Dict, Mapping, Tuple, cast
from importlib import import_module

from ._global_conf import conf_stack, default_scope

__all__ = ['Configurable']

#-- Configurable object metaclass ---------------------------------------------

class ConfigurableMeta(type):
    def __init__(self,
                 name: str,
                 bases: Tuple[type, ...],
                 dict_: Dict[str, object]) -> None:
        ''
        super().__init__(name, bases, dict_)
        entry = default_scope.get(name, None)
        default_scope[name] = (
            self if entry is None else
            [*entry, self] if isinstance(entry, list) else
            [entry, self]
        )

#-- Configurable objects ------------------------------------------------------

Rec = Mapping[str, object]
Tuple_ = Tuple[object, ...]

class Configurable(metaclass=ConfigurableMeta):
    '''
    An object that can be constructed from a JSON-object-like structure.

    A JSON-object-like structure is a string-keyed mapping composed of
    arbitrarily nested `bool`, `int`, `float`, `str`, `NoneType`, sequence, and
    string-keyed mappings.
    '''
    def __new__(cls, spec: Rec, *args: object, **kwargs: object) -> 'Configurable':
        type_name = spec.get('type', None)
        assert isinstance(type_name, str)
        type_ = cls if type_name is None else _resolve(type_name)
        assert isinstance(type_, type) and issubclass(type_, cls)
        return cast('Configurable', super().__new__(type_))

#-- Symbol <-> object mapping -------------------------------------------------

def _resolve(sym: str) -> object:
    ''' Search the current scope for an object. '''
    if sym in conf_stack.get().scope:
        return conf_stack.get().scope[sym]
    try:
        mod_name, type_name = sym.split('$')
        mod = import_module(mod_name)
        return cast(object, getattr(mod, type_name))
    except:
        raise KeyError(f'"{sym}" is not present in the current scope')
