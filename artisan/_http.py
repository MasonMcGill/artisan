'''
HTTP interfaces to Artisan contexts.

Exported definitions:
    API (class): A WSGI server that provides access to an Artisan context.
    WebUI (class): An HTTP responder for HTML UI requests.
    asset_builder (function decorator): <Not yet implemented>
    default_asset_builders (list): <Not yet implemented>
'''

from __future__ import annotations

import json, mimetypes, traceback
from base64 import b64decode
from datetime import datetime
from io import BufferedReader
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import (
    Callable, Collection, Dict, Iterator, List,
    Mapping, Optional, Tuple, TypeVar, Union, cast)
from wsgiref.simple_server import make_server

try:
    from fcntl import LOCK_SH, LOCK_UN, lockf
    locking_is_supported = True
except ImportError:
    locking_is_supported = False

import cbor2

from ._artifacts import Artifact, DynamicArtifact, build
from ._context import Context, get_context, using_context
from ._fs_index import DirIndex
from ._schemas import (
    get_spec_schema, get_spec_dict_schema,
    get_spec_list_schema)

T = TypeVar('T')

__all__ = ['API', 'WebUI', 'asset_builder', 'default_asset_builders']



#-- `API` ----------------------------------------------------------------------

class API:
    '''
    A WSGI server that provides access to an Artisan context.

    The following request types are supported:

    - `GET /artifacts{/path*}`
    - `POST /artifacts`
    - `DELETE /artifacts{/path*}`
    - `GET /schemas/spec`
    - `GET /schemas/spec-list`
    - `GET /schemas/spec-dict`
    - `GET /ui{/path*}`

    Analogous `HEAD` and `OPTIONS` requests are also supported.

    Arguments:
        permissions: A mapping from passwords to permission sets. Permissions
            sets can contain "read", "write", and/or "delete". The default
            permission policy is `{'': ('read', 'write', 'delete')}`, meaning
            even users who have not provided a password have "read", "write",
            and "delete" permissions.
        ui: The WSGI server that should handle requests in the form
            `/ui{/path*}`. The default UI is a `WebUI`.
        root: A path to override the active context's `root`.
        scope: A mapping to override the active context's `scope`.
        builder: A callable to override the active context's `builder`.
    '''
    def __init__(self, *,
                 permissions: Optional[Mapping[str, Collection[str]]] = None,
                 ui: Optional[Callable[[dict, Callable], None]] = None,
                 root: Union[str, Path, None] = None,
                 scope: Optional[Mapping[str, type]] = None,
                 builder: Optional[Callable[[Artifact, object], None]] = None
                 ) -> None:
        permissions = (
            permissions if permissions is not None
            else {'': ('read', 'write', 'delete')})
        self._allowed_methods = {
            password: (
                ('read' in user_perm) * ('OPTIONS', 'HEAD', 'GET')
                + ('write' in user_perm) * ('POST',)
                + ('delete' in user_perm) * ('DELETE',))
            for password, user_perm in permissions.items()}

        active_context = get_context()
        self._context = Context(
            root = active_context.root if root is None else root,
            scope = active_context.scope if scope is None else scope,
            builder = active_context.builder if builder is None else builder)

        with using_context(self._context):
            self._context.root.mkdir(parents=True, exist_ok=True)
            self._request_handlers: Dict[str, Callable] = {
                '/artifacts': ArtifactAPI(),
                '/schemas': SchemaAPI(),
                '/ui': ui or WebUI()}

    def __call__(self, env: dict, responder: Callable) -> Iterator[bytes]:
        '''
        Respond to a WSGI server request.
        '''
        method = env['REQUEST_METHOD']
        auth = env.get('HTTP_AUTHORIZATION', '')
        password = b64decode(auth.split(' ')[-1]).decode('utf8')[1:]
        if method not in self._allowed_methods.get(password, ()):
            responder('401 Unauthorized', [])
            return iter(())

        try:
            with using_context(self._context):
                prefix = '/'.join(env['PATH_INFO'].split('/')[:2])
                return self._request_handlers[prefix](env, responder)
        except KeyError:
            responder('404 Not Found', [])
            return iter(())

    def serve(self, port: int = 8000) -> None:
        '''
        Start a server on the specified port.

        This method uses the reference WSGI server defined in the standard
        library. Other servers, which can be installed via `pip`, may be more
        robust and performant.
        '''
        with make_server('', port, self) as server: # type: ignore
            server.serve_forever()



#-- Artifact-request-handling --------------------------------------------------

class ArtifactAPI:
    '''
    An HTTP responder for artifact creation, access, and modification requests.

    Supported routes:
        `GET /artifacts{/path*}`: Respond with the corresponding file or a
            shallow representation of the corresponding directory.
        `POST /artifacts{/path*}`: Create a new artifact from a specification. A
            password with "write" permission is required.
        `DELETE /artifacts{/path*}`: Delete the artifact at the given path. A
            password with "delete" permission is required.

    Analogous `HEAD` and `OPTIONS` requests are also supported.
    '''
    def __init__(self, prefix: str = '/artifacts') -> None:
        self._prefix = prefix
        self._root = get_context().root.resolve()

    def __call__(self, env: dict, responder: Callable) -> Iterator[bytes]:
        method = env['REQUEST_METHOD']
        handler = (
            self._handle_options_request if method == 'OPTIONS' else
            self._handle_head_request if method == 'HEAD' else
            self._handle_get_request if method == 'GET' else
            self._handle_post_request if method == 'POST' else
            self._handle_delete_request if method == 'DELETE' else
            self._handle_405_error)
        static_headers = [
            ('Access-Control-Allow-Origin', '*'),
            ('Cache-Control', 'no-cache')]
        try:
            status, dynamic_headers, body, *work = handler(env)
            responder(status, static_headers + dynamic_headers)
            yield body
            for work_item in work:
                work_item()
        except ValueError:
            responder('400 Bad Request', static_headers)
            return iter(())
        except PermissionError:
            responder('403 Forbidden', static_headers)
            return iter(())
        except OSError:
            responder('404 Not Found', static_headers)
            return iter(())
        except Exception:
            responder('500 Internal Server Error', static_headers)
            yield traceback.format_exc().encode('utf8')

    def _handle_options_request(self, env: dict) -> tuple:
        return ('204 No Content',
                [('Access-Control-Allow-Methods', '*'),
                 ('Access-Control-Allow-Headers', '*'),
                 ('Allow', 'OPTIONS, HEAD, GET, POST, DELETE')],
                b'')

    def _handle_head_request(self, env: dict) -> tuple:
        env = {**env, 'HTTP_RANGE': 'bytes=0-0'}
        return (*self._handle_get_request(env)[:2], b'')

    def _handle_get_request(self, env: dict) -> tuple:
        path = self._get_path(env)
        if path.is_file():
            return self._handle_file_get_request(env, path)
        else:
            return self._handle_dir_get_request(env, path)

    def _handle_file_get_request(self, env: dict, path: Path) -> tuple:
        timestamp = get_file_timestamp(path)
        if get_last_request_time(env) >= timestamp:
            return ('304 Not Modified', [], b'')
        else:
            start, end = env.get('HTTP_RANGE', '0-').strip('bytes=').split('-')
            start, end = int(start), (int(end) if end != '' else 2**48)
            timestamp_str = (
                datetime.fromtimestamp(timestamp)
                .strftime('%a, %d %b %Y %H:%M:%S GMT'))
            body = read_file(path, start, end)
            return ('200 OK',
                    [('Content-Type', get_content_type(path)),
                     ('Content-Length', str(len(body))),
                     ('Last-Modified', timestamp_str)],
                    body)

    def _handle_dir_get_request(self, env: dict, path: Path) -> tuple:
        timestamp = get_dir_timestamp(path)
        if get_last_request_time(env) >= timestamp:
            return ('304 Not Modified', [], b'')
        else:
            timestamp_str = (
                datetime.fromtimestamp(timestamp)
                .strftime('%a, %d %b %Y %H:%M:%S GMT'))
            entries = {name: None for name in (DynamicArtifact @ path)}
            body = cbor2.dumps({'_meta_': DirIndex(path).get_meta(), **entries})
            return ('200 OK',
                    [('Content-Type', 'application/cbor'),
                     ('Content-Length', str(len(body))),
                     ('Last-Modified', timestamp_str)],
                    body)

    def _handle_post_request(self, env: dict) -> tuple:
        work: List[Callable] = []
        original_builder = get_context().builder
        def delayed_builder(artifact: Artifact, spec: object) -> None:
            work.append(lambda: original_builder(artifact, spec))

        req_body_size = int(env.get('CONTENT_LENGTH', '0'))
        req_body = cbor2.loads(env['wsgi.input'].read(req_body_size))
        with using_context(get_context(), builder=delayed_builder):
            validate_path_strings(req_body)
            artifact = build(Artifact, req_body)

        uri = f'{self._prefix}/{artifact._path_.relative_to(self._root)}'
        headers = [('Content-Length', '0'), ('Location', uri)]
        return ('201 Created', headers, b'', *work)

    def _handle_delete_request(self, env: dict) -> tuple:
        with TemporaryDirectory() as dst:
            self._get_path(env).rename(Path(dst, 'tree-to-delete'))
        return ('204 No Content', [], b'')

    def _handle_405_error(self, env: dict) -> tuple:
        return ('405 Method Not Allowed',
                [('Allow', 'OPTIONS, HEAD, GET, POST, DELETE')],
                b'')

    def _get_path(self, env: dict) -> Path:
        path = env['PATH_INFO'][len(self._prefix)+1:]
        path = (self._root / path).resolve()
        path = DirIndex(path.parent).get_entry_path(path.stem)
        if path is None:
            raise FileNotFoundError()
        elif self._root not in (*path.parents, path):
            raise PermissionError()
        else:
            return path


def get_file_timestamp(path: Path) -> float:
    mtime = path.stat().st_mtime
    return min(mtime, datetime.now().timestamp() - 2)


def get_dir_timestamp(path: Path) -> float:
    try:
        meta_mtime = (path / '_meta_.json').stat().st_mtime
    except FileNotFoundError:
        meta_mtime = 0.0
    mtime = max(path.stat().st_mtime, meta_mtime)
    return min(mtime, datetime.now().timestamp() - 2)


def get_last_request_time(env: dict) -> float:
    try:
        time_format = '%a, %d %b %Y %H:%M:%S GMT'
        if_mod_header = env['HTTP_IF_MODIFIED_SINCE']
        return datetime.strptime(if_mod_header, time_format).timestamp()
    except (KeyError, ValueError):
        return 0.0


def get_content_type(path: Path) -> str:
    return ('application/cbor' if path.suffix == '.cbor' else
            mimetypes.types_map.get(path.suffix, 'application/octet-stream'))


def read_file(path: Path, start: int, end: int) -> bytes:
    '''
    Read a file, locking the first 128 bytes while reading them.
    '''
    buf = bytearray(min(end, path.stat().st_size) - start)
    with cast(BufferedReader, open(path, 'rb')) as f:
        if locking_is_supported: lockf(f, LOCK_SH, 128)
        header = cast(bytes, f.read(128))
        if locking_is_supported: lockf(f, LOCK_UN)
        f.seek(start)
        f.readinto(buf)
    buf[:len(header[start:])] = header[start:]
    return bytes(buf)


def validate_path_strings(obj: object) -> None:
    '''
    Raise a `PermissionError` if `obj` contains any path strings outside the
    root artifact directory.
    '''
    root = get_context().root.resolve()
    if isinstance(obj, str) and obj.startswith('@/'):
        path = (root / obj[2:]).resolve()
        if root not in (*path.parents, path):
            raise PermissionError(f'`{path}` is not in `{root}`')
    elif isinstance(obj, list):
        for v in obj:
            validate_path_strings(v)
    elif isinstance(obj, dict):
        if '_path_' in obj:
            path_str = obj['_path_']
            if not path_str.startswith('@/'):
                raise PermissionError(f'`_path_` must start with "@/"')
            path = (root / path_str[2:]).resolve()
            if root not in (*path.parents, path):
                raise PermissionError(f'`{path}` is not in `{root}`')
        for v in obj.values():
            validate_path_strings(v)



#-- Schema-request-handling ----------------------------------------------------

class SchemaAPI:
    '''
    An HTTP responder for JSON schema requests.

    Supported routes:
        `GET /schemas/spec`: Returns `get_spec_schema()`.
        `GET /schemas/spec-list`: Returns `get_spec_list_schema()`.
        `GET /schemas/spec-dict`: Returns `get_spec_dict_schema()`.

    Analogous `HEAD` and `OPTIONS` requests are also supported.
    '''
    def __init__(self) -> None:
        encode = lambda x: json.dumps(x, indent=2).encode('utf8')
        self._schemas = {
            '/schemas/spec': encode(get_spec_schema()),
            '/schemas/spec-list': encode(get_spec_list_schema()),
            '/schemas/spec-dict': encode(get_spec_dict_schema())}

    def __call__(self, env: dict, responder: Callable) -> Iterator[bytes]:
        method = env['REQUEST_METHOD']
        handler = (
            self._handle_options_request if method == 'OPTIONS' else
            self._handle_head_request if method == 'HEAD' else
            self._handle_get_request if method == 'GET' else
            self._handle_405_error)
        static_headers = [
            ('Access-Control-Allow-Origin', '*'),
            ('Cache-Control', 'no-cache')]
        status, dynamic_headers, body = handler(env)
        responder(status, static_headers + dynamic_headers)
        yield body

    def _handle_options_request(self, env: dict) -> tuple:
        return ('204 No Content',
                [('Access-Control-Allow-Methods', '*'),
                 ('Access-Control-Allow-Headers', '*'),
                 ('Allow', 'OPTIONS, HEAD, GET')],
                b'')

    def _handle_head_request(self, env: dict) -> tuple:
        return (*self._handle_get_request(env)[:2], b'')

    def _handle_get_request(self, env: dict) -> tuple:
        try:
            schema = self._schemas[env['PATH_INFO']]
            return ('200 OK',
                    [('Content-Type', 'application/schema+json'),
                     ('Content-Length', str(len(schema)))],
                    schema)
        except KeyError:
            return ('404 Not Found', [], b'')

    def _handle_405_error(self, env: dict) -> tuple:
        return ('405 Method Not Allowed',
                [('Allow', 'OPTIONS, HEAD, GET')],
                b'')



#-- UI-request-handling --------------------------------------------------------

class WebUI:
    '''
    An HTTP responder for HTML UI requests.
    '''
    # TODO: Make this more than a placeholder.

    def __init__(self, *,
                 prefix: str = '/ui',
                 styles: List[Union[Path, str]] = [],
                 scripts: List[Union[Path, str]] = [],
                 asset_builders: Optional[List[Tuple[str, Callable]]] = None
                 ) -> None:
        self._prefix = prefix

    def __call__(self, env: dict, responder: Callable) -> Iterator[bytes]:
        method = env['REQUEST_METHOD']
        handler = (
            self._handle_options_request if method == 'OPTIONS' else
            self._handle_head_request if method == 'HEAD' else
            self._handle_get_request if method == 'GET' else
            self._handle_405_error)
        static_headers = [
            ('Access-Control-Allow-Origin', '*'),
            ('Cache-Control', 'no-cache')]
        status, dynamic_headers, body = handler(env)
        responder(status, static_headers + dynamic_headers)
        yield body

    def _handle_options_request(self, env: dict) -> tuple:
        return ('204 No Content',
                [('Access-Control-Allow-Methods', '*'),
                 ('Access-Control-Allow-Headers', '*'),
                 ('Allow', 'OPTIONS, HEAD, GET')],
                b'')

    def _handle_head_request(self, env: dict) -> tuple:
        return (*self._handle_get_request(env)[:2], b'')

    def _handle_get_request(self, env: dict) -> tuple:
        path = env['PATH_INFO'][len(self._prefix)+1:]
        core_asset_path = Path(__file__).parent / '_ui'

        if path in ('', '/'):
            content_type = 'text/html'
            content = (
                (core_asset_path / 'index.html').read_text()
                .replace('{{extensionStyles}}', '')
                .replace('{{extensionScripts}}', '')
                .replace('{{refreshInterval}}', '1')
                .encode())
        elif path.startswith('_core-assets/'):
            resource_name = path.replace('_core-assets/', '', 1)
            content_type = get_content_type(Path(resource_name))
            content = (core_asset_path / resource_name).read_bytes()
        else:
            return ('404 Not Found', [], b'')

        return ('200 OK',
                [('Content-Type', content_type),
                 ('Content-Length', str(len(content)))],
                content)

    def _handle_405_error(self, env: dict) -> tuple:
        return ('405 Method Not Allowed',
                [('Allow', 'OPTIONS, HEAD, GET')],
                b'')

    def asset_builder(self, uri_template: str) -> Callable[[T], T]:
        raise NotImplementedError()


default_asset_builders: List[Tuple[str, Callable]] = []


def asset_builder(uri_template: str) -> Callable[[T], T]:
    def add_builder(builder: T) -> T:
        if callable(builder):
            default_asset_builders.append(
                (uri_template, builder))
        return builder
    return add_builder
