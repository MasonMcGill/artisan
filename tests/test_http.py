import json
from base64 import b64encode
from os import listdir
from pathlib import Path
from typing import Optional
from typing_extensions import Protocol

import cbor2
from webtest import TestApp as Client

from artisan import (
    API, Artifact, Context, Namespace,
    get_spec_schema, get_spec_dict_schema,
    get_spec_list_schema, using_context)



#-- Sample-API-generation ------------------------------------------------------

def sample_context(root: Path) -> Context:
    class Branch(Artifact):
        a: bool
        b: int

    class Leaf1(Branch):
        class Spec(Protocol):
            arg: int

        def __init__(self, spec: Spec) -> None:
            self.a = bool(spec.arg)
            self.b = int(spec.arg)

    class Leaf2(Branch):
        class Spec(Protocol):
            arg: float

        def __init__(self, spec: Spec) -> None:
            self.a = bool(spec.arg - 1)
            self.b = int(spec.arg - 1)

    context = Context(
        root = root,
        scope = dict(
            Branch = Branch,
            Leaf1 = Leaf1,
            Leaf2 = Leaf2))

    with using_context(context):
        Artifact(Namespace(_path_='@/x', type='Leaf1', arg=0))
        Artifact(Namespace(_path_='@/y', type='Leaf2', arg=1.2))

    return context



#-- Tests ----------------------------------------------------------------------

def test_schema_requests(tmp_path: Path) -> None:
    '''
    Test requests in the form `GET /schema/{schema-name}`.
    '''
    with using_context(sample_context(tmp_path)):
        get = Client(API()).get
        assert get('/schemas/spec').json == get_spec_schema()
        assert get('/schemas/spec-list').json == get_spec_list_schema()
        assert get('/schemas/spec-dict').json == get_spec_dict_schema()


def test_artifact_get_requests(tmp_path: Path) -> None:
    '''
    Test requests in the form `GET /artifacts{/path*}`.
    '''
    with using_context(sample_context(tmp_path)):
        get = Client(API()).get
        x_meta = json.loads((tmp_path / 'x/_meta_.json').read_text())
        y_meta = json.loads((tmp_path / 'y/_meta_.json').read_text())
        for _ in range(3): # To test caching
            root_res = get('/artifacts').body
            x_res = get('/artifacts/x').body
            y_res = get('/artifacts/y').body
            x_a_res = get('/artifacts/x/a').body
            x_b_res = get('/artifacts/x/b').body
            assert cbor2.loads(root_res) == dict(_meta_=None, x=None, y=None)
            assert cbor2.loads(x_res) == dict(_meta_=x_meta, a=None, b=None)
            assert cbor2.loads(y_res) == dict(_meta_=y_meta, a=None, b=None)
            assert x_a_res == (tmp_path / 'x/a.cbor').read_bytes()
            assert x_b_res == (tmp_path / 'x/b.cbor').read_bytes()


def test_artifact_post_requests(tmp_path: Path) -> None:
    '''
    Test requests in the form `POST /artifacts{/path*}`.
    '''
    with using_context(sample_context(tmp_path)):
        post = Client(API()).post

        z_spec = cbor2.dumps(dict(type='Leaf1', arg=2, _path_='@/z'))
        z_res = post('/artifacts', z_spec, status=201)
        assert z_res.location == '/artifacts/z'
        assert (Artifact @ '@/z')._meta_.spec.type == 'Leaf1'
        assert (Artifact @ '@/z')._meta_.events[-1].type == 'Success'

        anon_spec = cbor2.dumps(dict(type='Leaf2', arg=3.0))
        anon_res = post('/artifacts', anon_spec, status=201)
        anon_path = anon_res.location.replace('/artifacts', '@/')
        anon_meta = (Artifact @ anon_path)._meta_
        assert anon_meta.spec.type == 'Leaf2'
        assert anon_meta.events[-1].type == 'Success'

        post('/artifacts', z_spec, status=201)
        post('/artifacts', anon_spec, status=201)


def test_artifact_delete_requests(tmp_path: Path) -> None:
    '''
    Test requests in the form `DELETE /artifacts{/path*}`.
    '''
    with using_context(sample_context(tmp_path)):
        delete = Client(API()).delete
        delete('/artifacts/x'); assert listdir(tmp_path) == ['y']
        delete('/artifacts/y'); assert listdir(tmp_path) == []


def test_permissions(tmp_path: Path) -> None:
    '''
    Test API permissions.
    '''
    permissions = {
        'alice': ('read'),
        'bob': ('read', 'write'),
        'carl': ('read', 'write', 'delete')}
    headers = {
        pw: {'Authorization': 'Basic ' + b64encode(f':{pw}'.encode()).decode()}
        for pw in permissions}

    with using_context(sample_context(tmp_path)):
        client = Client(API(permissions=permissions))
        get, post, delete = client.get, client.post, client.delete

        get('/artifacts/x', headers={}, status=401)
        get('/artifacts/x', headers=headers['alice'], status=200)
        get('/artifacts/x', headers=headers['bob'], status=200)
        get('/artifacts/x', headers=headers['carl'], status=200)

        z0_spec = cbor2.dumps(dict(type='Leaf1', arg=2, _path_='@/z0'))
        z1_spec = cbor2.dumps(dict(type='Leaf1', arg=3, _path_='@/z1'))
        post('/artifacts/x', z0_spec, headers={}, status=401)
        post('/artifacts/x', z0_spec, headers=headers['alice'], status=401)
        post('/artifacts/x', z0_spec, headers=headers['bob'], status=201)
        post('/artifacts/x', z1_spec, headers=headers['carl'], status=201)

        delete('/artifacts/x', headers={}, status=401)
        delete('/artifacts/x', headers=headers['alice'], status=401)
        delete('/artifacts/x', headers=headers['bob'], status=401)
        delete('/artifacts/x', headers=headers['carl'], status=204)

