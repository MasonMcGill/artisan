from copy import copy
from contextlib import contextmanager
from dataclasses import dataclass
import threading
from typing import Dict, Iterator as Iter, Optional as Opt

__all__ = ['Conf', 'conf_stack', 'default_scope']

#-- Thread-local configuration ------------------------------------------------

@dataclass
class Conf:
    '''
    Options for Artisan's behavior

    Attributes:
        root_dir: The default directory for artifact creation, and the
            directory that will be searched for matches when an artifact is
            instantiated from a specification
        scope: The mapping used to resolve `type`s in specifications during
            artifact instantiation
    '''
    root_dir: str
    scope: Dict[str, object]


class ConfStack:
    '''
    A thread-local stack of Artisan configurations

    At any given time, the top `Conf` on the stack will be used to determine
    Artisan's behavior.
    '''
    def __init__(self) -> None:
        self._tl = threading.local()
        self._tl.list = [Conf(root_dir='.', scope=default_scope)]

    def get(self) -> Conf:
        'Returns the active configuration'
        return self._tl.list[-1]

    def push(self, conf: Opt[Conf] = None, **updates: object) -> None:
        'Pushes a `Conf` onto the stack, making it the active `Conf`'
        conf = self.get() if conf is None else copy(conf)
        for key, val in updates.items():
            setattr(conf, key, val)
        self._tl.list.append(conf)

    def pop(self) -> Conf:
        'Pops the top `Conf` off of the stack'
        if len(self._tl.list) == 1:
            raise IndexError(
                'The default `Conf` can\'t be removed.\n\n'
                'i.e. You may no longer pop. The fun must stop here.'
            )
        return self._tl.list.pop()

    @contextmanager
    def using(self, conf: Opt[Conf] = None, **updates: object) -> Iter[None]:
        'Returns a context manager that executes its body with `conf` active'
        self.push(conf, **updates); yield
        self.pop()


default_scope: Dict[str, object] = {}
conf_stack = ConfStack()
