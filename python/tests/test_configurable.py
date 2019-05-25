from artisan._configurable import Configurable
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

#-- Tests ---------------------------------------------------------------------

def test_direct_instantiation():
    obj = ChildA(dict(x=1, y=2))
    assert isinstance(obj, ChildA)
    assert obj.conf.x == 1
    assert obj.conf.y == 2


def test_subclass_forwarding():
    obj = Parent(dict(type='ChildA', x=1, y=2))
    assert isinstance(obj, ChildA)
    assert obj.conf.x == 1
    assert obj.conf.y == 2

    obj = Parent(dict(type='ChildB', a=1.0, b=2.0))
    assert isinstance(obj, ChildB)
    assert obj.conf.a == 1.0
    assert obj.conf.b == 2.0


def test_custom_scopes():
    with using_conf(scope={'Parent': Parent, 'A': ChildA, 'B': ChildB}):
        obj = Parent(dict(type='A', x=1, y=2))
        assert isinstance(obj, ChildA)
        assert obj.conf.x == 1
        assert obj.conf.y == 2

        obj = Parent(dict(type='B', a=1.0, b=2.0))
        assert isinstance(obj, ChildB)
        assert obj.conf.a == 1.0
        assert obj.conf.b == 2.0
