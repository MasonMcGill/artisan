'''
A small, in-development experiment-logging library designed to take advantage of
YAML, JSON-Schema, HDF5-SWMR, and web-based visualization software.
'''
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from contextlib import contextmanager
from datetime import datetime
import importlib
from inspect import getdoc
import io
from itertools import count
import json
from pathlib import Path
import re
import shutil
from textwrap import indent
import threading
from time import sleep
from typing import List

import bottle
import cbor2
import h5py as h5
import jsonschema
import numpy as np
from ruamel import yaml
from toolz import dissoc, valfilter, valmap

__all__ = [
    'Namespace', 'Configuration', 'Configurable',
    'using_conf', 'get_conf',
    'resolve', 'identify', 'create', 'describe',
    'Command', 'Record', 'require',
     'cli', 'serve'
 ]

#------------------------------------------------------------------------------
# Attribute-access-supporting dictionaries

class Namespace(dict):
    'An `dict` that supports accessing items as attributes'
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class Configuration:
    '''
    A read-only namespace that supports accessing items as attributes and
    tracks item access

    To be used in an API update allowing configurations to be passed
    without being converted into keyword arguments

    TODO:
    - Change the signature of `Configurable.{__new__,__init__}`.
    - Change `_run` and `require` to only care about accessed fields.
    '''
    def __init__(self, *args, **kwargs):
        self._entries = dict(*args, **kwargs)
        self._accessed_fields = set()

    def __getitem__(self, key):
        self._accessed_fields.add(key)
        return self._entries.__getitem__(key)

    def __getattr__(self, key):
        return self.__getitem__(key)


def _dictify(obj):
    if isinstance(obj, dict):
        return valmap(_dictify, obj)
    elif isinstance(obj, list):
        return list(map(_dictify, obj))
    else:
        return obj


def _namespacify(obj):
    if isinstance(obj, dict):
        return Namespace(valmap(_namespacify, obj))
    elif isinstance(obj, list):
        return list(map(_namespacify, obj))
    else:
        return obj


def _confify(obj):
    if isinstance(obj, dict):
        return Configuration(valmap(_confify, obj))
    elif isinstance(obj, list):
        return list(map(_confify, obj))
    else:
        return obj

#------------------------------------------------------------------------------
# Thread-local configuration

class _ConfStack(threading.local):
    def __init__(self):
        self.value = [Namespace(record_root='.', scope={})]


_conf_stack = _ConfStack()


@contextmanager
def using_conf(*, record_root='.', scope={}):
    conf = Namespace(record_root=record_root, scope=scope)
    _conf_stack.value.append(conf); yield
    _conf_stack.value.remove(conf)


def get_conf():
    return _conf_stack.value[-1]

#------------------------------------------------------------------------------
# Serialization/deserialization

def _id(obj):
    return obj.__module__+'$'+obj.__qualname__


def resolve(sym):
    'Search the current scope for an object.'
    if sym in get_conf().scope:
        return get_conf().scope[sym]
    try:
        mod_name, type_name = sym.split('$')
        mod = importlib.import_module(mod_name)
        return getattr(mod, type_name)
    except:
        raise KeyError(f'"{sym}" is not present in the current scope')


def identify(obj):
    'Search the current scope for an object\'s name.'
    for sym, val in get_conf().scope.items():
        if val is obj: return sym
    return _id(obj)


def create(spec):
    '''
    Instantiate a configurable object from a specification.

    A specification is a `dict` with

      - a "type" field; the innermost `Scope` symbol corresponding to the
        object's type, or "{module_name}${type_name}", if none exist.
      - other fields corresponding to the object's configuration properties.
    '''
    return resolve(spec['type'])(**dissoc(dict(spec), 'type'))


def describe(obj):
    '''
    Generate the specification for a configurable object.

    A specification is a `dict` with

      - a "type" field; the innermost `Scope` symbol corresponding to the
        object's type, or "{module_name}${type_name}", if none exist.
      - other fields corresponding to the object's configuration properties.
    '''
    return Namespace(type=identify(type(obj)), **getattr(obj, 'conf', {}))

#------------------------------------------------------------------------------
# JSON-Schema generation

def _schema_from_type(t):
    if t == bool:
        return dict(type='boolean')
    elif t == int:
        return dict(type='integer')
    elif t == float:
        return dict(type='number')
    elif t == str:
        return dict(type='string')
    elif type(t) == type(List) and t.__base__ == List:
        return dict(type='array', items=_schema_from_type(t.__args__[0]))
    elif issubclass(t, Configurable):
        return {'$ref': '#/definitions/'+identify(t)}
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


def _spec_schema(type_):
    # Concrete types
    if len(type_.__subclasses__()) == 0:
        prop_schemas = {
            k: _schema_from_prop_spec(v)
            for k, v in vars(type_.Conf).items()
            if not k.startswith('__')
        }
        return dict(
            type='object',
            properties=prop_schemas,
            required=[
                prop_name
                for prop_name, schema in prop_schemas.items()
                if 'default' not in schema
            ]
        )
    # Abstract types
    else:
        return {'oneOf': [
            {'allOf': [
                {'required': ['type'],
                 'properties': {'type': {'const': identify(t)}}},
                {'$ref': '#/definitions/'+identify(t)}
            ]}
            for t in type_.__subclasses__()
            if len(t.__subclasses__()) == 0
        ]}


def _collect_definitions(defs, schema):
    if isinstance(schema, dict) and '$ref' in schema:
        sym = schema['$ref'][len('#/definitions/'):]
        if sym not in defs:
            defs[sym] = _spec_schema(resolve(sym))
            _collect_definitions(defs, defs[sym])
    elif isinstance(schema, dict):
        for subschema in schema.values():
            _collect_definitions(defs, subschema)
    elif isinstance(schema, list):
        for subschema in schema:
            _collect_definitions(defs, subschema)


def _with_definitions(schema):
    defs = {}
    _collect_definitions(defs, schema)
    return dict(definitions=defs, **schema)


def _command_schema():
    defs = {}
    options = [
        {'allOf': [
            {'required': ['type'],
             'properties': {'type': {'const': sym}}},
            {'$ref': '#/definitions/'+sym}
        ]}
        for sym, val in get_conf().scope.items()
        if issubclass(val, Command) and len(val.__subclasses__()) == 0
    ]
    _collect_definitions(defs, options)
    return dict(definitions=defs, oneOf=options)

#------------------------------------------------------------------------------
# Configurable objects

class Configurable:
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

    def __new__(cls, *args, **conf):
        subclass = resolve(conf['type']) if 'type' in conf else cls
        return super().__new__(subclass)

    def __init__(self, *args, **conf):
        self.conf = _namespacify(dissoc(conf, 'type'))

    @classmethod
    def conf_fields(cls):
        return [k for k in vars(cls.Conf) if not k.startswith('__')]

#------------------------------------------------------------------------------
# Commands

class Command(Configurable):
    '''
    An operation that creates a `Record`.

    To specify the output path, define an `output_path` property or define
    `output_path` as a class-level format string to be resolved with the
    command configuration.

    Override `run` to do something useful.
    '''
    def run(self, output):
        'Override this, writing the output of the command to `output`.'


def _find_record(cmd):
    if getattr(cmd, 'volatile', False):
        return None

    conf_str = json.dumps(cmd.conf, sort_keys=True)
    rec_paths = Path(get_conf().record_root).glob(identify(type(cmd))+'_*')

    for rec in map(Record, rec_paths):
        if json.dumps(rec.cmd_info.conf, sort_keys=True) == conf_str:
            return rec
    return None


def _run(cmd):
    '''
    Execute a command.

    Performs the following operations:

      - Creates an output record.
      - Writes metadata to `{output_path}/_cmd-info.yaml`.
      - Calls `cmd.run`.
    '''
    type_ = identify(type(cmd))
    if 'name' in cmd.conf:
        dst = Path(f'{get_conf().record_root}/{type_}_{cmd.conf.name}')
        shutil.rmtree(dst, ignore_errors=True)
        dst.mkdir(parents=True)
    else:
        for i in count():
            date = datetime.now().strftime(r'%Y-%m-%d')
            dst = Path(f'{get_conf().record_root}/{type_}_{date}-{i:04x}')
            try:
                dst.mkdir(parents=True)
                break
            except FileExistsError:
                pass

    desc = re.sub(r'(?<!\n)(\n)(?!\n)', ' ', getdoc(cmd) or '')
    static_info = dict(
        type=identify(type(cmd)),
        desc=desc,
        conf=_dictify(cmd.conf)
    )
    write_info = lambda info: (
        (dst / '_cmd-info.yaml').write_text(
            yaml.round_trip_dump(info, allow_unicode=True)
        )
    )
    write_info({**static_info, 'status': 'running'})

    try:
        rec = Record(dst)
        cmd.run(rec)
        write_info({**static_info, 'status': 'done'})
        return rec
    except BaseException as e:
        write_info({**static_info, 'status': 'stopped'})
        raise e


def require(cmd):
    'Ensure that a command has started and block until it is finished.'
    if not isinstance(cmd, Command):
        cmd = create(cmd)
    rec = _find_record(cmd)
    if rec is None:
        return _run(cmd)
    while rec.cmd_info.status == 'running':
        sleep(0.01)
    if rec.cmd_info.status == 'stopped':
        shutil.rmtree(rec.path)
        return _run(cmd)
    elif rec.cmd_info.status == 'done':
        return rec

#------------------------------------------------------------------------------
# Command records

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
                name='data',
                shape=None,
                maxshape=(None, *val.shape[1:]),
                dtype=val.dtype,
                data=np.empty((0, *val.shape[1:]), val.dtype),
                chunks=(
                    int(np.ceil(2**12 / np.prod(val.shape[1:]))),
                    *val.shape[1:]
                )
            )
            f.swmr_mode = True
        self.dset.resize(self.dset.len() + len(val), 0)
        self.dset[-len(val):] = val
        self.dset.flush()


class Record:
    '''
    A record of the execution of a `Command`.

    A `Record` is an array-friendly view of a directory. It also supports
    reading command metadata (stored in "_cmd-info.yaml").

    TODO: Document this more.
    '''
    def __init__(self, path):
        self.__dict__['path'] = Path(path)
        self.__dict__['_cache'] = {}

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

    def __len__(self):
        return len([
            p for p in self.path.iterdir()
            if not p.name.startswith('_')
        ])

    def __contains__(self, key):
        path = self.path/key
        return path.exists or (
            path.suffix == '' and
            path.with_suffix('.h5').is_file())

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
        elif path.with_suffix('.h5').is_file(): # Return an array
            return self._get_entry(key).get()
        elif path.is_file(): # Return a file path
            return path
        else: # Return a subrecord
            return self._get_record(key)

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

    __getattr__ = __getitem__
    __setattr__ = __setitem__

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
            self._get_entry(key).append(val)

    @property
    def cmd_info(self):
        # TODO: Implement caching
        return _namespacify(yaml.safe_load(
            (self.path/'_cmd-info.yaml').read_text()
        ))

    def keys(self):
        yield from self

    def values(self):
        for k in self.keys():
            yield self[k]

    def items(self):
        yield from zip(self.keys(), self.values())

#------------------------------------------------------------------------------
# Command-line interface

def _ind_a(text):
    return indent(text, '  ', lambda _: True)


def _ind_b(text):
    return indent(text, '│ ', lambda _: True)


def _cmd_desc(name, cmd):
    json_schema = cmd.conf_schema['properties']
    schema_str = yaml.safe_dump(json_schema, allow_unicode=True)
    conf_desc = 'conf-schema:\n' + _ind_b(schema_str)
    cmd_desc = getdoc(cmd) or ''
    return name + ':\n' + _ind_b(cmd_desc + '\n' + conf_desc)


def _cmd_dict_desc():
    return 'commands:\n' + _ind_a('\n'.join(
        _cmd_desc(name, val)
        for name, val in get_conf().scope.items()
        if isinstance(val, Command)
    ))


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

    cmds = valfilter(lambda c: isinstance(c, Command), get_conf().scope)
    if len(cmds) == 1 and 'type' not in cmd_spec:
        cmd_spec['type'] = [*cmds][0]

    jsonschema.validate(cmd_spec, _command_schema())
    require(create(cmd_spec))

#------------------------------------------------------------------------------
# Web API

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
    float128='float64'
)


def _response(type_, content):
    return bottle.HTTPResponse(
        headers={'Content-Type': 'application/msgpack',
                 'Access-Control-Allow-Origin': '*'},
        body=io.BytesIO(cbor2.dumps(dict(type=type_, content=content))))


def _encode_entry(ent):
    if ent.dtype.kind in ['U', 'S']:
        return _response('plain-object', ent.astype('U').tolist())
    else:
        ent = ent.astype(_web_dtypes[ent.dtype.name])
        return _response('array', dict(
            shape=ent.shape,
            dtype=ent.dtype.name,
            data=ent.data.tobytes()
        ))


def serve(port=3000):
    '''
    Start a server providing access to the records in a directory.
    '''
    root = Record(get_conf().record_root)
    app = bottle.default_app()

    @app.route('/<:re:.*>', method='OPTIONS')
    def _(*_):
        return bottle.HTTPResponse(headers={
            'Allow': 'OPTIONS, GET, HEAD',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*'
        })

    @app.get('/_entry-names')
    @app.get('/<rec_id:path>/_entry-names')
    def _(rec_id=''):
        if not (root.path/rec_id).is_dir():
            raise bottle.HTTPError(404)
        return _response('plain-object', list(root[rec_id]))

    @app.get('/<rec_id:path>/_cmd-info')
    def _(rec_id):
        if (root.path/rec_id).is_dir():
            return _response('plain-object', root[rec_id].cmd_info)
        else:
            raise bottle.HTTPError(404)

    @app.get('/<ent_id:path>')
    def _(ent_id):
        if Path(ent_id).suffix != '':
            return bottle.static_file(ent_id, root=root.path)
        elif ent_id in root:
            t_last = float(bottle.request.query.get('t_last', 0)) / 1000
            if (root.path/f'{ent_id}.h5').stat().st_mtime <= t_last:
                return _response('cached-value', None)
            else:
                return _encode_entry(root[ent_id])
        else:
            raise bottle.HTTPError(404)

    app.run(host='localhost', port=port)
