from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from ruamel import yaml

from ._global_conf import get_conf, default_scope
from ._schemas import conf_schema_from_type

__all__ = ['Configurable', 'write_meta']

#-- Configurable object metaclass ---------------------------------------------

class ConfigurableMeta(type):
    def __init__(self,
                 name: str,
                 bases: Tuple[type, ...],
                 dict_: Dict[str, object]) -> None:

        super().__init__(name, bases, dict_)
        self.Spec = type('Spec', (Spec,), {'_impl': self})
        default_scope[name] = (
            type('NameConflict', (), {})
            if name in default_scope
            else self
        )


class Spec:
    _impl: type

#-- Configurable objects ------------------------------------------------------

class Configurable(metaclass=ConfigurableMeta):
    '''
    An object that can be constructed from a JSON-object-like structure

    A JSON-object-like structure is a string-keyed mapping composed of
    arbitrarily nested `bool`, `int`, `float`, `str`, `NoneType`, sequence, and
    string-keyed mapping objects.
    '''
    Spec = Dict[str, object]

    def __new__(cls, spec: Mapping[str, object],
                *args: object, **kwargs: object) -> 'Configurable':

        if 'type' in spec:
            sym = spec['type']
            assert isinstance(sym, str), '`spec[\'type\']` must be a string.'
            try: cls = get_conf().scope[sym]
            except: raise KeyError(f'"{sym}" can\'t be resolved.')

        obj = object.__new__(cls)
        object.__setattr__(obj, 'conf', _namespacify({
            k: v for k, v in spec.items() if k != 'type'
        }))
        return obj

#-- Namespaces ----------------------------------------------------------------

class _Namespace(Dict[str, object]):
    '''
    A `dict` that supports accessing items as attributes
    '''
    def __getattr__(self, key: str) -> Any:
        return dict.__getitem__(self, key)

    def __setattr__(self, key: str, val: object) -> None:
        dict.__setitem__(self, key, val)

    def __getattribute__(self, key: str) -> Any:
        if key == '__dict__': return self
        else: return object.__getattribute__(self, key)


def _namespacify(obj: object) -> object:
    '''
    Recursively convert dictionaries to namespaces.
    '''
    if isinstance(obj, dict):
        return _Namespace({k: _namespacify(obj[k]) for k in obj})
    elif isinstance(obj, list):
        return [_namespacify(v) for v in obj]
    else:
        return obj

#-- Global metadata writing ---------------------------------------------------

def write_meta() -> None:
    '''
    Write global config information to `{root_path}/_meta.yaml`.
    '''
    meta = {'spec': None, 'schema': _full_schema()}
    meta_text = yaml.round_trip_dump(meta)
    Path(f'{get_conf().root_dir}/_meta.yaml').write_text(meta_text)


def _full_schema() -> dict:
    '''
    Return a schema with a definition for each exposed object type.
    '''
    spec_types = {
        k: v.Spec # type: ignore
        for k, v in get_conf().scope.items()
        if hasattr(v, 'Spec')
    }
    return {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'definitions': {
            sym: conf_schema_from_type(type_, spec_types)
            for sym, type_ in get_conf().scope.items()
        }
    }
