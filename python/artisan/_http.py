'''
This module exports the `wsgi_app` object, a WSGI application that supports
queries of artifact data and metadata.

TODO: Switch to the following HTTP endpoints:
- `/_schema`: The schema, in JSON format
- `/x/y/z[t_last=null]`: A full fetch of an artifact, file, or array
- `/x/y/z/_meta[depth=0]`: Artifact/file/array metadata
'''

from multiprocessing import cpu_count
from pathlib import Path
import re
from typing import Dict, Iterator, Optional as Opt, cast

import cbor2
from falcon import API, HTTPStatus, Request, Response, HTTP_200, HTTP_404
from gunicorn.app.base import BaseApplication as GunicornApp
import h5py as h5
from ruamel import yaml

from ._artifacts import get_root_dir
from ._configurables import get_schema

__all__ = ['serve']

#-- Web API -------------------------------------------------------------------

def write_response(req: Request, res: Response) -> None:
    root = get_root_dir()
    res.content_type = 'application/cbor'
    res.set_header('Access-Control-Allow-Origin', '*')

    if req.path.endswith('/_entry-names'):
        path = root / req.path[1:-len('/_entry-names')]
        if path.is_file(): raise HTTPStatus(HTTP_404)
        res.data = cbor2.dumps(dict(
            type='plain-object',
            content=sorted([
                re.sub(r'\.h5$', '', p.name) + ('/' if p.is_dir() else '')
                for p in path.glob('[!_]*')
            ])
        ))

    elif req.path.endswith('/_entries'):
        path = root / req.path[1:-len('/_entries')]
        if path.is_file(): raise HTTPStatus(HTTP_404)
        res.data = cbor2.dumps(dict(
            type='plain-object',
            content=list(_entries(path))
        ))

    elif req.path == '/_meta':
        res.data = cbor2.dumps(dict(
            type='plain-object',
            content=dict(spec=None, schema=get_schema())
        ))

    elif req.path.endswith('/_meta'):
        key = req.path[1:-len('/_meta')]
        if (root / key).with_suffix('.h5').is_file():
            res.data = cbor2.dumps(dict(
                type='plain-object',
                content={'IS_ARRAY': True}
            ))
        else:
            res.data = cbor2.dumps(_read_meta(root, key))

    else:
        t_last = float(req.get_param('t_last') or 0) / 1000
        entry = _read(root, req.path[1:], t_last)
        if entry['type'] == 'file':
            res.data = (root / cast(str, entry['content'])).read_bytes()
        else:
            res.data = cbor2.dumps(entry)

    res.status = HTTP_200


class HandleCORS(object):
    def process_request(self, req: Request, res: Response) -> None:
        res.set_header('Access-Control-Allow-Origin', '*')
        res.set_header('Access-Control-Allow-Methods', '*')
        res.set_header('Access-Control-Allow-Headers', '*')
        res.set_header('Access-Control-Max-Age', 600)
        if req.method == 'OPTIONS':
            raise HTTPStatus(HTTP_200)


wsgi_app = API(middleware=[HandleCORS()])
wsgi_app.add_sink(write_response)

#-- I/O -----------------------------------------------------------------------

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
    a = f['data'][()]

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
        raise HTTPStatus(HTTP_404)
    try: meta = yaml.safe_load(path.read_text())
    except: meta = dict(spec=None, status='done')
    return dict(type='plain-object', content=meta)


def _entries(path: Path) -> Iterator[dict]:
    for p in sorted(path.glob('[!_]*')):
        if p.is_dir():
            yield {
                'type': 'artifact',
                'name': p.name,
                'nEntries': len(list(p.iterdir()))
            }

        elif p.suffix == '.h5':
            f = h5.File(p, 'r', libver='latest', swmr=True)
            a = f['data'][()]
            if a.dtype.kind in ['U', 'S']:
                yield {
                    'type': 'string-array',
                    'name': p.stem,
                    'dtype': 'string',
                    'shape': a.shape
                }
            else:
                yield {
                    'type': 'numeric-array',
                    'name': p.stem,
                    'dtype': _web_dtypes[a.dtype.name],
                    'shape': a.shape
                }

        else:
            yield {
                'type': 'file',
                'name': p.name,
                'size': p.stat().st_size
            }
