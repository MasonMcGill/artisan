'''
A build system for explainable science
'''
from ._artifacts import Artifact, ArrayFile, EncodedFile, write_global_meta
from ._configurables import Configurable
from ._global_conf import Conf, push_conf, pop_conf, using_conf, get_conf
from ._http import serve

__all__ = [
    'Configurable', 'Artifact', 'ArrayFile', 'EncodedFile', 'write_global_meta',
    'Conf', 'push_conf', 'pop_conf', 'using_conf', 'get_conf',
    'serve'
]

#-- `__module__` rebinding ----------------------------------------------------

Configurable.__module__ = __name__
Artifact.__module__ = __name__
write_global_meta.__module__ = __name__
Conf.__module__ = __name__
push_conf.__module__ = __name__
pop_conf.__module__ = __name__
using_conf.__module__ = __name__
get_conf.__module__ = __name__
serve.__module__ = __name__

#-- Wonky alias docstring definitions -----------------------------------------

ArrayFile = ArrayFile; 'An alias for `h5py.Dataset`' # type: ignore
EncodedFile = EncodedFile; 'An alias for `pathlib.Path`' # type: ignore
