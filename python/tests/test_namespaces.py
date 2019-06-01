# WIP

from artisan._namespaces import Namespace, namespacify


def test_namespaces():
    ns = Namespace(a=1, b=2)
    assert 'a' in dir(ns) and 'b' in dir(ns)
    assert ns.a == 1 and ns['a'] == 1
    assert ns.b == 2 and ns['b'] == 2

    ns['a'] = 11; ns.b = 22
    assert 'a' in dir(ns) and 'b' in dir(ns)
    assert ns.a == 11 and ns['a'] == 11
    assert ns.b == 22 and ns['b'] == 22

    del ns['a']; del ns.b
    assert 'a' not in dir(ns) and 'b' not in dir(ns)


def test_namespacify():
    ...
