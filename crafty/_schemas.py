
# def _identify(obj: object) -> str:
#     'Search the current scope for an object\'s name.'
#     for sym, val in get_conf().scope.items():
#         if val is obj: return sym
#     return f'{obj.__module__}${cast(Any, obj).__qualname__}'


# def _resolve(sym: str) -> object:
#     'Search the current scope for an object.'
#     if sym in get_conf().scope:
#         return get_conf().scope[sym]
#     try:
#         mod_name, type_name = sym.split('$')
#         mod = importlib.import_module(mod_name)
#         return cast(object, getattr(mod, type_name))
#     except:
#         raise KeyError(f'"{sym}" is not present in the current scope')

# def _schema_from_type(t):
#     if t == bool:
#         return dict(type='boolean')
#     elif t == int:
#         return dict(type='integer')
#     elif t == float:
#         return dict(type='number')
#     elif t == str:
#         return dict(type='string')
#     elif type(t) == type(List) and t.__base__ == List:
#         return dict(type='array', items=_schema_from_type(t.__args__[0]))
#     elif issubclass(t, Configurable):
#         return {'$ref': '#/definitions/'+_identify(t)}
#     else:
#         raise ValueError(f'Type "{t}" can\'t be mapped to a schema.')


# def _schema_from_prop_spec(prop_spec):
#     if not isinstance(prop_spec, tuple):
#         prop_spec = (prop_spec,)
#     schema = {}
#     for e in prop_spec:
#         if isinstance(e, type):
#             schema.update(_schema_from_type(e))
#         elif isinstance(e, list):
#             schema['default'] = e[0]
#         elif isinstance(e, str):
#             schema['description'] = e
#         elif isinstance(e, dict):
#             schema.update(e)
#     return schema


# def _spec_schema(type_):
#     # Concrete types
#     if len(type_.__subclasses__()) == 0:
#         prop_schemas = {
#             k: _schema_from_prop_spec(v)
#             for k, v in vars(type_.Conf).items()
#             if not k.startswith('__')
#         }
#         return dict(
#             type='object',
#             properties=prop_schemas,
#             required=[
#                 prop_name
#                 for prop_name, schema in prop_schemas.items()
#                 if 'default' not in schema
#             ]
#         )
#     # Abstract types
#     else:
#         return {'oneOf': [
#             {'allOf': [
#                 {'required': ['type'],
#                  'properties': {'type': {'const': _identify(t)}}},
#                 {'$ref': '#/definitions/'+_identify(t)}
#             ]}
#             for t in type_.__subclasses__()
#             if len(t.__subclasses__()) == 0
#         ]}


# def _collect_definitions(defs, schema):
#     if isinstance(schema, dict) and '$ref' in schema:
#         sym = schema['$ref'][len('#/definitions/'):]
#         if sym not in defs:
#             defs[sym] = _spec_schema(resolve(sym))
#             _collect_definitions(defs, defs[sym])
#     elif isinstance(schema, dict):
#         for subschema in schema.values():
#             _collect_definitions(defs, subschema)
#     elif isinstance(schema, list):
#         for subschema in schema:
#             _collect_definitions(defs, subschema)


# def _with_definitions(schema):
#     defs = {}
#     _collect_definitions(defs, schema)
#     return dict(definitions=defs, **schema)


# def _command_schema():
#     defs = {}
#     options = [
#         {'allOf': [
#             {'required': ['type'],
#              'properties': {'type': {'const': sym}}},
#             {'$ref': '#/definitions/'+sym}
#         ]}
#         for sym, val in get_conf().scope.items()
#         if issubclass(val, Command) and len(val.__subclasses__()) == 0
#     ]
#     _collect_definitions(defs, options)
#     return dict(definitions=defs, oneOf=options)


# import ast, inspect
# from dataclasses import fields, MISSING
# from typing import Tuple
# Rec = Dict[str, object]


# def _get_annotations(type_: type) -> Dict[str, Rec]:
#     try: src = inspect.getsource(type_)
#     except (OSError, TypeError): return {}

#     fields_ = fields(type_)
#     anns: Dict[str, Rec] = {f.name: {} for f in fields_}
#     for f in fields_:
#         if f.type != MISSING:
#             anns[f.name].update(_schema_from_type(f.type))
#         if f.default != MISSING:
#             anns[f.name]['default'] = f.default

#     curr_field = None
#     for node in cast(ast.ClassDef, ast.parse(src).body[0]).body:
#         if (isinstance(node, ast.AnnAssign)
#             and isinstance(node.target, ast.Name)):
#             curr_field = node.target.id

#         elif (isinstance(node, ast.Assign)
#             and len(node.targets) == 1
#             and isinstance(node.targets[0], ast.Name)):
#             curr_field = node.targets[0].id

#         elif curr_field is not None:
#             if isinstance(node, ast.Expr):
#                 try:
#                     val = ast.literal_eval(node.value)
#                     if not isinstance(val, (tuple, list)):
#                         val = [val]
#                     for i, elem in enumerate(val):
#                         if isinstance(elem, dict):
#                             anns[curr_field].update(elem)
#                         elif isinstance(elem, str):
#                             anns[curr_field]['description'] = elem
#                 except ValueError:
#                     pass
#             curr_field = None

#     return anns
