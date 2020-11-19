from types import SimpleNamespace as Ns
from typing import Type
from typing_extensions import Protocol

from artisan import Target
from artisan._targets import active_scope


def test_spec_class_generation() -> None:
    '''
    Test that, if a `Target` subclass does not define an inner `Spec` class,
    `<subclass>.Spec` will be generated.
    '''
    Subtype: Type[Target] = type('Subtype', (Target,), {})
    assert isinstance(Subtype.Spec, type)
    assert Subtype.Spec.__qualname__ == 'Subtype.Spec'


def test_subclass_forwarding_with_types() -> None:
    '''
    Test that if a `Target`'s specification contains a `type` field that is a
    type, `__new__` returns an instance of the resulting type.
    '''
    Parent: Type[Target] = type('Parent', (Target,), {})
    ChildA: Type[Target] = type('ChildA', (Parent,), {})
    ChildB: Type[Target] = type('ChildB', (Parent,), {})
    assert isinstance(Parent(Ns(type=ChildA)), ChildA)
    assert isinstance(Parent(Ns(type=ChildB, k0='v0', k1='v1')), ChildB)


def test_subclass_forwarding_with_strings() -> None:
    '''
    Test that if a `Target`'s specification contains a `type` field that is a
    string, `__new__` dereferences it in the current target scope and returns an
    instance of the resulting type.
    '''
    Parent: Type[Target] = type('Parent', (Target,), {})
    ChildA: Type[Target] = type('ChildA', (Parent,), {})
    ChildB: Type[Target] = type('ChildB', (Parent,), {})
    assert isinstance(Parent(Ns(type='ChildA')), ChildA)
    assert isinstance(Parent(Ns(type='ChildB', k0='v0', k1='v1')), ChildB)


def test_default_scope() -> None:
    '''
    Test that the default target scope contains every `Target` subclass defined
    outside of the `artisan` module.
    '''
    Parent: Type[Target] = type('Parent', (Target,), {})
    ChildA: Type[Target] = type('ChildA', (Parent,), {})
    ChildB_x: Type[Target] = type('ChildB', (Parent,), {'__module__': 'x'})
    ChildB_y: Type[Target] = type('ChildB', (Parent,), {'__module__': 'y'})
    assert active_scope.get()['Parent'] == Parent
    assert active_scope.get()['ChildA'] == ChildA
    assert active_scope.get()['ChildB (x)'] == ChildB_x
    assert active_scope.get()['ChildB (y)'] == ChildB_y


def test_subclass_forwarding_with_custom_scopes() -> None:
    '''
    Test target type name rebinding.
    '''
    Parent: Type[Target] = type('Parent', (Target,), {})
    ChildA: Type[Target] = type('ChildA', (Parent,), {})
    ChildB: Type[Target] = type('ChildB', (Parent,), {})

    try:
        token = active_scope.set(dict(A=ChildA, B=ChildB))
        assert isinstance(Parent(Ns(type='A')), ChildA)
        assert isinstance(Parent(Ns(type='B', k0='v0', k1='v1')), ChildB)
    finally:
        active_scope.reset(token)


def test_default_spec_attrs() -> None:
    '''
    Test filling in `spec` attributes based on `Spec` class fields.
    '''
    class MyTarget(Target):
        class Spec(Protocol):
            x: int = 0
            y: int = 1

        def __init__(self, spec: Spec) -> None:
            self.x = spec.x
            self.y = spec.y

    assert MyTarget(Ns(x=2, y=3)).x == 2
    assert MyTarget(Ns(x=2, y=3)).y == 3
    assert MyTarget(Ns(x=2)).x == 2
    assert MyTarget(Ns(x=2)).y == 1
    assert MyTarget(Ns()).x == 0
    assert MyTarget(Ns()).y == 1
