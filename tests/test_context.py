from pathlib import Path
from string import ascii_letters, digits
from typing import (
    Callable, List, Mapping, Optional, Type, TypedDict, Union)

from hypothesis import given
from hypothesis.strategies import (
    SearchStrategy, binary, booleans, builds,
    dictionaries, functions, lists, none, text)

from artisan import (
    Artifact, Context, Target, get_context,
    pop_context, push_context, using_context)
from artisan._targets import TargetTypeRegistry



#-- Supporting definitions -----------------------------------------------------

class ContextArgDict(TypedDict):
    '''
    A keyword-argument dictionary that can be used to construct a `Context`.
    '''
    root: Union[None, str, Path]
    scope: Optional[Mapping[str, Type[Target]]]
    builder: Optional[Callable[[Artifact, object], None]]


def context_arg_dicts() -> SearchStrategy[ContextArgDict]:
    '''
    Return a search strategy that samples `ContextArgDict`s.
    '''
    return builds(dict, # type: ignore
        root = none() | builds(str, paths()) | paths(),
        scope = none() | dictionaries(text(), binary()),
        builder = none() | functions(like=(lambda artifact, spec: None)))


def paths() -> SearchStrategy[Path]:
    '''
    Return a search strategy that samples paths.
    '''
    return builds(Path, text(ascii_letters + digits + '/.'))


def fields_match(c0: Context, c1: Context) -> bool:
    '''
    Return whether two contexts correspond to identical target-building
    behavior.
    '''
    return (c0.root == c1.root and
            c0.scope == c1.scope and
            c0.builder == c1.builder)



#-- Tests ----------------------------------------------------------------------

@given(context_arg_dicts())
def test_construction(arg_dict: ContextArgDict) -> None:
    '''
    Test `Context` construction.
    '''
    root = arg_dict['root']
    scope = arg_dict['scope']
    builder = arg_dict['builder']
    ctx = Context(**arg_dict)
    assert ctx.root == (Path('.') if root is None else Path(root))
    assert ctx.scope == (TargetTypeRegistry() if scope is None else scope)
    assert ctx.builder == (Context().builder if builder is None else builder)


@given(lists(context_arg_dicts(), min_size=1), booleans())
def test_pushing_contexts(arg_dicts: List[ContextArgDict], wrap: bool) -> None:
    '''
    Test `push_context`.
    '''
    for arg_dict in arg_dicts:
        if wrap: push_context(Context(**arg_dict))
        else: push_context(**arg_dict)
    assert fields_match(get_context(), Context(**arg_dicts[-1]))

    for _ in arg_dicts:
        pop_context()
    assert fields_match(get_context(), Context())


@given(lists(context_arg_dicts(), min_size=1), booleans())
def test_using_contexts(arg_dicts: List[ContextArgDict], wrap: bool) -> None:
    '''
    Test `using_context`.
    '''
    context_blocks = [
        using_context(Context(**arg_dict)) if wrap
        else using_context(**arg_dict)
        for arg_dict in arg_dicts]

    for block in context_blocks:
        block.__enter__()
    assert fields_match(get_context(), Context(**arg_dicts[-1]))

    for block in reversed(context_blocks):
        block.__exit__(None, None, None)
    assert fields_match(get_context(), Context())
