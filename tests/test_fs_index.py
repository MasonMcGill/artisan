import json, gc, shutil
from pathlib import Path
from typing import Set
from weakref import finalize

from artisan._fs_index import DirIndex, TreeIndex


def test_dir_indices(tmp_path: Path) -> None:
    '''
    Test `DirIndex`.
    '''
    (tmp_path / 'a').mkdir()
    (tmp_path / 'b').mkdir()
    (tmp_path / 'b/_meta_.json').write_text('{"spec": {}, "events": []}')
    (tmp_path / 'c').mkdir()
    (tmp_path / 'c/_meta_.json').write_text('[invalid JSON]')
    (tmp_path / 'c/x.txt').write_text('[x text]')
    (tmp_path / 'c/y.txt').write_text('[y text]')

    root_index = DirIndex(tmp_path)
    assert root_index.path == tmp_path
    assert root_index.parent == DirIndex(tmp_path.parent)
    assert set(root_index.children) == set()
    assert root_index.get_meta() is None
    assert set(root_index.get_entry_names()) == {'a', 'b', 'c'}
    assert root_index.get_entry_path('a') == tmp_path / 'a'
    assert root_index.get_entry_path('b') == tmp_path / 'b'
    assert root_index.get_entry_path('c') == tmp_path / 'c'
    assert set(root_index.get_artifacts()) == {DirIndex(tmp_path / 'b')}

    gc.collect()
    a_index = DirIndex(tmp_path / 'a')
    assert set(root_index.children) == {a_index}
    assert a_index.path == tmp_path / 'a'
    assert a_index.parent is root_index
    assert set(a_index.children) == set()
    assert a_index.get_meta() is None
    assert set(a_index.get_entry_names()) == set()
    assert set(a_index.get_artifacts()) == set()

    gc.collect()
    b_index = DirIndex(tmp_path / 'b')
    assert set(root_index.children) == {a_index, b_index}
    assert b_index.path == tmp_path / 'b'
    assert b_index.parent is root_index
    assert set(b_index.children) == set()
    assert b_index.get_meta() == {'spec': {}, 'events': []}
    assert set(b_index.get_entry_names()) == {'_meta_'}
    assert set(b_index.get_artifacts()) == {b_index}

    del b_index; gc.collect()
    c_index = DirIndex(tmp_path / 'c')
    assert set(root_index.children) == {a_index, c_index}
    assert c_index.path == tmp_path / 'c'
    assert c_index.parent is root_index
    assert set(c_index.children) == set()
    assert isinstance(c_index.get_meta(), Exception)
    assert set(c_index.get_entry_names()) == {'_meta_', 'x', 'y'}
    assert c_index.get_entry_path('x') == tmp_path / 'c/x.txt'
    assert c_index.get_entry_path('y') == tmp_path / 'c/y.txt'
    assert set(c_index.get_artifacts()) == set()


def test_tree_indices(tmp_path: Path) -> None:
    '''
    Test `TreeIndex`.
    '''
    (tmp_path / 'a').mkdir()
    (tmp_path / 'b').mkdir()
    (tmp_path / 'b/_meta_.json').write_text('{"spec": {}, "events": []}')
    (tmp_path / 'c').mkdir()
    (tmp_path / 'c/_meta_.json').write_text('[invalid JSON]')
    (tmp_path / 'c/x.txt').write_text('[x text]')
    (tmp_path / 'c/y.txt').write_text('[y text]')

    collected_index_names: Set[str] = set()
    def finalize_dir_index(name: str) -> None:
        collected_index_names.add(name)

    a_index = DirIndex(tmp_path / 'a')
    finalize(a_index, finalize_dir_index, 'a')

    tree_index = TreeIndex(tmp_path)
    assert tree_index.root == DirIndex(tmp_path)

    del a_index; gc.collect()
    assert collected_index_names == set()

    b_index = DirIndex(tmp_path / 'b')
    finalize(b_index, finalize_dir_index, 'b')

    del b_index; gc.collect()
    assert collected_index_names == set()

    shutil.rmtree(tmp_path / 'b')
    assert set(tree_index.root.get_entry_names()) == {'a', 'c'}
    assert collected_index_names == {'b'}

    c_index = DirIndex(tmp_path / 'c')
    finalize(c_index, finalize_dir_index, 'c')

    del tree_index; gc.collect()
    assert collected_index_names == {'a', 'b'}

    del c_index; gc.collect()
    assert collected_index_names == {'a', 'b', 'c'}
