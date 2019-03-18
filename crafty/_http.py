import io
from pathlib import Path
from typing import Optional as Opt

import bottle
import cbor2
import numpy as np

from ._artifacts import Artifact
from ._global_conf import get_conf

__all__ = ['serve']

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


def _response(type_: str, content: object) -> bottle.HTTPResponse:
    return bottle.HTTPResponse(
        headers={'Content-Type': 'application/msgpack',
                 'Access-Control-Allow-Origin': '*'},
        body=io.BytesIO(cbor2.dumps(dict(type=type_, content=content))))


def _encode_entry(ent: np.ndarray) -> bottle.HTTPResponse:
    if ent.dtype.kind in ['U', 'S']:
        return _response('string-array', ent.astype('U').tolist())
    else:
        ent = ent.astype(_web_dtypes[ent.dtype.name])
        return _response('numeric-array', dict(
            shape=ent.shape,
            dtype=ent.dtype.name,
            data=ent.data.tobytes()
        ))


def serve(port: int = 3000, root_dir: Opt[str] = None) -> None:
    '''
    Start a server providing access to the records in a directory.
    '''
    root = Artifact(root_dir or get_conf().root_dir)
    app = bottle.default_app()

    @app.route('/<:re:.*>', method='OPTIONS')
    def _(*_):
        return bottle.HTTPResponse(headers={
            'Allow': 'OPTIONS, GET, HEAD',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*'
        })

    @app.get('/_entry-names') # type: ignore
    @app.get('/<rec_id:path>/_entry-names')
    def _(rec_id=''):
        if not (root.path/rec_id).is_dir():
            raise bottle.HTTPError(404)
        return _response('plain-object', list(root[rec_id]))

    @app.get('/<rec_id:path>/_cmd-info') # type: ignore
    def _(rec_id):
        if (root.path/rec_id).is_dir():
            return _response('plain-object', root[rec_id].cmd_info)
        else:
            raise bottle.HTTPError(404)

    @app.get('/<ent_id:path>') # type: ignore
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
