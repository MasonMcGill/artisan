from ._namespaces import Namespace
from ._artifacts import Configurable, Artifact
from ._global_conf import GlobalConf, push_conf, pop_conf, using_conf, get_conf
from ._http import  serve

__all__ = [
    'Namespace', 'Configurable', 'Artifact',
    'GlobalConf', 'push_conf', 'pop_conf', 'using_conf', 'get_conf',
    'serve'
]

for sym in __all__:
    globals()[sym].__module__ = __name__
