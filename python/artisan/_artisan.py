'''
This module exports the `Artisan` class. `Artisan` objects represent the
thread-local state of an Artisan environment. They can also be used as an HTTP
server or WSGI application.
'''

from pathlib import Path
import threading
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Union
from wsgiref.simple_server import make_server

from ._artifacts import Artifact, set_root_dir
from ._configurables import default_scope, get_schema, set_scope
from ._http import wsgi_app
from ._namespaces import Namespace

__all__ = ['Artisan']

#------------------------------------------------------------------------------

class Artisan:
    '''
    The thread-local state of an Artisan environment

    `Artisan` objects can also be used as an HTTP or WSGI server.

    Parameters:
        root_dir: The default directory for artifact creation, and the
            directory that will be searched for matches when an artifact is
            instantiated from a specification
        scope: The mapping used to resolve `type`s in specifications during
            configurable object instantiation
        build: [Not currently used]
    '''
    root_dir: Path
    scope: Dict[str, type]
    build: Optional[Callable[[str, dict], None]]

    def __init__(self, *,
                 root_dir: Union[str, Path, None] = None,
                 scope: Optional[Mapping[str, type]] = None,
                 build: Optional[Callable[[str, dict], None]] = None) -> None:
        self.root_dir = Path('.') if root_dir is None else Path(root_dir)
        self.scope = default_scope if scope is None else Namespace(scope)
        self.build = Artifact if build is None else build # type: ignore

    #-- Context manipulation ------------------------------

    @staticmethod
    def get_current() -> 'Artisan':
        '''
        Return the currently active artisan.
        '''
        return artisan_stack.contents[-1]

    @staticmethod
    def push(artisan: Optional['Artisan'] = None, *,
             root_dir: Union[str, Path, None] = None,
             scope: Optional[Mapping[str, type]] = None,
             build: Optional[Callable[[str, dict], None]] = None) -> None:
        '''
        Push an artisan onto the thread-local artisan stack, making it active.

        `root_dir`, `scope`, and `build` override the corresponding attributes
        of `artisan` if they are defined.
        '''
        top_artisan = Artisan(
            root_dir = (
                root_dir if root_dir is not None
                else getattr(artisan, 'root_dir', None)
            ),
            scope = (
                scope if scope is not None
                else getattr(artisan, 'scope', None)
            ),
            build = (
                build if build is not None
                else getattr(artisan, 'build', None)
            )
        )
        artisan_stack.contents.append(top_artisan)
        set_scope(top_artisan.scope)
        set_root_dir(top_artisan.root_dir)

    @staticmethod
    def pop() -> 'Artisan':
        '''
        Remove and return the current artisan from the artisan stack.

        The previously present artisan becomes active after this method is
        called.
        '''
        set_scope(artisan_stack.contents[-2].scope)
        set_root_dir(artisan_stack.contents[-2].root_dir)
        return artisan_stack.contents.pop()

    def __enter__(self) -> None:
        ''' [Equivalent to `Artisan.push(self)`] '''
        Artisan.push(self)

    def __exit__(self, *args: object) -> None:
        ''' [Equivalent to `Artisan.pop()`] '''
        Artisan.pop()

    #-- JSON-Schema generation ----------------------------

    @property
    def schema(self) -> dict:
        '''
        The JSON Schema describing specifications accepted by this artisan
        '''
        with self:
            return get_schema()

    #-- HTTP API ------------------------------------------

    def __call__(self, env: dict, start_response: Callable) -> Iterable[bytes]:
        '''
        Respond to a WSGI server request.

        This method is defined so WSGI servers (*e.g.* `Gunicorn
        <https://gunicorn.org/>`_ ) can use an `Artisan` object as a WSGI
        application.
        '''
        with self:
            return wsgi_app(env, start_response)

    def serve(self, port: int = 3000) -> None:
        '''
        Start an HTTP server providing access to artifacts and the current
        schema.

        This method uses the reference WSGI server defined in the standard
        library. Other servers, which can be installed via `pip`, may be more
        robust and performant.
        '''
        with make_server('', port, self) as server:
            server.serve_forever()

#------------------------------------------------------------------------------

class ArtisanStack(threading.local):
    def __init__(self) -> None:
        self.contents: List[Artisan] = [Artisan()]

artisan_stack = ArtisanStack()
