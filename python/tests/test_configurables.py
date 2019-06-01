from artisan._configurables import Configurable
from artisan._global_conf import using_conf

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


def test_custom_scopes():
    with using_conf(scope={'Parent': Parent, 'A': ChildA, 'B': ChildB}):
        obj = Parent(dict(type='A', a=1.0, b=2.0))
        assert isinstance(obj, ChildA)
        assert obj.conf.a == 1.0
        assert obj.conf.b == 2.0

        obj = Parent(dict(type='B', x=1, y=2))
        assert isinstance(obj, ChildB)
        assert obj.conf.x == 1
        assert obj.conf.y == 2
