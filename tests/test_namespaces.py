from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from artisan import Namespace
from artisan._namespaces import namespacify, dictify


def test_repr() -> None:
    '''
    Test that namespaces print nicely.
    '''
    ns_a = Namespace()
    assert repr(ns_a) == 'Namespace()'

    ns_b = Namespace(
        list = [
            Namespace(a=0, b=1),
            Namespace(c=2, d=3)
        ],
        dict = Namespace(
            a = Namespace(a=0, b=1),
            b = Namespace(c=2, d=3)
        ),
        namespace = Namespace(
            c = Namespace(a=0, b=1),
            d = Namespace(c=2, d=3)
        )
    )
    assert repr(ns_b) == (
        'Namespace(\n'
        '  list = [Namespace(a=0, b=1), Namespace(c=2, d=3)],\n'
        '  dict = Namespace(a=Namespace(a=0, b=1), b=Namespace(c=2, d=3)),\n'
        '  namespace = Namespace(c=Namespace(a=0, b=1), d=Namespace(c=2, d=3))\n'
        ')'
    )

    ns_c = Namespace(
        bool = False,
        int = 0,
        float = 1.1,
        large_entry = Namespace(
            list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            str = 'The quick brown fox jumped over the lazy dog.'
        )
    )
    assert repr(ns_c) == (
        'Namespace(\n'
        '  bool = False,\n'
        '  int = 0,\n'
        '  float = 1.1,\n'
        '  large_entry = Namespace(\n'
        '    list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],\n'
        '    str = \'The quick brown fox jumped over the lazy dog.\'\n'
        '  )\n'
        ')'
    )


def test_json_compatibility() -> None:
    '''
    Test `dictify` and `namespacify`.
    '''
    dict_ = {
        'bool': False,
        'int': 1,
        'float': 2.2,
        'str': 'three',
        'list': [0, 1, 2],
        'dict': {'a': 0, 'b': 1}
    }

    ns = Namespace(
        bool = False,
        int = 1,
        float = 2.2,
        str = 'three',
        list = [0, 1, 2],
        dict = Namespace(a=0, b=1)
    )

    assert dictify(ns) == dict_
    assert isinstance(dictify(ns)['dict'], dict)

    assert namespacify(dict_) == ns
    assert isinstance(namespacify(dict_).dict, Namespace)


def test_json_compatibility_with_nesting() -> None:
    '''
    Test that `dictify` and `namespacify` also work recursively.
    '''
    dict_ = {
        'list': [
            {'a': 0, 'b': 1},
            {'c': 2, 'd': 3}
        ],
        'dict': {
            'a': {'a': 0, 'b': 1},
            'b': {'c': 2, 'd': 3}
        }
    }

    ns = Namespace(
        list = [
            Namespace(a=0, b=1),
            Namespace(c=2, d=3)
        ],
        dict = Namespace(
            a = Namespace(a=0, b=1),
            b = Namespace(c=2, d=3)
        )
    )

    assert dictify(ns) == dict_
    assert isinstance(dictify(ns)['dict'], dict)
    assert isinstance(dictify(ns)['dict']['a'], dict)
    assert isinstance(dictify(ns)['dict']['b'], dict)

    assert namespacify(dict_) == ns
    assert isinstance(namespacify(dict_).dict, Namespace)
    assert isinstance(namespacify(dict_).dict.a, Namespace)
    assert isinstance(namespacify(dict_).dict.b, Namespace)


def test_path_encoding(tmp_path: Path) -> None:
    '''
    Test converting paths to path strings.
    '''
    path = Path('x/y.ext')
    encode_path = lambda path: f'@/{path}'
    assert dictify(path, encode_path) == '@/x/y.ext'
    assert dictify([path], encode_path) == ['@/x/y.ext']
    assert dictify(Namespace(a=path), encode_path) == {'a': '@/x/y.ext'}


def test_artifact_encoding(tmp_path: Path) -> None:
    '''
    Test converting paths strings to path-like objects.
    '''
    path = Path('x/y.ext')
    decode_path = lambda path_str: Path(path_str[2:])
    assert namespacify('@/x/y.ext', decode_path) == path
    assert namespacify(['@/x/y.ext'], decode_path) == [path]
    assert namespacify({'a': '@/x/y.ext'}, decode_path) == Namespace(a=path)
