'''
Execution-context-local target-construction customization.

Exported definitions:
    Context (class): A collection of target-construction options.
    get_context (function): Return the call stack's currently active context.
    push_context (function): Replace the active context.
    pop_context (function): Revert to the previously active context.
    using_context (function): Return a context manager that makes a context
        active within its body.
'''

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from copy import copy
from itertools import groupby
from pathlib import Path
from types import MappingProxyType as MappingProxy
from typing import (
    Callable, Iterator, Mapping, MutableMapping,
    Optional, Type, Union, cast)

from ._artifacts import Artifact, active_builder, active_root
from ._targets import active_scope

__all__ = [
    'Context', 'get_context', 'pop_context',
    'push_context', 'using_context']



#-- `Context` ------------------------------------------------------------------

class Context:
    '''
    A collection of target-construction options.

    Arguments:
        root (Path | str | None):
            The default directory for artifact creation, and the directory that
            will be searched for matches when an artifact is instantiated from a
            specification. By default, `root` is the current working directory.
        scope (Mapping[str, type] | None):
            The mapping used to resolve type names in specifications during
            target instantiation. By default, `scope` contains all
            non-Artisan-defined target types.
        builder (Callable[[Artifact, object], None] | None):
            The function called to write files into artifact directories.
            `builder` accepts two arguments, the artifact to construct and its
            specification. The default builder calls `artifact.__init__(spec)`
            and logs metadata to a `_meta_.json` file. Custom builders can log
            additional information or offload work to other processes to build
            artifacts in parallel.

    :var root:
        `root` as a `Path`, if `root` was provided, or the default, otherwise.
    :var scope:
        `scope`, if `scope` was provided, or the default, otherwise.
    :var builder:
        `builder`, if `builder` was provided, or the default, otherwise.

    :vartype root: Path
    :vartype scope: Mapping[str, type]
    :vartype builder: Callable[[Artifact, object], None]
    '''
    def __init__(self, *,
                 root: Union[str, Path, None] = None,
                 scope: Optional[Mapping[str, type]] = None,
                 builder: Optional[Callable[[Artifact, object], None]] = None
                 ) -> None:
        self.root: Path = (
            initial_context.root
            if root is None
            else Path(root))
        self.scope: Mapping[str, type] = (
            initial_context.scope
            if scope is None
            else scope)
        self.builder: Callable[[Artifact, object], None] = (
            initial_context.builder
            if builder is None
            else builder)
        self._token: Optional[Token] = None



#-- Active context storage and retrieval ---------------------------------------

initial_context = Context(root = active_root.get(),
                          scope = active_scope.get(),
                          builder = active_builder.get()); \
    '''
    A `Context` constructed from the default configuration of the `_targets` and
    `_artifacts` modules.
    '''


active_context = ContextVar('artisan:context', default=initial_context); \
    '''
    A `ContextVar` that can be dereferenced to retreive the currently active
    context for the call stack.
    '''


def sync_context_vars() -> None:
    '''
    Propagate the options specified in `active_context` to other modules.
    '''
    context = active_context.get()
    active_root.set(context.root)
    active_scope.set(context.scope)
    active_builder.set(context.builder) # type: ignore


def push_context(context: Optional[Context] = None, *,
                 root: Union[Path, str, None] = None,
                 scope: Optional[Mapping[str, type]] = None,
                 builder: Optional[Callable[[Artifact, object], None]] = None
                 ) -> None:
    '''
    Replace the active context in the current call stack.

    `pop_context` can be called to revert to the previously active context.

    Arguments:
        context (Context | None):
            A context to make active. A new context will
            be created if one is not provided.
        root (Path | str | None):
            A value to override `context.root`.
        scope (Mapping[str, type] | None):
            A value to override `context.scope`.
        builder (Callable[[Artifact, object], None] | None):
            A value to override `context.builder`.
    '''
    new_context = copy(context) or Context()
    if root is not None: new_context.root = Path(root)
    if scope is not None: new_context.scope = scope
    if builder is not None: new_context.builder = builder
    new_context._token = active_context.set(new_context)
    sync_context_vars()


def pop_context() -> None:
    '''
    Revert to the previously active context.

    A `LookupError` is raised if no context was previously active.
    '''
    token = active_context.get()._token
    if token is not None: active_context.reset(token)
    else: raise LookupError('No context was previously active.')
    sync_context_vars()


@contextmanager
def using_context(context: Optional[Context] = None, *,
                  root: Union[Path, str, None] = None,
                  scope: Optional[Mapping[str, type]] = None,
                  builder: Optional[Callable[[Artifact, object], None]] = None
                  ) -> Iterator[None]:
    '''
    Return a context manager that makes a context active within its body.

    Arguments:
        context (Context | None):
            A context to make active. A new context will
            be created if one is not provided.
        root (Path | str | None):
            A value to override `context.root`.
        scope (Mapping[str, type] | None):
            A value to override `context.scope`.
        builder (Callable[[Artifact, object], None] | None):
            A value to override `context.builder`.
    '''
    push_context(context, root=root, scope=scope, builder=builder)
    try: yield
    finally: pop_context()


def get_context() -> Context:
    '''
    Return the call stack's currently active context.
    '''
    return active_context.get()
