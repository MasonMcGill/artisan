'''
Functionality for defining user-constructable objects.

Exported definitions:
    Target (abstract class): An object that can be constructed via an Artisan
        command-line interface or REST API. `Target` is intended to be
        subclassed by application authors.

Internal definitions:
    TargetType (metaclass): `Target`'s metaclass.
    active_scope (context variable): The mapping used to resolve type names in
        specifications during target instantiation.
'''

from __future__ import annotations

from abc import ABCMeta
from contextvars import ContextVar
from copy import copy
from functools import lru_cache
from itertools import groupby
from typing import (
    ClassVar, Dict, Iterator, Optional,
    Mapping, Tuple, Type, TypeVar)
from typing_extensions import Protocol
from weakref import WeakValueDictionary, finalize
T = TypeVar('T')

__all__ = ['Target', 'TargetType', 'active_scope']



#-- `Target`'s metaclass -------------------------------------------------------

class TargetType(ABCMeta):
    '''
    `Target`'s metaclass.

    `TargetType.__call__` performs subclass forwarding and fills in missing
    `spec` attributes before calling `__new__` and `__init__`.
    '''
    def __call__(cls: Type[T], *args: object, **kwargs: object) -> T:
        cls, args = cls._refine_call_args(args) # type: ignore
        return super().__call__(*args, **kwargs) # type: ignore

    def _refine_call_args(cls: Type[T],
                          other_args: Tuple[object, ...]
                          ) -> Tuple[Type[T], Tuple[object, ...]]:
        '''
        Perform subclass forwarding and fill in missing `spec` attributes.
        '''
        # Narrow `cls` based on `spec.type`.
        spec = next(iter(other_args), object())
        cls_spec = getattr(spec, 'type', None)
        refined_cls = (
            active_scope.get()[cls_spec] if isinstance(cls_spec, str)
            else cls_spec if isinstance(cls_spec, type)
            else cls)

        # Add default attribute values to `spec`.
        defaults = get_spec_defaults(refined_cls).items()
        missing_items = [(k, v) for k, v in defaults if not hasattr(spec, k)]
        refined_spec = copy(spec) if missing_items else spec
        refined_spec.__dict__.update(missing_items)

        # Check that the subclass is valid.
        if not issubclass(refined_cls, cls):
            raise ValueError(f'`{refined_cls}` is not a subclass of `{cls}`.')

        # Return the refined arguments.
        return refined_cls, (refined_spec, *other_args[1:])


@lru_cache(maxsize=None)
def get_spec_defaults(cls: type) -> Dict[str, object]:
    '''
    Return the default specification attributes for a type.
    '''
    spec_type = getattr(cls, 'Spec', None)
    return {k: getattr(spec_type, k)
            for k in dir(spec_type)
            if not k.startswith('_')
            and not callable(getattr(spec_type, k))}



#-- `Target` -------------------------------------------------------------------

class Target(metaclass=TargetType):
    '''
    A user-constructable object.

    All target constructors should accept a specification as their first
    argument. Specification attributes can be boolean values, integers,
    floating-point numbers, strings, `None` values, `pathlib.Path` objects,
    artifacts, lists of allowed values, and namespace-like objects with
    `__dict__` attributes containing only allowed values.

    If `spec` has a `type` attribute, `Target`'s constructor will dereference it
    in the current target scope and return an instance of the resulting type.
    The default target scope contains every `Target` subclass defined outside of
    the `artisan` library, and uses keys in the form `<subclass>.__qualname__`
    for uniquely named target types and `f'{<subclass>.__qualname__}
    ({<subclass>.__module__})'` for target types with non-unique names.
    `artisan.push_context` or `artisan.using_context` can be used to set the
    active target scope.

    `Target` types can define an inner `Spec` class to indicate the expected
    type of `spec`. If `<subclass>.Spec` is not defined explicitly, it will be
    defined implicitly as a protocol with no required fields. Public,
    non-callable attributes of `<subclass>.Spec` will be used as default values
    for missing `spec` attributes.

    Parameters:
        spec: The target's specification.
    '''
    class Spec(Protocol):
        'A protocol describing valid specifications.'

    def __init_subclass__(cls, abstract: bool = False) -> None:
        # Add a specification class if one has not been defined.
        if 'Spec' not in cls.__dict__:
            class Spec(Protocol): pass
            Spec.__module__ = cls.__module__
            Spec.__qualname__ = cls.__qualname__ + '.Spec'
            cls.Spec = Spec # type: ignore

        # Keep the target type registry in sync.
        TargetTypeRegistry._invalidate()
        finalize(cls, TargetTypeRegistry._invalidate)

    def __new__(cls: Type[T], *args: object, **kwargs: object) -> T:
        return object.__new__(cls)

    def __init__(self, spec: Spec) -> None:
        pass



#-- `TargetTypeRegistry` and `active_scope` ------------------------------------

class TargetTypeRegistry(Mapping[str, Type[Target]]):
    '''
    A mapping containing all `Target` subclasses defined outside of the
    `artisan` module.

    The key for a target type `T` is `T.__qualname__` if its name is unique and
    `f'{T.__qualname__} ({T.__module__})'` otherwise.
    '''
    _cache: ClassVar[Optional[Mapping[str, Type[Target]]]] = None

    def __len__(self) -> int:
        return self._get_content().__len__()

    def __iter__(self) -> Iterator[str]:
        return self._get_content().__iter__()

    def __contains__(self, key: object) -> bool:
        return self._get_content().__contains__(key)

    def __getitem__(self, key: str) -> Type[Target]:
        return self._get_content().__getitem__(key)

    @classmethod
    def _get_content(cls) -> Mapping[str, Type[Target]]:
        if cls._cache is None:
            types_by_name = [
                (name, list(group)) for name, group in
                groupby(cls._values(), lambda t: t.__qualname__)]
            cls._cache = WeakValueDictionary({
                name + (len(group) > 1) * f' ({type_.__module__})': type_
                for name, group in types_by_name
                for type_ in group})
        return cls._cache

    @classmethod
    def _invalidate(cls) -> None:
        cls._cache = None

    @classmethod
    def _values(cls, base: Type[Target] = Target) -> Iterator[Type[Target]]:
        if not base.__module__.startswith('artisan'):
            yield base
        for subtype in base.__subclasses__():
            yield from cls._values(subtype)


active_scope: ContextVar[Mapping[str, type]] = (
        ContextVar('artisan:scope', default=TargetTypeRegistry())); \
    '''
    The mapping used to resolve type names in specifications during target
    instantiation.
    '''
