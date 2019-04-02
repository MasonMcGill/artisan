from copy import copy
from contextlib import contextmanager
import threading
from typing import Dict, Iterator, Optional as Opt
from dataclasses import dataclass

__all__ = ['GlobalConf', 'push_conf', 'pop_conf', 'using_conf', 'get_conf']

#------------------------------------------------------------------------------
# Thread-local configuration

# TODO: document, support paths

@dataclass
class GlobalConf:
    root_dir: str
    scope: Dict[str, object]


class _ConfStack(threading.local):
    def __init__(self) -> None:
        self.value = [GlobalConf(root_dir='.', scope={})]


_conf_stack = _ConfStack()


def get_conf() -> GlobalConf:
    return _conf_stack.value[-1]


def push_conf(conf: Opt[GlobalConf] = None, **updates: object) -> None:
    conf = get_conf() if conf is None else copy(conf)
    for key, val in updates.items():
        setattr(conf, key, val)
    _conf_stack.value.append(conf)

def pop_conf() -> GlobalConf:
    return _conf_stack.value.pop()


@contextmanager
def using_conf(conf: Opt[GlobalConf] = None,
               **updates: object) -> Iterator[None]:
    push_conf(conf, **updates); yield
    pop_conf()
