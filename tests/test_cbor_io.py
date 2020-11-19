from pathlib import Path
from string import ascii_letters
from tempfile import NamedTemporaryFile
from typing import List, Tuple
from typing_extensions import Literal

import numpy as np
from hypothesis import given
from hypothesis.strategies import (
    SearchStrategy, binary, booleans, builds, dictionaries, floats,
    integers, lists, none, one_of, recursive, sampled_from, text, tuples)
from numpy import ndarray as Array
from numpy.testing import assert_equal

from artisan import (
    Namespace, PersistentArray, PersistentList,
    read_cbor_file, write_object_as_cbor)



#-- Search strategies ----------------------------------------------------------

def cbor_encodable_objects() -> SearchStrategy[object]:
    '''
    Return a search strategy that samples CBOR-encodable objects.
    '''
    return recursive(
        base = (none() | booleans() | integers() |
                floats(allow_nan=False) | binary() | text()),
        extend = lambda s: lists(s, max_size=4) | namespaces(s),
        max_leaves = 16)


def cbor_lists() -> SearchStrategy[list]:
    '''
    Return a search strategy that samples lists of CBOR-encodable objects.
    '''
    return lists(cbor_encodable_objects())


def namespaces(s: SearchStrategy) -> SearchStrategy[Namespace]:
    '''
    Return a search strategy that samples
    namespaces with fields sampled from `s`.
    '''
    return builds(lambda attrs: Namespace(**attrs),
                  dictionaries(text(ascii_letters), s, max_size=4))


def concat_methods() -> SearchStrategy[str]:
    '''
    Return a search strategy that samples CBOR-encodable objects.
    '''
    return sampled_from(['append', 'extend', 'extend-via-iter'])


def array_shapes() -> SearchStrategy[List[int]]:
    '''
    Return a search strategy that samples NumPy array shapes.
    '''
    return one_of(
        lists(integers(0, 1024), min_size=0, max_size=1),
        lists(integers(0, 32), min_size=2, max_size=2),
        lists(integers(0, 10), min_size=3, max_size=3),
        lists(integers(0, 5), min_size=4, max_size=4))


def dtypes() -> SearchStrategy[np.dtype]:
    '''
    Return a search strategy that samples NumPy data types.
    '''
    return sampled_from(list(map(np.dtype, [
        'u1', '>u2', '>u4', '>u8', '<u2', '<u4', '<u8',
        'i1', '>i2', '>i4', '>i8', '<i2', '<i4', '<i8',
        '>f2', '>f4', '>f8', '<f2', '<f4', '<f8'])))



#-- Tests ----------------------------------------------------------------------

@given(cbor_encodable_objects())
def test_basic_use(content: object) -> None:
    '''
    Test reading and writing objects supported by the core CBOR specification.
    '''
    with NamedTemporaryFile(suffix='.cbor') as f:
        write_object_as_cbor(Path(f.name), content)
        assert_equal(read_cbor_file(Path(f.name)), content)


@given(cbor_lists(), lists(tuples(concat_methods(), cbor_lists()), max_size=4))
def test_persistent_lists(head: list, tail: List[Tuple[str, list]]) -> None:
    '''
    Test `PersistentList.append` and `PersistentList.extend`.
    '''
    with NamedTemporaryFile(suffix='.cbor') as f:
        write_object_as_cbor(Path(f.name), head)
        standard_list = head.copy()
        persistent_list = read_cbor_file(Path(f.name))
        assert isinstance(persistent_list, PersistentList)
        assert_equal(persistent_list, standard_list)

        for i, (concat_method, section) in enumerate(tail):
            if concat_method == 'append':
                for element in section:
                    standard_list.append(element)
                    persistent_list.append(element)
            elif concat_method == 'extend':
                standard_list.extend(section)
                persistent_list.extend(section)
            elif concat_method == 'extend-via-iter':
                standard_list.extend(iter(section))
                persistent_list.extend(iter(section))

            assert isinstance(read_cbor_file(Path(f.name)), PersistentList)
            assert_equal(read_cbor_file(Path(f.name)), standard_list)
            assert_equal(persistent_list, standard_list)


@given(lists(integers(0, 8), min_size=2, max_size=4), array_shapes(), dtypes())
def test_persistent_arrays(array_lengths: List[int],
                           elem_shape: List[int],
                           dtype: np.dtype) -> None:
    '''
    Test `PersistentArray.append` and `PersistentArray.extend`.
    '''
    np.random.seed(0)
    arrays = [
        np.array(2**20 * np.random.randn(length, *elem_shape), dtype)
        for length in array_lengths]

    with NamedTemporaryFile(suffix='.cbor') as f:
        write_object_as_cbor(Path(f.name), arrays[0])
        persistent_array = read_cbor_file(Path(f.name))
        assert isinstance(persistent_array, PersistentArray)
        assert_equal(persistent_array, arrays[0])

        for i in range(1, len(arrays)):
            if np.random.rand() < 0.5:
                for element in arrays[i]:
                    persistent_array.append(element)
            else:
                persistent_array.extend(arrays[i])

            expected_result = np.concatenate(arrays[:i+1])
            assert isinstance(read_cbor_file(Path(f.name)), PersistentArray)
            assert_equal(read_cbor_file(Path(f.name)), expected_result)
            assert_equal(persistent_array, expected_result)


def test_extension_by_proxy() -> None:
    '''
    Test the workaround for NumPy issue 4198.
    '''
    with NamedTemporaryFile(suffix='.cbor') as f:
        write_object_as_cbor(Path(f.name), np.arange(20).reshape(4, 5))
        persistent_array = read_cbor_file(Path(f.name))

        assert persistent_array.min() == 0
        assert persistent_array.max() == 19
        assert_equal(persistent_array + 3, (np.arange(20).reshape(4, 5) + 3))
        assert_equal(2 * persistent_array, (2 * np.arange(20).reshape(4, 5)))

        assert type(persistent_array[0]) == np.memmap
        assert persistent_array[0].shape == (5,)
        assert type(persistent_array[1:3]) == np.memmap
        assert persistent_array[1:3].shape == (2, 5)
        assert type(persistent_array.view(np.memmap)) == np.memmap
        assert type(persistent_array.view(np.ndarray)) == np.ndarray
