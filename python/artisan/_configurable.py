import ast
from inspect import getsource
from pathlib import Path
from textwrap import dedent
from typing import Any, DefaultDict, Dict, Iterator, List, Mapping, Tuple, cast

from ruamel import yaml

from ._global_conf import get_conf, default_scope

__all__ = ['Configurable']

#-- Configurable object metaclass ---------------------------------------------

class ConfigurableMeta(type):
    def __init__(self,
                 name: str,
                 bases: Tuple[type, ...],
                 dict_: Dict[str, object]) -> None:

        super().__init__(name, bases, dict_)

        self.Spec = type('Spec', (Spec,), {'_impl': self})
        
        entry = default_scope.get(name, None)
        default_scope[name] = (
            self if entry is None else
            [*entry, self] if isinstance(entry, list) else
            [entry, self]
        )


class Spec:
    _impl: type

#-- Configurable objects ------------------------------------------------------

Rec = Mapping[str, object]
Tuple_ = Tuple[object, ...]

class Configurable(metaclass=ConfigurableMeta):
    '''
    An object that can be constructed from a JSON-object-like structure

    A JSON-object-like structure is a string-keyed mapping composed of
    arbitrarily nested `bool`, `int`, `float`, `str`, `NoneType`, sequence, and
    string-keyed mapping objects.
    '''
    def __new__(cls, spec: Rec, *args: object, **kwargs: object) -> 'Configurable':
        type_name = spec.get('type', None)
        assert type_name is None or isinstance(type_name, str)
        type_ = cls if type_name is None else _resolve(type_name)
        assert isinstance(type_, type) and issubclass(type_, cls)
        obj = cast('Configurable', super().__new__(type_))
        obj.conf = _namespacify({k: v for k, v in spec.items() if k != 'type'})
        return obj

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

#-- Global metadata writing ---------------------------------------------------

def write_meta() -> None:
    '''
    Write global config information to `{root_path}/_meta.yaml`.
    '''
    meta = {'spec': None, 'schema': _full_schema()}
    meta_text = yaml.round_trip_dump(meta)
    Path(f'{get_conf().root_dir}/_meta.yaml').write_text(meta_text)

#-- Symbol <-> object mapping -------------------------------------------------

def _resolve(sym: str) -> type:
    '''
    Search the current scope for a `Configurable` subclass.
    '''
    try: return get_conf().scope[sym]
    except: raise KeyError(f'"{sym}" is not present in the current scope.')


def _identify(type_: type) -> str:
    '''
    Search the current scope for a `Configurable` subclass's name.
    '''
    for sym, val in get_conf().scope.items():
        if val is type_: return sym
    raise KeyError(f'"{type_}" is not present in the current scope.')

#-- JSON-Schema extraction ----------------------------------------------------

def _full_schema() -> dict:
    '''
    Return a schema with a definition for each exposed object type.
    '''
    return {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'definitions': {
            sym: _root_schema_from_type(cast(ConfigurableMeta, type_))
            for sym, type_ in get_conf().scope.items()
        }
    }


def _root_schema_from_type(type_: type) -> dict:
    '''
    Return a schema for the specification of a `type_` instance.
    '''
    # Concrete types
    if len(type_.__subclasses__()) == 0:
        desc, outputDesc = _extended_docstrings(type_)
        prop_schemas = _prop_schemas_from_type(type_)
        return {
            'type': 'object',
            'description': desc,
            'outputDescriptions': outputDesc,
            'properties': prop_schemas,
            'required': [
                prop_name
                for prop_name, schema in prop_schemas.items()
                if 'default' not in schema
            ]
        }

    # Abstract types
    else:
        return {'oneOf': [
            {'allOf': [
                {'required': ['type']},
                {'properties': {'type': {'const': _identify(type_)}}},
                {'$ref': '#/definitions/'+_identify(type_)}
            ]}
            for sub in type_.__subclasses__()
            if len(sub.__subclasses__()) == 0
            and sub in get_conf().scope.values()
        ]}


def _prop_schemas_from_type(type_: type) -> Dict[str, dict]:
    '''
    Return schemas for `type_`'s configuration properties.
    '''
    Conf = getattr(type_, 'Conf', type('', (), {}))
    prop_schemas = DefaultDict[str, dict](lambda: {})

    # Find type annotations.
    for key, ann in getattr(Conf, '__annotations__', {}).items():
        prop_schemas[key].update(_prop_schema_from_ann(ann))

    # Find default values.
    for key, val in vars(Conf).items():
        if not key.startswith('__'):
            prop_schemas[key]['default'] = val

    # Find docstrings.
    for key, doc in _extended_docstrings(Conf)[1].items():
        prop_schemas[key]['description'] = doc

    return dict(prop_schemas)


def _prop_schema_from_ann(ann: type) -> dict:
    '''
    Generate a property schema from a type annotation.
    '''
    if ann == bool:
        return {'type': 'boolean'}
    elif ann == int:
        return {'type': 'integer'}
    elif ann == float:
        return {'type': 'number'}
    elif ann == str:
        return {'type': 'string'}
    elif issubclass(ann, List):
        item_schema = _prop_schema_from_ann(ann.__args__[0]) # type: ignore
        return {'type': 'array', 'items': item_schema}
    elif issubclass(ann, Configurable):
        return {'$ref': '#/definitions/'+_identify(ann)}
    else:
        raise ValueError(f'Type "{ann}" can\'t be mapped to a schema.')

#-- Syntax tree parsing -------------------------------------------------------

def _extended_docstrings(t: type) -> Tuple[str, Dict[str, str]]:
    '''
    Collect and return (`root_doc`, `field_docs`) for `t`.
    '''
    desc = ''
    outputDesc: Dict[str, str] = {}
    curr_field = None

    for stmt in _statements_in_def(t):
        # Store the statment's value if it's a string literal.
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Str):
            content = dedent(ast.literal_eval(stmt.value)).strip()
            if curr_field is None:
                desc = desc + '\n\n' + content
            else:
                outputDesc[curr_field] = content

        # Compute the current field.
        if (isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)):
            curr_field = stmt.targets[0].id

        elif (isinstance(stmt, ast.AnnAssign)
              and isinstance(stmt.target, ast.Name)):
            curr_field = stmt.target.id

        else:
            curr_field = None

    return desc, outputDesc


def _statements_in_def(t: type) -> Iterator[ast.stmt]:
    '''
    Yield the statement's in `t`'s definition, if it can be located.
    '''
    try:
        mod_def = cast(ast.Module, ast.parse(dedent(getsource(t))))
        cls_def = cast(ast.ClassDef, mod_def.body[0])
        yield from cls_def.body
    except (OSError, TypeError):
        pass