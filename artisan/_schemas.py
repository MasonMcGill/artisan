'''
JSON Schema generation.

Exported definitions:
    get_spec_schema (function):
        Return a JSON Schema describing valid artifact specifications.
    get_spec_list_schema (function):
        Return a JSON Schema describing lists of artifact specifications.
    get_spec_dict_schema (function):
        Return a JSON Schema describing artifact specification dictionaries.
'''

import ast
from functools import lru_cache
from inspect import getsource, cleandoc
from os import PathLike
from pathlib import Path
from textwrap import dedent
from typing import (
    Any, DefaultDict, Dict, Iterator, List, Mapping, Optional,
    Tuple, Union, cast, get_args, get_origin, get_type_hints)
from typing_extensions import Literal

from ._artifacts import Artifact, active_root
from ._namespaces import dictify
from ._targets import active_scope

__all__ = ['get_spec_dict_schema', 'get_spec_list_schema', 'get_spec_schema']



#-- Specification schema generation --------------------------------------------

def get_spec_schema() -> dict:
    '''
    Return a JSON Schema describing valid artifact specifications.

    The schema will contain a definition corresponding to the `Spec` type of
    every entry in the active scope.
    '''
    scope = active_scope.get()
    def_index = {
        **{
            getattr(type_, 'Spec'): name
            for name, type_ in scope.items()
            if hasattr(type_, 'Spec')
        },
        **{
            type_: f'__PathString::{name}'
            for name, type_ in scope.items()
        }
    }
    return {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        '$defs': {
            **{
                name: spec_schema_from_type(type_, scope, def_index)
                for name, type_ in scope.items()
            },
            **{
                f'__PathString::{name}': {'pattern': '^@\\/.*'}
                for name, type_ in scope.items()
                if issubclass(type_, Artifact)
            }
        },
        'oneOf': [
            {'allOf': [
                {'required': ['type']},
                {'properties': {'type': {'const': name}}},
                {'$ref': f'#/$defs/{name}'}
            ]}
            for name, type_ in scope.items()
            if issubclass(type_, Artifact) and not type_.__subclasses__()
        ]
    }


def get_spec_list_schema() -> dict:
    '''
    Return a JSON Schema describing lists of artifact specifications.

    The schema will contain a definition corresponding to the `Spec` type of
    every entry in the active scope.
    '''
    spec_schema = get_spec_schema()
    return {'$schema': spec_schema['$schema'],
            '$defs': spec_schema['$defs'],
            'type': 'array',
            'items': {'oneOf': spec_schema['oneOf']}}


def get_spec_dict_schema() -> dict:
    '''
    Return a JSON Schema describing artifact specification dictionaries.

    Objects whose entries are artifact specifications will be valid against the
    schema. The schema will contain a definition corresponding to the `Spec`
    type of every entry in the active scope.
    '''
    spec_schema = get_spec_schema()
    return {'$schema': spec_schema['$schema'],
            '$defs': spec_schema['$defs'],
            'type': 'object',
            'properties': {'$schema': {'type': 'string'}},
            'additionalProperties': {'oneOf': spec_schema['oneOf']}}


def spec_schema_from_type(type_: type,
                          scope: Mapping[str, type],
                          def_index: Mapping[type, str]) -> dict:
    '''
    Return a schema for the specification of a `type_` instance.

    A concrete type's schema (the schema of a type with no subclasses in
    `scope`) has the following fields:

    - `type (str)`: "object"
    - `description (str)`: `type_`'s docstring
    - `properties (Dict[str, dict])`: Per-property schemas, including
      descriptions and/or defaults, generated from attribute
      declarations/definitions in `type_`'s inner `Spec` class, if it exists
    - `required (List[str])`: The list of required properties (those without
      default values)

    An abstract type's schema describes the type-tagged union of the schemas
    of its subclasses.
    '''
    if type_.__subclasses__():
        return abstract_spec_schema(type_, scope)
    else:
        return concrete_spec_schema(type_, def_index)


def abstract_spec_schema(type_: type, scope: Mapping[str, type]) -> dict:
    '''
    Return a specification schema for a type with subtypes.
    '''
    return {
        'description': cleandoc(type_.__doc__ or ''),
        'oneOf': [
            {'allOf': [
                {'required': ['type']},
                {'properties': {'type': {'const': name}}},
                {'$ref': f'#/$defs/{name}'}
            ]}
            for name, t in scope.items()
            if issubclass(t, type_) and not t.__subclasses__()
        ]
    }


def concrete_spec_schema(type_: type, def_index: Mapping[type, str]) -> dict:
    '''
    Return a specification schema for a type without subtypes.
    '''
    spec_type = getattr(type_, 'Spec', type('', (), {}))

    # Collect property type annotations.
    properties = DefaultDict[str, dict](dict, {
        key: schema_from_type_ann(ann, def_index)
        for key, ann in type_annotations(spec_type)
    })

    # Collect property defaults.
    for key, val in vars(spec_type).items():
        if not key.startswith('_') and not callable(val):
            encoded_val = dictify(val, encode_path, get_type_name)
            properties[key]['default'] = encoded_val

    # Collect property descriptions and raw property schema.
    for key, ann in literal_annotations(type_, 'Spec'):
        properties[key].update(schema_from_literal_ann(ann))

    return {
        'type': 'object',
        'description': cleandoc(type_.__doc__ or ''),
        'properties': dict(properties),
        'required': [
            key for key, val in properties.items()
            if 'default' not in val
        ]
    }



#-- Supporting definitions -----------------------------------------------------

def schema_from_type_ann(ann: Any, def_index: Mapping[type, str]) -> dict:
    '''
    Generate a property schema from a type annotation.
    '''
    if ann in def_index:
        return {'$ref': f'#/$defs/{def_index[ann]}'}

    elif ann in (object, Path):
        return {}

    elif ann in (None, type(None)):
        return {'type': 'null'}

    elif ann is bool:
        return {'type': 'boolean'}

    elif ann is int:
        return {'type': 'integer'}

    elif ann is float:
        return {'type': 'number'}

    elif ann is str:
        return {'type': 'string'}

    elif ann is list:
        return {'type': 'array'}

    elif ann is dict:
        return {'type': 'object'}

    elif get_origin(ann) is Union:
        return {'oneOf': [
            schema_from_type_ann(t, def_index)
            for t in get_args(ann)
        ]}

    elif get_origin(ann) is Literal:
        return {'enum': list(get_args(ann))}

    elif get_origin(ann) in (list, List):
        item_schema = schema_from_type_ann(get_args(ann)[0], def_index)
        return {'type': 'array', 'items': item_schema}

    elif get_origin(ann) in (dict, Dict) and get_args(ann)[0] is str:
        item_schema = schema_from_type_ann(get_args(ann)[1], def_index)
        return {'type': 'object', 'additionalProperties': item_schema}

    else:
        properties = {
            field: schema_from_type_ann(type_ann, def_index)
            for field, type_ann in type_annotations(ann)
        }
        return {
            'type': 'object',
            'properties': properties,
            'required': list(properties)
        }


def schema_from_literal_ann(ann: object) -> dict:
    '''
    Generate a property schema from a literal annotation.
    '''
    if isinstance(ann, str):
        return {'description': dedent(ann).strip()}

    elif isinstance(ann, dict):
        return ann

    elif (isinstance(ann, tuple) and len(ann) == 2
          and isinstance(ann[0], str) and isinstance(ann[1], dict)):
        return {'description': dedent(ann[0]).strip(), **ann[1]}

    elif (isinstance(ann, tuple) and len(ann) == 2
          and isinstance(ann[0], dict) and isinstance(ann[1], str)):
        return {**ann[0], 'description': dedent(ann[1]).strip()}

    else:
        return {}



#-- Class definition introspection ---------------------------------------------

def type_annotations(type_: type) -> Iterator[Tuple[str, type]]:
    '''
    Yield (target, annotation) pairs for the type annotations in a class
    definition.
    '''
    for t in reversed(type_.mro()):
        for field, ann in get_type_hints(t).items():
            if not field.startswith('_'):
                yield field, ann


@lru_cache(maxsize=None)
def literal_annotations(type_: type,
                        name: Optional[str] = None
                        ) -> List[Tuple[str, object]]:
    '''
    Yield (target, annotation) pairs for the literal annotations in a class
    definition.

    If `name` is a string, use the definition of the inner class with that name.
    '''
    leaf_def = parse_class_def(type_, name)
    type_ = type_ if name is None else getattr(type_, name, type('', (), {}))
    class_defs = [*map(parse_class_def, reversed(type_.mro()[1:])), leaf_def]
    result: List[Tuple[str, object]] = []

    for class_def in class_defs:
        curr_field: Optional[str] = None

        for stmt in class_def.body:
            # Yield the statment's value if it's a post-assignment literal.
            if (isinstance(stmt, ast.Expr)
                and curr_field is not None
                and not curr_field.startswith('_')):
                try:
                    result.append((curr_field, ast.literal_eval(stmt.value)))
                except ValueError:
                    pass

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

    return result


@lru_cache(maxsize=None)
def parse_class_def(type_: type, name: Optional[str] = None) -> ast.ClassDef:
    '''
    Locate, parse, and return the given class' definition.

    If `name` is a string, return the definition of the inner class with that
    name.
    '''
    try:
        mod_def = cast(ast.Module, ast.parse(dedent(getsource(type_))))
        cls_def = cast(ast.ClassDef, mod_def.body[0])
    except (OSError, TypeError):
        cls_def = ast.ClassDef('', (), (), [], [])

    if name is None:
        return cls_def
    else:
        for stmt in cls_def.body:
            if isinstance(stmt, ast.ClassDef) and stmt.name == name:
                return stmt
        else:
            return ast.ClassDef('', (), (), [], [])



#-- Default-value encoding -----------------------------------------------------

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
