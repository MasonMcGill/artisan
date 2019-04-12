from copy import copy
from contextlib import contextmanager
import threading
from typing import Dict, Iterator, Optional as Opt
from dataclasses import dataclass

__all__ = [
    'GlobalConf', 'push_conf', 'pop_conf', 'using_conf', 'get_conf',
    'default_scope'
]

#------------------------------------------------------------------------------
# Thread-local configuration

# TODO: document, support paths

@dataclass
class GlobalConf:
    'A thread-local configuration for Artisan'
    root_dir: str
    scope: Dict[str, object]


class _ConfStack(threading.local):
    def __init__(self) -> None:
        self.value = [GlobalConf(root_dir='.', scope=default_scope)]


_conf_stack = _ConfStack()


def get_conf() -> GlobalConf:
    'Returns the active global configuration'
    return _conf_stack.value[-1]


def push_conf(conf: Opt[GlobalConf] = None, **updates: object) -> None:
    'Pushes a `GlobalConf` onto the stack, making it the active `GlobalConf`'
    conf = get_conf() if conf is None else copy(conf)
    for key, val in updates.items():
        setattr(conf, key, val)
    _conf_stack.value.append(conf)

def pop_conf() -> GlobalConf:
    'Pops the top `GlobalConf` off of the conf stack'
    if len(_conf_stack) == 1:
        raise IndexError(
            'The default `GlobalConf` can\'t be removed.\n\n'
            'i.e. You can\'t pop. The fun must stop here.'
        )
    return _conf_stack.value.pop()


@contextmanager
def using_conf(conf: Opt[GlobalConf] = None,
               **updates: object) -> Iterator[None]:
    'Returns a context manager that executes its body with the `conf` active'
    push_conf(conf, **updates); yield
    pop_conf()

#------------------------------------------------------------------------------
# Default scope

default_scope: Dict[str, object] = {}