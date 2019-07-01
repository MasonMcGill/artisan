'''
A build system for explainable science
'''

from ._artifacts import Artifact, ArrayFile, EncodedFile
from ._artisan import Artisan
from ._configurables import Configurable
from ._namespaces import Namespace

__all__ = [
    'ArrayFile', 'Artifact', 'Configurable',
    'EncodedFile', 'Namespace'
]

#-- `__module__` rebinding ----------------------------------------------------

Configurable.__module__ = __name__
Artifact.__module__ = __name__
ArrayFile.__module__ = __name__
Namespace.__module__ = __name__
Artisan.__module__ = __name__

#-- Wonky alias docstring definitions -----------------------------------------

EncodedFile = EncodedFile; 'An alias for `pathlib.Path`' # type: ignore
