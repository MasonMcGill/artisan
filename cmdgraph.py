'''
A small, in-development experiment-logging library designed to take advantage of
YAML, JSON-Schema, HDF5-SWMR, and web-based visualization software.
'''
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import importlib
import io
import json
from pathlib import Path
import shutil
from textwrap import dedent, indent
from time import sleep
from types import SimpleNamespace as Ns
from typing import GenericMeta, List

import bottle
import h5py as h5
import imageio
import jsonschema
import numpy as np
from ruamel import yaml

__all__ = [
    'Configurable', 'Namespace', 'resolve', 'identify', 'create', 'describe',
    'Command', 'Record', 'cli', 'require', 'serve']

################################################################################
# [Supporting definitions] Namespace <-> dict conversion
################################################################################

def _namespacify(obj):
    if isinstance(obj, dict):
        return Ns(**{k: _namespacify(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return list(map(_namespacify, obj))
    else:
        return obj

def _dictify(obj):
    if isinstance(obj, Ns):
        return {k: _dictify(v) for k, v in vars(obj).items()}
    elif isinstance(obj, list):
        return list(map(_dictify, obj))
    else:
        return obj

################################################################################
# [Supporting definitions] JSON-Schema generation
################################################################################

class _Undef: pass
_undef = _Undef()

def _parse_prop_desc(cm):
    if isinstance(cm, tuple):
        type_, default, doc = 3 * [_undef]
        for e in cm:
            if isinstance(e, type): type_ = e
            if isinstance(e, list): default: e[0]
            if isinstance(e, str): doc = e
        return Ns(type=type_, default=default, doc=doc)
    else:
        return _parse_prop_desc((cm,))

def _to_json_schema(conf_type):
    def is_list_type(t):
        return isinstance(t, GenericMeta) and t.__base__ == List
    def convert_type(t):
        if t == bool: return {'type': 'boolean'}
        elif t == int: return {'type': 'integer'}
        elif t == float: return {'type': 'number'}
        elif t == str: return {'type': 'string'}
        elif is_list_type(t): return {
            'items': convert_type(t.__args__[0]),
            'type': 'array'}
        else: return {}
    def convert_default(d):
        return {} if d is _undef else {'default': _dictify(d)}
    def convert_doc(d):
        return {} if d is _undef else {'description': d}
    prop_descs = {
        k: _parse_prop_desc(v)
        for k, v in vars(conf_type).items()
        if not k.startswith('__')}
    return {} if len(prop_descs.items()) == 0 else {
        'type': 'object',
        'properties': {
            k: {**convert_type(v.type),
                **convert_default(v.default),
                **convert_doc(v.doc)}
            for k, v in prop_descs.items()},
        'required': list(prop_descs.keys())}

################################################################################
# Serialization/deserialization
################################################################################

_namespaces = []

class Namespace(dict):
    '''
    A `dict` context that makes its entries available to `resolve` when active.

    If multiple namespaces are active, the innermost scope (the one entered
    most recently) takes precedence.
    '''
    def __enter__(self):
        _namespaces.append(self)

    def __exit__(self, *_):
        _namespaces.remove(self)

def resolve(sym):
    '''
    Search the namespace stack and module path for an object.
    '''
    for ns in reversed(_namespaces):
        if sym in ns:
            return ns[sym]
    try:
        mod_name, type_name = sym.split('/')
        mod = importlib.import_module(mod_name)
        return getattr(mod, type_name)
    except:
        raise KeyError(
            f'"{sym}" is not present in the '
            'CommandGraph namespace stack.')

def identify(obj):
    '''
    Search the namespace stack and module path for an object's name.
    '''
    for ns in reversed(_namespaces):
        for sym, val in ns.items():
            if val is obj:
                return sym
    mod_name = obj.__module__
    obj_name = obj.__qualname__
    return f'{mod_name}/{obj_name}'

def create(spec):
    '''
    Instantiate a configurable object from a specification.

    A specification is a namespace with

      - a `type` field; the innermost `Namespace` symbol corresponding to the
        object's type, or "{module_name}/{type_name}", if none exist.
      - other fields corresponding to object's configuration properties (to be
        passed into the constructor).
    '''
    return resolve(spec['type'])(**{
        k: v for k, v in spec.items()
        if k != 'type'})

def describe(obj):
    '''
    Generate a specification from a configurable object.

    A specification is a namespace with

      - a `type` field; the innermost `Namespace` symbol corresponding to the
        object's type, or "{module_name}/{type_name}", if none exist.
      - other fields corresponding to object's configuration properties (to be
        passed into the constructor).
    '''
    return Ns(type=identify(type(obj)), **vars(obj.conf))

################################################################################
# Configurable objects
################################################################################

class Configurable:
    '''
    An object that can be constructed from JSON-object-like structures.

    A JSON-object-like structure is a string-keyed `dict` composed of
    arbitrarily nested `bool`, `int`, `float`, `str`, `NoneType`, `list`, and
    string-keyed `dict` instances.

    A `Configurable`'s configuration should be passed its the constructor as a
    set of keyword arguments.
    '''
    class Conf:
        '''
        Override this to specify a configuration schema.

        Members of `Conf` are interpreted in the following way:

        - The member's name corresponds to the expected property's name.
        - A `type` value specify the property's expected type.
        - A single-element `list` value specifies the property's default value.
        - A `str` value specifies the property's docstring.
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
        if (hasattr(type(self), 'output_path') and
            isinstance(type(self).output_path, str)):
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
            return status if spec == _dictify(describe(self)) else 'unbegun'
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
        spec_dict = _dictify(describe(self))
        spec_str = yaml.safe_dump(spec_dict, allow_unicode=True)
        (dst/'_cmd-spec.yaml').write_text(spec_str)
        (dst/'_cmd-status.yaml').write_text('running')
        self.run()
        (dst/'_cmd-status.yaml').write_text('done')

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

class _ImageEntry:
    def __init__(self, path):
        self.path = path

    def get(self):
        return imageio.imread(self.path)

    def put(self, val):
        imageio.imwrite(self.path, val)

    def append(self, val):
        self.put(np.concatenate([self.get(), val], 0))

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
        entry_types = {
            '.bmp': _ImageEntry,
            '.png': _ImageEntry,
            '.jpg': _ImageEntry,
            '.jpeg': _ImageEntry,
            '.h5': _HDF5Entry}
        if key not in self._cache:
            type_ = entry_types[Path(key).suffix]
            self._cache[key] = type_(self.path/key)
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
                yield p.name

    def __getitem__(self, key):
        if '/' in key:
            head, *tail = Path(key).parts
            return self._get_record(head)['/'.join(tail)]
        elif (self.path/key).is_file():
            return self._get_entry(key).get()
        elif (self.path/key).is_dir():
            return self._get_record(key)
        else:
            raise KeyError()

    def __setitem__(self, key, val):
        if isinstance(val, (dict, Record)):
            for subkey, subval in val.items():
                self[f'{key}/{subkey}'] = subval
        elif '/' in key:
            head, *tail = Path(key).parts
            self._get_record(head)['/'.join(tail)] = val
        else:
            self.path.mkdir(parents=True, exist_ok=True)
            self._get_entry(key).put(val)

    def __delitem__(self, key):
        if '/' in key:
            head, *tail = Path(key).parts
            rec = self._get_record(head)
            del rec['/'.join(tail)]
        elif (self.path/key).is_file():
            (self.path/key).unlink()
        elif (self.path/key).is_dir():
            rec = self._get_record(key)
            for k in rec: del rec[k]
            shutil.rmtree(self.path/key, True)
        else:
            raise KeyError()
        self._forget(key)
        if len([*self.path.iterdir()]) == 0:
            self.path.rmdir()

    def append(self, key, val):
        if isinstance(val, (dict, Record)):
            for subkey, subval in val.items():
                self.append(f'{key}/{subkey}', subval)
        elif '/' in key:
            head, *tail = Path(key).parts
            self._get_record(head).append('/'.join(tail), val)
        else:
            self.path.mkdir(parents=True, exist_ok=True)
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
            if any(part.startswith('_')
                   for part in p_rel.parts):
                yield str(p_rel)

    def flat_values(self):
        for k in self.flat_keys():
            yield self[k]

    def flat_items(self):
        yield from zip(
            self.flat_keys(),
            self.flat_values())

################################################################################
# Command execution
################################################################################

def _known_cmds():
    return {
        k: v
        for ns in _namespaces
        for k, v in ns.items()
        if issubclass(v, Command)}

def _ind_a(text):
    return indent(text, '  ', lambda _: True)

def _ind_b(text):
    return indent(text, '│ ', lambda _: True)

def _cmd_desc(name, cmd):
    json_schema = _to_json_schema(cmd.Conf)
    schema_str = yaml.safe_dump(json_schema, allow_unicode=True)
    conf_desc = 'conf-schema:\n' + _ind_b(schema_str)
    return name + ':\n' + _ind_b(dedent(cmd.__doc__[1:]) + '\n' + conf_desc)

def _cmd_dict_desc():
    return 'commands:\n' + _ind_a('\n'.join(
        _cmd_desc(name, cmd) for name, cmd
        in _known_cmds().items()))

def cli():
    '''
    Run a command-line interface.

    All commands in the current scope (defined by entering `Namespace`
    contexts) are available.
    '''
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        epilog=_cmd_dict_desc())
    parser.add_argument(
        'cmd', metavar='cmd', choices=_known_cmds().keys(), help=(
            'the command to execute'))
    parser.add_argument(
        'conf', nargs='?', default=r'{}', help=(
            'the command configuration, in YAML format, or '
            'the path to a YAML configuration file'))
    args = parser.parse_args()
    cmd = resolve(args.cmd)
    conf = yaml.safe_load(args.conf)
    if isinstance(conf, str):
        with open(conf) as f:
            conf = yaml.safe_load(f)
    schema = _to_json_schema(cmd.Conf)
    jsonschema.validate(conf, schema)
    cmd(**conf)()

def require(cmd):
    '''
    Ensure that a command has started and block until it is finished.
    '''
    if isinstance(cmd, str): cmd = create(cmd)
    if cmd.status in {'unbegun', 'stopped'}: cmd()
    while cmd.status == 'running': sleep(0.01)
    return Record(cmd.output_path)

################################################################################
# Web API
################################################################################

def serve(rec_path, port=3000):
    '''
    Start a server providing access to the records in a directory.
    '''
    root = Record(rec_path)
    app = bottle.default_app()

    def json_res(obj):
        return bottle.HTTPResponse(
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'},
            body=json.dumps(obj))

    def buffer_res(obj):
        return bottle.HTTPResponse(
            headers={
                'Content-Type': 'application/octet-stream',
                'Access-Control-Allow-Origin': '*'},
            body=io.BytesIO(obj))

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
        return json_res(list(root[rec_id]))

    @app.get('/_cmd-info')
    @app.get('/<rec_id:path>/_cmd-info')
    def _(rec_id=''):
        if not (root.path/rec_id).is_dir():
            raise bottle.HTTPError(404)
        spec = root[rec_id].cmd_spec
        status = root[rec_id].cmd_status
        return json_res(
            None if spec is None else
            {'type': spec['type'],
             'desc': dedent(create(spec).__doc__[1:]),
             'conf': {k: v for k, v in spec.items() if k != 'type'},
             'status': status})

    @app.get('/<ent_id:path>')
    def _(ent_id):
        if not (root.path/ent_id).is_file():
            raise bottle.HTTPError(404)
        elif bottle.request.query.get('mode', None) == 'file':
            return bottle.static_file(ent_id, root=root.path)
        else:
            dtypes = {
                'uint8': 0, 'uint16': 1, 'uint32': 2,
                'int8': 3, 'int16': 4, 'int32': 5,
                'float32': 6, 'float64': 7}
            ent = root[ent_id]
            msg = bytearray(ent.nbytes + 40)
            msg[0:4] = np.uint32(dtypes[ent.dtype.name]).data
            msg[4:8] = np.uint32(ent.ndim).data
            msg[8:8+4*len(ent.shape)] = (
                np.uint32(ent.shape).data)
            msg[40:] = ent.data
            return buffer_res(msg)

    app.run(host='localhost', port=port)
