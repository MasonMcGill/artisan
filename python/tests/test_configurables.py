import fastjsonschema
import pytest

from artisan._configurables import (
    Configurable, get_schema, get_scope, set_scope
)

#-- Shared definitions --------------------------------------------------------

class Parent(Configurable):
    pass


class ChildA(Parent):
    class Conf:
        a: int
        b: int


class ChildB(Parent):
    class Conf:
        x: float
        y: float

#-- `Configurable` tests ------------------------------------------------------

def test_direct_instantiation():
    obj = ChildA(dict(a=1, b=2))
    assert isinstance(obj, ChildA)
    assert obj.conf.a == 1
    assert obj.conf.b == 2


def test_subclass_forwarding_with_types():
    obj = Parent(dict(type=ChildA, a=1.0, b=2.0))
    assert isinstance(obj, ChildA)
    assert obj.conf.a == 1.0
    assert obj.conf.b == 2.0

    obj = Parent(dict(type=ChildB, x=1, y=2))
    assert isinstance(obj, ChildB)
    assert obj.conf.x == 1
    assert obj.conf.y == 2


def test_subclass_forwarding_with_strings():
    obj = Parent(dict(type='ChildA', a=1.0, b=2.0))
    assert isinstance(obj, ChildA)
    assert obj.conf.a == 1.0
    assert obj.conf.b == 2.0

    obj = Parent(dict(type='ChildB', x=1, y=2))
    assert isinstance(obj, ChildB)
    assert obj.conf.x == 1
    assert obj.conf.y == 2


def test_scope_storage():
    scope = get_scope()
    assert scope['Configurable'] == Configurable
    assert scope['Parent'] == Parent
    assert scope['ChildA'] == ChildA
    assert scope['ChildB'] == ChildB

    set_scope({'Parent': Parent, 'A': ChildA, 'B': ChildB})
    assert get_scope() == {'Parent': Parent, 'A': ChildA, 'B': ChildB}


def test_subclass_forwarding_with_custom_scopes():
    set_scope({'Parent': Parent, 'A': ChildA, 'B': ChildB})

    obj = Parent(dict(type='A', a=1.0, b=2.0))
    assert isinstance(obj, ChildA)
    assert obj.conf.a == 1.0
    assert obj.conf.b == 2.0

    obj = Parent(dict(type='B', x=1, y=2))
    assert isinstance(obj, ChildB)
    assert obj.conf.x == 1
    assert obj.conf.y == 2

    set_scope(None)


def test_schema():
    validate = fastjsonschema.compile(get_schema())
    validate({'type': 'ChildA', 'a': 1, 'b': 2})
    validate({'type': 'ChildB', 'x': 0.1, 'y': 0.2})
    with pytest.raises(Exception):
        validate({'x': 0.1, 'y': 0.2})
    with pytest.raises(Exception):
        validate({'type': 'ChildB', 'x': 'some-string', 'y': 0.2})
