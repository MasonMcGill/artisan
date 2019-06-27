from pathlib import Path

import h5py as h5
import numpy as np

from artisan._artifacts import Artifact

#-- [Base class tests] Empty artifacts ----------------------------------------

def test_empty_artifact_with_existing_dir(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    assert a.path == tmp_path
    assert a.conf == {}
    assert a.meta == {'spec': None, 'status': 'done'}
    assert len(a) == 0
    assert list(a) == []
    assert isinstance(a.nonexistent_entry, Artifact)


def test_empty_artifact_with_nonexistent_dir(tmp_path: Path) -> None:
    a = Artifact(tmp_path / 'new_dir')
    assert a.path == tmp_path / 'new_dir'
    assert a.conf == {}
    assert a.meta == {'spec': None, 'status': 'done'}
    assert len(a) == 0
    assert list(a) == []
    assert isinstance(a.nonexistent_entry, Artifact)
    assert not (tmp_path / 'new_dir').exists()

#-- [Base class tests] Entry assignment ---------------------------------------

def test_float_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = 1.5
    a.b = 2.5
    a['c'] = 3.5
    a['c'] = 4.5
    assert len(a) == 2
    assert 'b' in a
    assert 'c' in a
    assert (tmp_path / 'b.h5').is_file()
    assert (tmp_path / 'c.h5').is_file()
    assert isinstance(a.b, h5.Dataset)
    assert isinstance(a.c, h5.Dataset)
    assert np.array_equal(a.b, 2.5)
    assert np.array_equal(a.c, 4.5)


def test_byte_string_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = b'bee'
    a.b = b'buzz'
    a['c'] = b'sea'
    a['c'] = b'ahoy!'
    assert len(a) == 2
    assert 'b' in a
    assert 'c' in a
    assert (tmp_path / 'b.h5').is_file()
    assert (tmp_path / 'c.h5').is_file()
    assert isinstance(a.b, h5.Dataset)
    assert isinstance(a.c, h5.Dataset)
    assert np.array_equal(a.b, b'buzz')
    assert np.array_equal(a.c, b'ahoy!')


def test_list_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = [1, 2, 3]
    a.b = [4, 5, 6]
    a['c'] = [[7, 8], [9, 10]]
    a['c'] = [[11, 12, 13], [14, 15, 16]]
    assert len(a) == 2
    assert 'b' in a
    assert 'c' in a
    assert (tmp_path / 'b.h5').is_file()
    assert (tmp_path / 'c.h5').is_file()
    assert isinstance(a.b, h5.Dataset)
    assert isinstance(a.c, h5.Dataset)
    assert np.array_equal(a.b, [4, 5, 6])
    assert np.array_equal(a.c, [[11, 12, 13], [14, 15, 16]])


def test_array_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = np.ones((2, 3), dtype='float32')
    a.b = np.zeros((4, 5, 6), dtype='float32')
    a['c'] = np.ones((4, 5, 6), dtype='float32')
    a['c'] = np.ones((2, 3), dtype='uint16')
    assert len(a) == 2
    assert 'b' in a
    assert 'c' in a
    assert (tmp_path / 'b.h5').is_file()
    assert (tmp_path / 'c.h5').is_file()
    assert isinstance(a.b, h5.Dataset)
    assert isinstance(a.c, h5.Dataset)
    assert np.array_equal(a.b, np.zeros((4, 5, 6), dtype='float32'))
    assert np.array_equal(a.c, np.ones((2, 3), dtype='uint16'))
    assert a.b.dtype == 'float32'
    assert a.c.dtype == 'uint16'


def test_path_assignment(tmp_path: Path) -> None:
    path_b0 = tmp_path / 'some_path.txt'
    path_b1 = tmp_path / 'some_other_path.txt'
    path_c0 = tmp_path / 'yet_another_path.txt'
    path_c1 = tmp_path / 'gosh_so_many_paths.txt'
    path_b0.write_text('[Some worthless nonsense]')
    path_b1.write_text('I am bee text.')
    path_c0.write_text('[The complete works of Shakespeare]')
    path_c1.write_text('I am sea text.')
    a = Artifact(tmp_path / 'artifact')
    a.b__txt = path_b0
    a.b__txt = path_b1
    a['c.txt'] = path_c0
    a['c.txt'] = path_c1
    assert len(a) == 2
    assert 'b.txt' in a
    assert 'c.txt' in a
    assert (tmp_path / 'artifact/b.txt').is_file()
    assert (tmp_path / 'artifact/c.txt').is_file()
    assert isinstance(a.b__txt, Path)
    assert isinstance(a.c__txt, Path)
    assert a.b__txt.read_text() == 'I am bee text.'
    assert a.c__txt.read_text() == 'I am sea text.'


def test_dict_assignment(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.dict = dict(a=[1, 2, 3], b=dict(c=[4], d=[5, 6]))
    assert (tmp_path / 'dict/a.h5').is_file()
    assert (tmp_path / 'dict/b/c.h5').is_file()
    assert (tmp_path / 'dict/b/d.h5').is_file()
    assert 'dict' in a
    assert 'a' in a.dict
    assert 'b' in a.dict
    assert 'c' in a.dict.b # type: ignore
    assert 'd' in a.dict.b # type: ignore
    assert 'c' not in a.dict
    assert 'd' not in a.dict
    assert isinstance(a.dict, Artifact)
    assert isinstance(a.dict.a, h5.Dataset)
    assert isinstance(a.dict.b, Artifact)
    assert isinstance(a.dict.b.c, h5.Dataset)
    assert isinstance(a.dict.b.d, h5.Dataset)
    assert np.array_equal(a.dict.a, [1, 2, 3])
    assert np.array_equal(a.dict.b.c, [4])
    assert np.array_equal(a.dict.b.d, [5, 6])


def test_artifact_assignment(tmp_path: Path) -> None:
    (tmp_path / 'text.txt').write_text('effigy')
    a_src = Artifact(tmp_path / 'a_src')
    a_src.b.c = b'bee sea'
    a_src.d.e = [1, 2, 3, 4]
    a_src.f.g__txt = tmp_path / 'text.txt'
    a_dst = Artifact(tmp_path / 'a_dst')
    a_dst.a = a_src
    assert len(a_dst) == 1
    assert len(a_dst.a) == 3
    assert len(a_dst.a.b) == 1
    assert len(a_dst.a.d) == 1
    assert len(a_dst.a.f) == 1
    assert (tmp_path / 'a_dst/a/b/c.h5').is_file()
    assert (tmp_path / 'a_dst/a/d/e.h5').is_file()
    assert (tmp_path / 'a_dst/a/f/g.txt').is_file()
    assert 'b' in a_dst.a
    assert 'c' in a_dst.a.b
    assert 'd' in a_dst.a
    assert 'e' in a_dst.a.d
    assert 'f' in a_dst.a
    assert 'g.txt' in a_dst.a.f
    assert isinstance(a_dst.a.b, Artifact)
    assert isinstance(a_dst.a.b.c, h5.Dataset)
    assert isinstance(a_dst.a.d, Artifact)
    assert isinstance(a_dst.a.d.e, h5.Dataset)
    assert isinstance(a_dst.a.f, Artifact)
    assert isinstance(a_dst.a.f.g__txt, Path)
    assert np.array_equal(a_dst.a.b.c, b'bee sea')
    assert np.array_equal(a_dst.a.d.e, [1, 2, 3, 4])
    assert a_dst.a.f.g__txt.read_text() == 'effigy'

#-- [Base class tests] Entry extension ----------------------------------------

# def test_list_extension(tmp_path: Path) -> None:
#     a = Artifact(tmp_path)
#     a.b = [1, 2, 3]
#     a.extend('b', [4, 5, 6])
#     a.extend('c', [[7, 8], [9, 10]])
#     a.extend('c', [[11, 12]])
#     assert len(a) == 2
#     assert 'b' in a
#     assert 'c' in a
#     assert (tmp_path / 'b.h5').is_file()
#     assert (tmp_path / 'c.h5').is_file()
#     assert isinstance(a.b, h5.Dataset)
#     assert isinstance(a.c, h5.Dataset)
#     assert np.array_equal(a.b, [1, 2, 3, 4, 5, 6])
#     assert np.array_equal(a.c, [[7, 8], [9, 10], [11, 12]])


# def test_array_extension(tmp_path: Path) -> None:
#     a = Artifact(tmp_path)
#     a.b = np.float32([1, 2, 3])
#     a.extend('b', np.float32([4, 5, 6]))
#     a.extend('c', np.uint16([[7, 8], [9, 10]]))
#     a.extend('c', np.uint16([[11, 12]]))
#     assert len(a) == 2
#     assert 'b' in a
#     assert 'c' in a
#     assert (tmp_path / 'b.h5').is_file()
#     assert (tmp_path / 'c.h5').is_file()
#     assert isinstance(a.b, h5.Dataset)
#     assert isinstance(a.c, h5.Dataset)
#     assert np.array_equal(a.b, [1, 2, 3, 4, 5, 6])
#     assert np.array_equal(a.c, [[7, 8], [9, 10], [11, 12]])
#     assert a.b.dtype == 'float32'
#     assert a.c.dtype == 'uint16'


def test_path_extension(tmp_path: Path) -> None:
    ...


def test_dict_extension(tmp_path: Path) -> None:
    ...


def test_artifact_extension(tmp_path: Path) -> None:
    ...

#-- [Base class tests] Entry deletion -----------------------------------------

def test_array_file_deletion(tmp_path: Path) -> None:
    a = Artifact(tmp_path)
    a.b = [1, 2, 3]
    a.c = b'four five six'
    del a.b
    del a['c']
    assert len(a) == 0
    assert 'b' not in a
    assert 'c' not in a


def test_opaque_file_deletion(tmp_path: Path) -> None:
    ...


def test_artifact_deletion(tmp_path: Path) -> None:
    ...

#-- [Subclass tests] Construction ---------------------------------------------

def test_construction_from_path(tmp_path: Path) -> None:
    '''
    - Case 1: (path_given, exists)
    - Case 2: (path_given, does_not_exists)
    '''


def test_construction_from_conf(tmp_path: Path) -> None:
    '''
    - Case 3: (spec_given, exists)
    - Case 4: (spec_given, does_not_exist)
    '''


def test_construction_from_path_and_conf(tmp_path: Path) -> None:
    '''
    - Case 5: (path_given, spec_given, exists_and_matches)
    - Case 6: (path_given, spec_given, exists_and_does_not_match)
    - Case 7: (path_given, spec_given, does_not_exist)
    '''

#-- [Subclass tests] Build customization --------------------------------------

class TypedArtifactA(Artifact):
    def build(self) -> None:
        self.field = self.conf.prop


class TypedArtifactB(Artifact):
    def build(self, conf) -> None:
        self.field = conf.prop


def test_build_customization(tmp_path: Path) -> None:
    '''
    - Calling `build`, passing in `conf`
    - Calling `build` without passing in `conf`
    '''
