import ast
from inspect import getsource
from textwrap import dedent
from typing import (
    Any, DefaultDict, Dict, Iterator, List, Optional, Tuple, Union, cast
)

__all__ = ['conf_schema_from_type']

#-- Type aliases --------------------------------------------------------------

ObjDict = Dict[str, object]
TypeDict = Dict[str, type]

#-- Top-level configuration schema generation ---------------------------------

def conf_schema_from_type(type_: type, scope: TypeDict = {}) -> ObjDict:
    '''
    Return a schema for the configuration of a `type_` instance.
    '''
    is_strict_subclass = lambda t: t is not type_ and issubclass(t, type_)
    if any(map(is_strict_subclass, scope.values())):
        return conf_schema_from_abstract_type(type_, scope)
    else:
        return conf_schema_from_concrete_type(type_, scope)


def conf_schema_from_abstract_type(type_: type, scope: TypeDict) -> ObjDict:
    '''
    Return a configuration schema for a type with subtypes.
    '''
    return {'oneOf': [
        {'allOf': [
            {'required': ['type']},
            {'properties': {'type': {'const': name}}},
            {'$ref': '#/definitions/'+name}
        ]}
        for name, t in scope.items()
        if issubclass(t, type_)
        and t is not type_
    ]}


def conf_schema_from_concrete_type(type_: type, scope: TypeDict) -> ObjDict:
    '''
    Return a configuration schema for a type with no subclasses.
    '''
    try:
        mod_def = cast(ast.Module, ast.parse(dedent(getsource(type_))))
        cls_def = cast(ast.ClassDef, mod_def.body[0])
    except (OSError, TypeError):
        cls_def = ast.ClassDef('', (), (), [], [])

    Conf = getattr(type_, 'Conf', type('', (), {}))
    conf_def = ast.ClassDef('', (), (), [], [])
    for stmt in cls_def.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == 'Conf':
            conf_def = stmt

    schema: dict = {
        'type': 'object',
        'description': [],
        'outputDescriptions': {},
        'properties': DefaultDict[str, dict](lambda: {})
    }

    # Collect `description` & `ouputDescriptions`.
    for tgt, ann in literal_annotations(cls_def):
        if isinstance(ann, str):
            if tgt is None:
                schema['description'].append(dedent(ann).strip())
            else:
                schema['outputDescriptions'][tgt] = dedent(ann).strip()

    # Collect property type annotations.
    for tgt, ann in getattr(Conf, '__annotations__', {}).items():
        schema['properties'][tgt].update(schema_from_type_ann(ann, scope))

    # Collect property defaults.
    for key, val in vars(Conf).items():
        if not key.startswith('_'):
            schema['properties'][key]['default'] = val

    # Collect property descriptions and raw property schema.
    for tgt, ann in literal_annotations(conf_def):
        tgt_schema = schema if tgt is None else schema['properties'][tgt]
        tgt_schema.update(schema_from_literal_ann(ann))

    # Define required properties.
    schema['required'] = [
        key for key, val in schema['properties'].items()
        if 'default' not in val
    ]

    schema['description'] = '\n\n'.join(schema['description'])
    schema['properties'] = dict(schema['properties'])
    return schema

#-- Configuration property schema generation ----------------------------------

def schema_from_type_ann(ann: Any, scope: TypeDict) -> ObjDict:
    '''
    Generate a property schema from a type annotation.
    '''
    ann_metatype = getattr(ann, '__origin__', None)

    if ann is object or ann is Any:
        return {}

    elif ann is None or ann is type(None):
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

    elif ann_metatype == Union:
        return {'oneOf': [
            schema_from_type_ann(t, scope)
            for t in ann.__args__
        ]}

    elif ann_metatype in (list, List):
        item_schema = schema_from_type_ann(ann.__args__[0], scope)
        return {'type': 'array', 'items': item_schema}

    elif ann_metatype in (dict, Dict) and ann.__args__[0] is str:
        item_schema = schema_from_type_ann(ann.__args__[1], scope)
        return {'type': 'object', 'additionalProperties': item_schema}

    elif ann in scope.values():
        name = next(k for k, v in scope.items() if v is ann)
        return {'$ref': '#/definitions/'+name}

    else:
        raise ValueError(f'Type "{ann}" can\'t be mapped to a schema.')


def schema_from_literal_ann(ann: object) -> ObjDict:
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

#-- Syntax tree parsing -------------------------------------------------------

def literal_annotations(cls_def: ast.ClassDef) -> (
        Iterator[Tuple[Optional[str], object]]):
    '''
    Yield (target, annotation) pairs for the literal annotations in a class
    definition.
    '''
    curr_field: Optional[str] = None
    for stmt in cls_def.body:
        # Yield the statment's value if it's a literal.
        if isinstance(stmt, ast.Expr):
            try: yield curr_field, ast.literal_eval(stmt.value)
            except ValueError: pass

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
