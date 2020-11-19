'''
CBOR reader and writing functionality used by the `Artifact` class.

Exported definitions:
    PersistentArray (`numpy.memmap` subclass): A `memmap` backed by a CBOR file.
    PersistentList (`list` subclass): A `list` backed by a CBOR file.
    read_cbor_file (function): Read a CBOR file.
    write_object_as_cbor (function): Write an object to a CBOR file.
'''

from __future__ import annotations

import sys
from contextlib import contextmanager
from io import BufferedRandom
from itertools import chain
from os import SEEK_END, SEEK_SET
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence, Tuple, cast
from typing_extensions import Annotated

try:
    from fcntl import LOCK_EX, LOCK_SH, LOCK_UN, lockf
    locking_is_supported = True
except ImportError:
    locking_is_supported = False

import cbor2
import numpy as np

from ._namespaces import dictify, namespacify

__all__ = [
    'PersistentArray', 'PersistentList',
    'read_cbor_file', 'write_object_as_cbor']



#-- CBOR primitives ------------------------------------------------------------

MAJOR_TYPE_UINT = 0 << 5
MAJOR_TYPE_BYTE_STRING = 2 << 5
MAJOR_TYPE_ARRAY = 4 << 5
MAJOR_TYPE_TAG = 6 << 5

TAG_MULTIDIM_ARRAY = 40

INFO_NEXT_BYTE = 24
INFO_NEXT_2_BYTES = 25
INFO_NEXT_4_BYTES = 26
INFO_NEXT_8_BYTES = 27

dtypes_by_tag = {
    64: np.dtype('u1'),
    65: np.dtype('>u2'),
    66: np.dtype('>u4'),
    67: np.dtype('>u8'),
    68: np.dtype('u1'),
    69: np.dtype('<u2'),
    70: np.dtype('<u4'),
    71: np.dtype('<u8'),
    72: np.dtype('i1'),
    73: np.dtype('>i2'),
    74: np.dtype('>i4'),
    75: np.dtype('>i8'),
    77: np.dtype('<i2'),
    78: np.dtype('<i4'),
    79: np.dtype('<i8'),
    80: np.dtype('>f2'),
    81: np.dtype('>f4'),
    82: np.dtype('>f8'),
    84: np.dtype('<f2'),
    85: np.dtype('<f4'),
    86: np.dtype('<f8')}

tags_by_dtype = {
    dtype: tag
    for tag, dtype
    in dtypes_by_tag.items()}



#-- Persistent collections -----------------------------------------------------

class PersistentList(list):
    '''
    A `list` backed by a CBOR file.

    For performance, a `PersistentList` is invalidated when another object,
    including another `PersistentList`, writes to its backing file. An
    invalidated `PersistentList` is a potentially out-of-date read-only view
    into the file, and calling `append` or `extend` on it will corrupt the file.
    '''
    def __init__(self, file_: BufferedRandom, length: int) -> None:
        # Read the file into a buffer.
        file_.seek(0, SEEK_END)
        buf = bytearray(file_.tell())
        file_.seek(0, SEEK_SET)
        file_.readinto(buf)

        # Overwrite the header, in case it is currently being written to.
        header = list_header(length)
        buf[:len(header)] = header

        # Parse the buffer's contents as list items.
        super().__init__(namespacify(cbor2.loads(buf)))

        # Store the file pointer for `extend` calls.
        self._file = file_

    def __setitem__(self, index: object, value: object) -> None:
        raise TypeError('`PersistentList`s do not support item assignment')

    def __delitem__(self, index: object) -> None:
        raise TypeError('`PersistentList`s do not support item deletion')

    def extend(self, items: Iterable[object]) -> None:
        '''
        Extend list by appending elements from the iterable.
        '''
        # Coerce the collection of items to add into a sequence.
        items = items if isinstance(items, Sequence) else list(items)

        # Append the items, CBOR-encoded, to the backing file.
        data = b''.join(map(cbor2.dumps, dictify(items)))
        self._file.seek(0, SEEK_END)
        self._file.write(data)
        self._file.flush()

        # Update the header with the new list length.
        header = list_header(len(self) + len(items))
        with locking_header(self._file, LOCK_EX):
            self._file.seek(0, SEEK_SET)
            self._file.write(header)
            self._file.flush()

        # Add the items to `self`.
        super().extend(items)

    def append(self, item: object) -> None:
        '''
        Append object to the end of the list.
        '''
        self.extend([item])


class PersistentArray(np.memmap):
    '''
    A `numpy.memmap` backed by a CBOR file.

    The file must contain a row-major multidimensional array as defined in IETF
    RFC 8746. For performance, a `PersistentArray` is invalidated when another
    object, including another `PersistentArray`, writes to its backing file. An
    invalidated `PersistentArray` is a potentially out-of-date read-only view
    into the file, and calling `append` or `extend` on it will corrupt the file.

    Due to NumPy issue 4198 (https://github.com/numpy/numpy/issues/4198),
    `PersistenArray` extends `np.memmap` by proxy, meaning that it delegates
    attribute accesses and method calls to an internal `np.memmap` object
    instead of using Python's native subclassing mechanism.
    '''
    def extend(self, items: object) -> None:
        '''
        Extend the array by appending elements from `items`.
        '''

    def append(self, item: object) -> None:
        '''
        Append `item` to the array.
        '''


class PersistentArrayImpl:
    __name__ = 'PersistentArray'
    __qualname__ = 'PersistentArray'
    __doc__ = PersistentArray.__doc__

    def __init__(self,
                 file_: BufferedRandom,
                 shape: Tuple[int, ...],
                 dtype: np.dtype) -> None:
        self._file = file_
        self._memmap = np.memmap(
            file_, dtype, 'r+',
            data_offset(len(shape)),
            shape)

    def __array__(self) -> np.memmap:
        return self._memmap

    def extend(self, items: object) -> None:
        '''
        Extend the array by appending elements from `items`.
        '''
        # Convert `items` to a NumPy array.
        item_array = np.require(items, self._memmap.dtype, ['C_CONTIGUOUS'])

        # Raise an error if the arrays' shapes are not compatible.
        if self._memmap.ndim == 0:
            raise ValueError('scalars cannot be extended')
        if item_array.ndim == 0:
            raise ValueError('`items` must be a sequence')
        if item_array.shape[1:] != self._memmap.shape[1:]:
            raise ValueError('container and item shapes do not match')

        # Write data.
        self._file.seek(0, SEEK_END)
        self._file.write(item_array)
        self._file.flush()

        # Expand the memory-mapped array.
        dtype = self._memmap.dtype
        offset = data_offset(self._memmap.ndim)
        shape = (len(self._memmap) + len(item_array), *self._memmap.shape[1:])
        self._memmap = np.memmap(self._file, dtype, 'r+', offset, shape)

        # Overwrite the header.
        self._file.seek(0, SEEK_SET)
        with locking_header(self._file, LOCK_EX):
            self._file.write(ndarray_header(
                self._memmap.shape, self._memmap.dtype))
            self._file.flush()

    def append(self, item: object) -> None:
        '''
        Append `item` to the array.
        '''
        self.extend(np.asanyarray(item, self._memmap.dtype)[None])


class MemMapForwardingAttr:
    '''
    A descriptor that returns `obj._memmap.{key1}` when accessed.
    '''
    def __init__(self, key: str) -> None:
        self._key = key

    def __get__(self, obj: object, type_: type = None) -> Any:
        return getattr(getattr(obj, '_memmap'), self._key)


if 'sphinx' not in sys.modules:
    # Replace `PersistentArray` with `PersistentArrayImpl`
    # and add `np.memmap` methods and attribute-accessors.
    globals()['PersistentArray'] = PersistentArrayImpl
    for key in set(dir(np.memmap)) - set(dir(PersistentArrayImpl)):
        wrapper = MemMapForwardingAttr(key)
        wrapper.__doc__ = getattr(np.memmap, key).__doc__
        setattr(PersistentArrayImpl, key, wrapper)



#-- Reading --------------------------------------------------------------------

def read_cbor_file(path: Annotated[Path, '.cbor']) -> Any:
    '''
    Read a CBOR file.

    If the file encodes an indefinite-length array, a `PersistentList` will be
    returned.

    If the file encodes a 0–12-dimensional row-major array as specified in IETF
    RFC 8746, and the shape elements and byte string length are encoded as
    8-byte unsigned integers, a `PersistentArray` will be returned.

    Otherwise, a JSON-like object will be returned.
    '''
    # Defer to other readers if the path does not correspond to a CBOR file.
    if path.suffix != '.cbor':
        raise ValueError()

    # Open the specified file and read the first 128 bytes.
    f = cast(BufferedRandom, open(path, 'rb+'))
    with locking_header(f, LOCK_SH):
        header = cast(bytes, f.read(128))
    f.seek(0)

    # Try parsing the file as a `PersistentList`.
    try: return PersistentList(f, parse_list(header))
    except (ValueError, IndexError): pass

    # Try parsing the file as a `PersistentArray`.
    try: return PersistentArray(f, *parse_ndarray(header))
    except (ValueError, IndexError): pass

    # Parse the file using `cbor2`.
    return namespacify(cbor2.loads(f.read()))


def parse_list(buf: bytes) -> int:
    '''
    Parse the given buffer as the header of a `PersistentList` and return the
    number of items in the list.

    A `ValueError` is raised if an unexpected token is encountered and an
    `IndexError` is raised if the end of the buffer was reached while parsing.
    '''
    pos, size = parse_token(buf, 0, MAJOR_TYPE_ARRAY)
    fail_if(pos != 9)
    return size


def parse_ndarray(buf: bytes) -> Tuple[Tuple[int, ...], np.dtype]:
    '''
    Parse the given buffer as the header of a `PersistentArray` and return its
    shape and data type.

    A `ValueError` is raised if an unexpected token is encountered and an
    `IndexError` is raised if the end of the buffer was reached while parsing.
    '''
    # Check for a "multidimensional array" tag.
    pos, root_tag = parse_token(buf, 0, MAJOR_TYPE_TAG)
    fail_if(pos != 2 or root_tag != TAG_MULTIDIM_ARRAY)

    # Check whether the payload is a length-2 array.
    pos, root_len = parse_token(buf, pos, MAJOR_TYPE_ARRAY)
    fail_if(pos != 3 or root_len != 2)

    # Check for a shape array with up to 12 entries.
    pos, ndim = parse_token(buf, pos, MAJOR_TYPE_ARRAY)
    fail_if(pos != 4 or ndim > 12)

    # Read the shape array.
    shape = ndim * [0]
    for i in range(ndim):
        pos, shape[i] = parse_token(buf, pos, MAJOR_TYPE_UINT)
        fail_if(pos != 4 + 9 * (i + 1))

    # Check whether the shape array is followed by a typed data array.
    pos, dtype_tag = parse_token(buf, pos, MAJOR_TYPE_TAG)
    fail_if(pos != 6 + 9 * ndim or dtype_tag not in dtypes_by_tag)
    dtype = dtypes_by_tag[dtype_tag]

    # Check whether the data array is a byte string with an 8-byte size.
    pos, nbytes = parse_token(buf, pos, MAJOR_TYPE_BYTE_STRING)
    fail_if(pos != 15 + 9 * ndim or nbytes != np.prod(shape) * dtype.itemsize)

    # Return metadata if parsing succeeded.
    return tuple(shape), dtype


def parse_token(buf: bytes, pos: int,
                expected_major_type: int) -> Tuple[int, int]:
    '''
    Parse the CBOR token starting at `buf[pos]` and return the position of the
    next token in the buffer and the token's value.

    A `ValueError` is raised if the major type of the token does not match
    `expected_major_type`.
    '''
    major_type = buf[pos] & 0b1110_0000
    extra_info = buf[pos] & 0b0001_1111

    if major_type != expected_major_type:
        raise ValueError('CBOR parsing failed.')
    elif extra_info < INFO_NEXT_BYTE:
        return pos + 1, int(extra_info)
    elif extra_info == INFO_NEXT_BYTE:
        return pos + 2, int.from_bytes(buf[pos+1:pos+2], 'big')
    elif extra_info == INFO_NEXT_2_BYTES:
        return pos + 3, int.from_bytes(buf[pos+1:pos+3], 'big')
    elif extra_info == INFO_NEXT_4_BYTES:
        return pos + 5, int.from_bytes(buf[pos+1:pos+5], 'big')
    elif extra_info == INFO_NEXT_8_BYTES:
        return pos + 9, int.from_bytes(buf[pos+1:pos+9], 'big')
    else:
        raise ValueError('CBOR parsing failed.')


def fail_if(condition: bool) -> None:
    '''
    Raise a `ValueError` if the given condition is not true.
    '''
    if condition:
        raise ValueError('CBOR parsing failed')



#-- Writing --------------------------------------------------------------------

def write_object_as_cbor(path: Path, val: object) -> str:
    '''
    Write a JSON-encodable object or a NumPy array to a CBOR file.
    '''
    if isinstance(val, np.ndarray):
        write_ndarray(path, val)
    elif hasattr(val, '__array__'):
        write_ndarray(path, val.__array__()) # type: ignore
    elif isinstance(val, list):
        write_list(path, val)
    else:
        with open(path, 'wb') as f:
            cbor2.dump(dictify(val), f)
    return '.cbor'


def write_list(path: Path, list_: list) -> None:
    '''
    Write a list as a CBOR file containing an array.
    '''
    with open(path, 'wb') as f:
        f.write(list_header(len(list_)))
        for elem in list_:
            cbor2.dump(dictify(elem), f)
        f.flush()


def write_ndarray(path: Path, array: np.ndarray) -> None:
    '''
    Write an array as a CBOR file containing an row-major multidimensional
    array, as specified in IETF RFC 8746.

    The shape elements and the size of the byte string will be encoded as 8-byte
    unsigned integers.
    '''
    with open(path, 'wb') as f:
        f.write(ndarray_header(array.shape, array.dtype))
        f.write(np.ascontiguousarray(array).data)
        f.flush()


def list_header(length: int) -> bytes:
    '''
    Return the CBOR header for a list.
    '''
    return bytes((
        MAJOR_TYPE_ARRAY | INFO_NEXT_8_BYTES,
        *length.to_bytes(8, 'big')))


def ndarray_header(shape: Tuple[int, ...], dtype: np.dtype) -> bytes:
    '''
    Return the CBOR header for a multidimensional array.
    '''
    return bytes((
        MAJOR_TYPE_TAG | INFO_NEXT_BYTE,
        TAG_MULTIDIM_ARRAY,
        MAJOR_TYPE_ARRAY | 2,
        MAJOR_TYPE_ARRAY | len(shape),
        *chain.from_iterable(
            (MAJOR_TYPE_UINT | INFO_NEXT_8_BYTES,
             *n.to_bytes(8, 'big'))
            for n in shape),
        MAJOR_TYPE_TAG | INFO_NEXT_BYTE,
        tags_by_dtype[dtype],
        MAJOR_TYPE_BYTE_STRING | INFO_NEXT_8_BYTES,
        *int(np.prod(shape) * dtype.itemsize).to_bytes(8, 'big')))


def data_offset(ndim: int) -> int:
    '''
    Return the byte offset corresponding to the start of an `ndarray`'s data in
    a CBOR file.
    '''
    return 15 + 9 * ndim


@contextmanager
def locking_header(file_: BufferedRandom, mode: int) -> Iterator[None]:
    '''
    Return a context manager that acquires a lock on a CBOR file's header.
    '''
    if locking_is_supported:
        lockf(file_, mode, 128)
        yield
        lockf(file_, LOCK_UN)
    else:
        yield
