import io
from pathlib import Path
import re
from typing import Dict, Optional as Opt

import bottle
import cbor2
import h5py as h5
from ruamel import yaml

from ._global_conf import get_conf

__all__ = ['serve']

#------------------------------------------------------------------------------
# Web API

def serve(port: int = 3000, root_dir: Opt[str] = None) -> None:
    '''
    Start a server providing access to the records in a directory.
    '''
    root_dir = Path(root_dir or get_conf().root_dir)
    app = bottle.default_app()

    @app.route('/<:re:.*>', method='OPTIONS')
    def _(*_):
        return bottle.HTTPResponse(headers={
            'Allow': 'OPTIONS, GET, HEAD',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*'
        })

    @app.get('/_entry-names') # type: ignore
    @app.get('/<entry_name:path>/_entry-names')
    def _(entry_name=''):
        path = root_dir / entry_name
        if path.is_file(): raise bottle.HTTPError(404)
        return _response('plain-object', sorted([
            re.sub(r'\.h5$', '', p.name) + ('/' if p.is_dir() else '')
            for p in path.glob('[!_]*')
        ]))

    @app.get('/_meta') # type: ignore
    @app.get('/<entry_name:path>/_meta')
    def _(entry_name=''):
        return _response(**_read_meta(root_dir, entry_name))

    @app.get('/<entry_name:path>') # type: ignore
    def _(entry_name):
        t_last = float(bottle.request.query.get('t_last', 0)) / 1000
        entry = _read(root_dir, entry_name, t_last)
        return (
            bottle.static_file(entry['content'], root=root_dir)
            if entry['type'] == 'file'
            else _response(**entry)
        )

    app.run(host='localhost', port=port)

#------------------------------------------------------------------------------
# I/O

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


def _read(root: Path, key: str, t_last: float) -> Dict[str, object]:
    if Path(f'{root}/{key}.h5').is_file():         # Array
        return _read_array(root, key, t_last)
    elif (root / key).is_file():                   # Non-array file
        return dict(type='file', content=key)
    else:                                          # Artifact
        return _read_artifact(root, key, t_last)


def _read_array(root: Path, key: str, t_last: float) -> Dict[str, object]:
    if Path(f'{root}/{key}.h5').stat().st_mtime <= t_last:
        return dict(type='cached-value', content=None)

    f = h5.File(f'{root}/{key}.h5', 'r', libver='latest', swmr=True)
    a = f['data'][:]

    if a.dtype.kind in ['U', 'S']:
        return dict(
            type='string-array',
            content=a.astype('U').tolist()
        )

    else:
        a = a.astype(_web_dtypes[a.dtype.name])
        return dict(
            type='numeric-array',
            content=dict(
                shape=a.shape,
                dtype=a.dtype.name,
                data=a.data.tobytes()
            )
        )


def _read_artifact(root: Path, key: str, t_last: float) -> Dict[str, object]:
    return dict(
        type='artifact',
        content=dict(
            _meta=_read_meta(root, key),
            **{
                p.name: _read(root, str(p.relative_to(root)), t_last)
                for p in sorted((root / key).glob('[!_]*'))
            }
        )
    )


def _read_meta(root: Path, key: str) -> Dict[str, object]:
    path = root / key / '_meta.yaml'
    if path.parent.is_file():
        raise bottle.HTTPError(404)
    try: meta = yaml.safe_load(path.read_text())
    except: meta = dict(spec=None, status='done')
    return dict(type='plain-object', content=meta)

#------------------------------------------------------------------------------
# HTTP response encoding

def _response(type: str, content: object) -> bottle.HTTPResponse:
    res = bottle.HTTPResponse(
        headers={'Content-Type': 'application/cbor',
                 'Access-Control-Allow-Origin': '*'},
        body=io.BytesIO(cbor2.dumps(dict(type=type, content=content)))
    )
    return res

