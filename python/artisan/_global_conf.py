from copy import copy
from contextlib import contextmanager
from dataclasses import dataclass
import threading
from typing import Dict, Iterator as Iter, Optional as Opt

__all__ = [
    'Conf', 'push_conf', 'pop_conf',
    'using_conf', 'get_conf', 'default_scope'
]

#-- Thread-local configuration ------------------------------------------------

@dataclass
class Conf:
    '''
    A thread-scoped Artisan configuration

    Attributes:
        root_dir: The default directory for artifact creation, and the
            directory that will be searched for matches when an artifact is
            instantiated from a specification
        scope: The mapping used to resolve `type`s in specifications during
            configurable object instantiation
    '''
    root_dir: str
    scope: Dict[str, type]


class ConfStack(threading.local):
    def __init__(self):
        super().__init__()
        self.contents = [Conf(root_dir='.', scope=default_scope)]


default_scope: Dict[str, type] = {}
conf_stack = ConfStack()


def get_conf() -> Conf:
    'Returns the active configuration'
    return conf_stack.contents[-1]


def push_conf(conf: Opt[Conf] = None, **updates: object) -> None:
    'Pushes a `Conf` onto the stack, making it the active `Conf`'
    conf = copy(get_conf() if conf is None else conf)
    for key, val in updates.items():
        setattr(conf, key, val)
    for val in conf.scope.values():
        assert isinstance(val, type)
    conf_stack.contents.append(conf)

def pop_conf() -> Conf:
    'Pops the top `Conf` off of the stack'
    if len(conf_stack.contents) == 1:
        raise IndexError(
            'The default `Conf` can\'t be removed.\n\n'
            'i.e. You may no longer pop. The fun must stop here.'
        )
    return conf_stack.contents.pop()


@contextmanager
def using_conf(conf: Opt[Conf] = None, **updates: object) -> Iter[None]:
    'Returns a context manager that executes its body with `conf` active'
    push_conf(conf, **updates); yield
    pop_conf()
