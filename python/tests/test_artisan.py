from pathlib import Path

from artisan._artisan import Artisan

#------------------------------------------------------------------------------

def test_artisan():
    assert Artisan().root_dir == Path('.')
    assert isinstance(Artisan().scope, dict)

    Artisan.push(scope={'int': int})
    assert Artisan.get_current().root_dir == Path('.')
    assert Artisan.get_current().scope == {'int': int}

    Artisan.push(scope={}, root_dir='test_dir')
    assert Artisan.get_current().root_dir == Path('test_dir')
    assert Artisan.get_current().scope == {}

    Artisan.pop()
    assert Artisan.get_current().root_dir == Path('.')
    assert Artisan.get_current().scope == {'int': int}

    with Artisan(scope={'float': float}, root_dir='test_dir_2'):
        assert Artisan.get_current().root_dir == Path('test_dir_2')
        assert Artisan.get_current().scope == {'float': float}
    assert Artisan.get_current().root_dir == Path('.')
    assert Artisan.get_current().scope == {'int': int}

    Artisan.pop()
    assert Artisan().root_dir == Path('.')
    assert isinstance(Artisan().scope, dict)
