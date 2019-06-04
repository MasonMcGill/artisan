from artisan._global_conf import get_conf, push_conf, pop_conf, using_conf

#------------------------------------------------------------------------------

def test_conf():
    assert get_conf().root_dir == '.'
    assert isinstance(get_conf().scope, dict)

    push_conf(scope={'int': int})
    assert get_conf().root_dir == '.'
    assert get_conf().scope == {'int': int}

    push_conf(scope={}, root_dir='test_dir')
    assert get_conf().root_dir == 'test_dir'
    assert get_conf().scope == {}

    pop_conf()
    assert get_conf().root_dir == '.'
    assert get_conf().scope == {'int': int}

    with using_conf(scope={'float': float}, root_dir='test_dir_2'):
        assert get_conf().root_dir == 'test_dir_2'
        assert get_conf().scope == {'float': float}

