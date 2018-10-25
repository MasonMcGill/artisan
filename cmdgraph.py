'''
A small, in-development experiment-logging library designed to take advantage of
YAML, JSON-Schema, HDF5-SWMR, and web-based visualization software.
'''
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import importlib
from inspect import cleandoc
import io
import json
from pathlib import Path
import re
import shutil
from textwrap import indent
from time import sleep
from typing import GenericMeta, List

import bottle
import cbor2
import h5py as h5
import jsonschema
import numpy as np
from ruamel import yaml
from toolz import dissoc, keyfilter, merge, valfilter, valmap

__all__ = [
    'Namespace', 'Configurable',
    'Scope', 'resolve', 'identify', 'create', 'describe',
    'Command', 'Record', 'cli', 'require', 'serve']

################################################################################
# Attribute-access-supporting dictionaries
################################################################################

class Namespace(dict):
    'An `dict` that supports accessing items as attributes'
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

def _namespacify(obj):
    if isinstance(obj, dict):
        return Namespace(valmap(_namespacify, obj))
    elif isinstance(obj, list):
        return list(map(_namespacify, obj))
    else:
        return obj

################################################################################
# Serialization/deserialization
################################################################################

_scopes = []

def _flat_scope():
    return merge(_scopes)

class Scope(dict):
    '''
    A `dict` context that makes its entries available to `resolve` when active.

    If multiple scopes are active, the innermost scope (the one entered
    most recently) takes precedence.
    '''
    def __enter__(self):
        _scopes.append(self)

    def __exit__(self, *_):
        _scopes.remove(self)

def resolve(sym):
    'Search the scope stack and module path for an object.'
    for scope in reversed(_scopes):
        if sym in scope:
            return scope[sym]
    try:
        mod_name, type_name = sym.split('|')
        mod = importlib.import_module(mod_name)
        return getattr(mod, type_name)
    except:
        raise KeyError(
            f'"{sym}" is not present in the '
            'CommandGraph scope stack.')

def identify(obj):
    'Search the scope stack and module path for an object\'s name.'
    for scope in reversed(_scopes):
        for sym, val in scope.items():
            if val is obj:
                return sym
    mod_name = obj.__module__
    obj_name = obj.__qualname__
    return f'{mod_name}|{obj_name}'

def create(spec):
    '''
    Instantiate a configurable object from a specification.

    A specification is a `dict` with

      - a "type" field; the innermost `Scope` symbol corresponding to the
        object's type, or "{module_name}|{type_name}", if none exist.
      - other fields corresponding to the object's configuration properties.
    '''
    return resolve(spec['type'])(**dissoc(dict(spec), 'type'))

def describe(obj):
    '''
    Generate the specification for a configurable object.

    A specification is a `dict` with

      - a "type" field; the innermost `Scope` symbol corresponding to the
        object's type, or "{module_name}|{type_name}", if none exist.
      - other fields corresponding to the object's configuration properties.
    '''
    return Namespace(type=identify(type(obj)), **getattr(obj, 'conf', {}))

################################################################################
# JSON-Schema generation
################################################################################

def _schema_from_type(t):
    if t == bool:
        return dict(type='boolean')
    elif t == int:
        return dict(type='integer')
    elif t == float:
        return dict(type='number')
    elif t == str:
        return dict(type='string')
    elif type(t) == GenericMeta and t.__base__ == List:
        return dict(type='array', items=_schema_from_type(t.__args__[0]))
    else:
        raise ValueError(f'Type "{t}" can\'t be mapped to a schema.')

def _schema_from_prop_spec(prop_spec):
    if not isinstance(prop_spec, tuple):
        prop_spec = (prop_spec,)
    schema = {}
    for e in prop_spec:
        if isinstance(e, type):
            schema.update(_schema_from_type(e))
        elif isinstance(e, list):
            schema['default'] = e[0]
        elif isinstance(e, str):
            schema['description'] = e
        elif isinstance(e, dict):
            schema.update(e)
    return schema

def _conf_schema(type_):
    prop_specs = keyfilter(re.compile('!(^__)').match, vars(type_.Conf))
    prop_schemas = valmap(_schema_from_prop_spec, prop_specs)
    required = [*valfilter(lambda v: 'default' not in v, prop_schemas)]
    return dict(type='object', properties=prop_schemas)

def _spec_schema(type_):
    schema = _conf_schema(type_)
    schema['properties']['type'] = {'const': identify(type_)}
    return schema

def _update_refs(schema):
    if isinstance(schema, dict) and '$ref' in schema:
        prefix = '#/definitions/'
        old_sym = schema['$ref'][len(prefix):]
        new_sym = identify(resolve(old_sym))
        return {'$ref': prefix + new_sym}
    elif isinstance(schema, dict):
        return valmap(_update_refs, schema)
    elif isinstance(schema, list):
        return list(map(_update_refs, schema))
    else:
        return schema

def _command_schema():
    return dict(
        definitions=_update_refs(valmap(_spec_schema, _flat_scope())),
        oneOf=[{'$ref': f'#/definitions/{sym}'}
               for sym, val in _flat_scope().items()
               if issubclass(val, Command)])

################################################################################
# Configurable objects
################################################################################

class ConfigurableMeta(type):
    def __init__(self, *args, **kwargs):
        id_ = self.__module__+'|'+self.__qualname__
        self.conf_schema = _conf_schema(self)
        self.spec_schema = {'$ref': f'#/definitions/{id_}'}

class Configurable(metaclass=ConfigurableMeta):
    '''
    An object that can be constructed from JSON-object-like structures.

    A JSON-object-like structure is a string-keyed `dict` composed of
    arbitrarily nested `bool`, `int`, `float`, `str`, `NoneType`, `list`, and
    string-keyed `dict` instances.

    An object's configuration should be passed to its constructor as a set of
    keyword arguments.
    '''
    class Conf:
        '''
        Override this to specify a configuration schema.

        Members of `Conf` are interpreted in the following way:

        - The member's name corresponds to the expected property's name.
        - A `type` value specify the property's expected type.
        - A single-element `list` value specifies the property's default value.
        - A `str` value specifies the property's docstring.
        - A `dict` value specifies raw JSON-Schema constraints.
        - A `tuple` value may specify any combination of the above.

        Examples:

        .. code-block:: python

            class Person(cg.Configurable):
                class Conf:
                    name = str, 'a long-winded pointer'
                    age = int, [0], 'solar rotation count'
                    shoe_size = 'European standard as of 2018-08-17'
        '''
        pass

    def __init__(self, **conf):
        assert ('type' not in conf), (
            '"type" can\'t be used as a key in configurations')
        self.conf = _namespacify(conf)

    @property
    def spec(self):
        '''
        Return the object's specification.

        A specification is a `dict` with

          - a "type" field; the innermost `Scope` symbol corresponding to the
            object's type, or "{module_name}|{type_name}", if none exist.
          - other fields corresponding to the object's configuration properties.

        (This is equivalent to ``cg.describe(self)``.)
        '''
        return describe(self)

################################################################################
# Commands
################################################################################

class Command(Configurable):
    '''
    An operation that creates a `Record`.

    To specify the output path, define an `output_path` property or define
    `output_path` as a class-level format string to be resolved with the
    command configuration.

    Override `run` to do something useful.
    '''
    def __init__(self, **conf):
        super().__init__(**conf)
        if isinstance(getattr(type(self), 'output_path', None), str):
            self.output_path = Path(type(self).output_path.format(conf))
        self.output = Record(self.output_path)

    def __del__(self):
        dst = Path(self.output_path)
        if self.status == 'running':
            (dst/'_cmd-status.yaml').write_text('stopped')

    def run(self):
        'Override this, writing the output of the command to `cmd.output`.'

    @property
    def status(self):
        '"running", "done", "stopped", or "unbegun".'
        try:
            dst = Path(self.output_path)
            spec = yaml.safe_load((dst/'_cmd-spec.yaml').read_text())
            status = yaml.safe_load((dst/'_cmd-status.yaml').read_text())
            return status if spec == describe(self) else 'unbegun'
        except FileNotFoundError:
            return 'unbegun'

    def __call__(self):
        '''
        Execute the command.

        Performs the following operations:

          - Ensures that the output directory exist **and clears it**.
          - Writes the configuration to `{cmd.output_path}/_cmd-spec.yaml`.
          - Writes "running" to `{cmd.output_path}/_cmd-status.yaml`.
          - Calls `cmd.run`.
          - Writes "done" to `{cmd.output_path}/_cmd-status.yaml`.
        '''
        dst = Path(self.output_path)
        shutil.rmtree(dst, ignore_errors=True)
        dst.mkdir(parents=True, exist_ok=True)
        spec_dict = dict(describe(self))

        # spec_str = yaml.safe_dump(spec_dict, allow_unicode=True)
        import json; spec_str = json.dumps(spec_dict)

        (dst/'_cmd-spec.yaml').write_text(spec_str)
        (dst/'_cmd-status.yaml').write_text('running')
        self.run()
        (dst/'_cmd-status.yaml').write_text('done')

def require(cmd):
    '''
    Ensure that a command has started and block until it is finished.
    '''
    if isinstance(cmd, str): cmd = create(cmd)
    if cmd.status in {'unbegun', 'stopped'}: cmd()
    while cmd.status == 'running': sleep(0.01)
    return Record(cmd.output_path)

################################################################################
# Command records
################################################################################

class _HDF5Entry:
    def __init__(self, path):
        self.path = path
        self.dset = None

    def get(self):
        f = h5.File(self.path, 'r', libver='latest', swmr=True)
        return f['data'][()]

    def put(self, val):
        val = np.asarray(val)
        f = h5.File(self.path, libver='latest')
        f.create_dataset('data', data=val)

    def append(self, val):
        val = np.asarray(val)
        if self.dset is None:
            f = h5.File(self.path, libver='latest')
            self.dset = f.require_dataset(
                name='data', shape=None, maxshape=(None, *val.shape),
                dtype=val.dtype, data=np.empty((0, *val.shape), val.dtype),
                chunks=(int(np.ceil(2**12 / val.size)), *val.shape))
            f.swmr_mode = True
        self.dset.resize(self.dset.len() + 1, 0)
        self.dset[-1] = val
        self.dset.flush()

class Record:
    '''
    A record of the execution of a `Command`.

    A `Record` is an array-friendly view of a directory. It also supports
    reading command metadata (stored in "_cmd-spec.yaml" and "_cmd-status.yaml").

    TODO: Document this more.
    '''
    def __init__(self, path):
        self.path = Path(path)
        self._cache = {}

    def _get_entry(self, key):
        if key not in self._cache:
            self._cache[key] = _HDF5Entry(self.path/f'{key}.h5')
        return self._cache[key]

    def _get_record(self, key):
        if key not in self._cache:
            self._cache[key] = Record(self.path/key)
        return self._cache[key]

    def _forget(self, key):
        self._cache.pop(key, None)

    def __iter__(self):
        for p in self.path.iterdir():
            if not p.name.startswith('_'):
                if p.suffix == '.h5': yield p.name[:-3]
                else: yield p.name

    def __getitem__(self, key):
        key = Path(key)
        path = self.path/key
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_record(key.parts[0])
            return subrec['/'.join(key.parts[1:])]
        elif path.is_dir(): # Return a subrecord
            return self._get_record(key)
        elif path.with_suffix('.h5').is_file(): # Return an array
            return self._get_entry(key).get()
        elif path.is_file(): # Return a file path
            return path
        else:
            raise FileNotFoundError()

    def __setitem__(self, key, val):
        key = Path(key)
        path = self.path/key
        assert key.suffix == '', 'Can\'t write to encoded files'
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_record(key.parts[0])
            subrec['/'.join(key.parts[1:])] = val
        elif isinstance(val, (dict, Record)): # Forward to all subrecords
            for subkey, subval in val.items():
                self[f'{key}/{subkey}'] = subval
        else: # Write an array
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.with_suffix('.h5').exists():
                path.with_suffix('.h5').unlink()
            self._get_entry(key).put(val)

    def __delitem__(self, key):
        key = Path(key)
        path = self.path/key
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_record(key.parts[0])
            del subrec['/'.join(key.parts[1:])]
        elif path.is_dir(): # Delete a subrecord
            rec = self._get_record(key)
            for k in rec: del rec[k]
            shutil.rmtree(path, True)
        elif path.with_extension('.h5').is_file(): # Delete an array
            path.with_extension('.h5').unlink()
        elif path.is_file(): # Delete a non-array file
            path.unlink()
        else:
            raise FileNotFoundError()
        self._forget(key)
        if self.path.stat().st_nlink == 0:
            self.path.rmdir()

    def append(self, key, val):
        key = Path(key)
        path = self.path/key
        assert key.suffix == '', 'Can\'t write to encoded files'
        if len(key.parts) > 1: # Forward to a subrecord
            subrec = self._get_record(key.parts[0])
            subrec.append('/'.join(key.parts[1:]), val)
        elif isinstance(val, (dict, Record)): # Forward to all subrecords
            for subkey, subval in val.items():
                self.append(f'{key}/{subkey}', subval)
        else: # Append to an array
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.with_suffix('.h5').exists():
                path.with_suffix('.h5').unlink()
            self._get_entry(key).append(val)

    @property
    def cmd_status(self):
        try:
            spec = yaml.safe_load((self.path/'_cmd-spec.yaml').read_text())
            status = yaml.safe_load((self.path/'_cmd-status.yaml').read_text())
            return status if spec == self.cmd_spec else 'unbegun'
        except FileNotFoundError:
            return 'unbegun'

    @property
    def cmd_spec(self):
        try:
            return yaml.safe_load(
                (self.path/'_cmd-spec.yaml')
                .read_text())
        except FileNotFoundError:
            return None

    def keys(self):
        yield from self

    def values(self):
        for k in self.keys():
            yield self[k]

    def items(self):
        yield from zip(
            self.keys(),
            self.values())

    def flat_keys(self):
        for p in self.path.glob('**'):
            p_rel = p.relative_to(self.path)
            if not any(part.startswith('_') for part in p_rel.parts):
                if p_rel.suffix == '.h5': yield str(p_rel)[:-3]
                else: yield str(p_rel)

    def flat_values(self):
        for k in self.flat_keys():
            yield self[k]

    def flat_items(self):
        for k in self.flat_keys():
            yield k, self[k]

################################################################################
# Command-line interface
################################################################################

def _doc(obj):
    return cleandoc(obj.__doc__ or '')

def _ind_a(text):
    return indent(text, '  ', lambda _: True)

def _ind_b(text):
    return indent(text, '│ ', lambda _: True)

def _cmd_desc(name, cmd):
    json_schema = cmd.conf_schema['properties']
    schema_str = yaml.safe_dump(json_schema, allow_unicode=True)
    conf_desc = 'conf-schema:\n' + _ind_b(schema_str)
    return name + ':\n' + _ind_b(_doc(cmd) + '\n' + conf_desc)

def _cmd_dict_desc():
    return 'commands:\n' + _ind_a('\n'.join(
        _cmd_desc(name, val)
        for name, val in _flat_scope().items()
        if isinstance(val, Command)))

def cli():
    'Run a command-line interface derived from the current scope stack.'
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        epilog=_cmd_dict_desc())
    parser.add_argument('cmd_spec', help=(
        'the command specification, in YAML format, or '
        'the path to a YAML configuration file'))
    args = parser.parse_args()
    cmd_spec = yaml.safe_load(args.cmd_spec)

    if isinstance(cmd_spec, str):
        with open(cmd_spec) as f:
            cmd_spec = yaml.safe_load(f)

    cmds = valfilter(lambda c: isinstance(c, Command), _flat_scope())
    if len(cmds) == 1 and 'type' not in cmd_spec:
        cmd_spec['type'] = [*cmds][0]

    schema = _command_schema()
    jsonschema.validate(cmd_spec, schema)
    create(cmd_spec)()

################################################################################
# Web API
################################################################################

_web_dtypes = dict(
    bool='uint8',
    uint8='uint8',
    uint16='uint16',
    uint32='uint32',
    uint64='uint32',
    int8='int8',
    int16='int16',
    int32='int32',
    int64='int32',
    float16='float32',
    float32='float32',
    float64='float64',
    float96='float64',
    float128='float64')

def _response(obj):
    return bottle.HTTPResponse(
        headers={'Content-Type': 'application/msgpack',
                 'Access-Control-Allow-Origin': '*'},
        body=io.BytesIO(cbor2.dumps(obj)))

def serve(rec_path, port=3000):
    '''
    Start a server providing access to the records in a directory.
    '''
    root = Record(rec_path)
    app = bottle.default_app()

    @app.route('/<:re:.*>', method='OPTIONS')
    def _(*_):
        return bottle.HTTPResponse(headers={
            'Allow': 'OPTIONS, GET, HEAD',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*'})

    @app.get('/_entry-names')
    @app.get('/<rec_id:path>/_entry-names')
    def _(rec_id=''):
        if not (root.path/rec_id).is_dir():
            raise bottle.HTTPError(404)
        return _response(list(root[rec_id]))

    @app.get('/_cmd-info')
    @app.get('/<rec_id:path>/_cmd-info')
    def _(rec_id=''):
        if not (root.path/rec_id).is_dir():
            raise bottle.HTTPError(404)
        spec = root[rec_id].cmd_spec
        status = root[rec_id].cmd_status
        return _response(
            None if spec is None else
            {'type': spec['type'],
             'desc': _doc(resolve(spec['type'])),
             'conf': {k: v for k, v in spec.items() if k != 'type'},
             'status': status})

    @app.get('/<ent_id:path>')
    def _(ent_id):
        if not (root.path/ent_id).is_file():
            raise bottle.HTTPError(404)
        elif bottle.request.query.get('mode', None) == 'file':
            return bottle.static_file(ent_id, root=root.path)
        else:
            ent = root[ent_id]
            if ent.dtype.kind in ['U', 'S']:
                return _response(ent.astype('U').tolist())
            else:
                ent = ent.astype(_web_dtypes[ent.dtype.name])
                return _response({'$type': 'array',
                                  'data': ent.data.tobytes(),
                                  'dtype': ent.dtype.name,
                                  'shape': ent.shape})

    app.run(host='localhost', port=port)
