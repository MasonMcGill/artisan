from typing import Any, Dict, List, Mapping, cast

from ._global_conf import get_conf

__all__ = ['Namespace', 'namespacify']

#-- Namespaces ----------------------------------------------------------------

class Namespace(Dict[str, Any]):
    '''
    A `dict` that supports accessing items as attributes
    '''
    def __dir__(self) -> List[str]:
        return list(set([*dict.__dir__(self), *dict.__iter__(self)]))

    def __getattr__(self, key: str) -> Any:
        return dict.__getitem__(self, key)

    def __setattr__(self, key: str, val: object) -> None:
        dict.__setitem__(self, key, val)

    def __delattr__(self, key: str) -> None:
        dict.__delitem__(self, key)

    @property
    def __dict__(self) -> dict: # type: ignore
        return self

    def __repr__(self) -> str:
        def single_line_repr(elem: object) -> str:
            if isinstance(elem, list):
                return '[' + ', '.join(map(single_line_repr, elem)) + ']'
            elif isinstance(elem, Namespace):
                return (
                    'Namespace('
                    + ', '.join(
                        f'{k}={single_line_repr(v)}'
                        for k, v in elem.items()
                    )
                    + ')'
                )
            else:
                return repr(elem).replace('\n', ' ')

        def repr_in_context(elem: object, curr_col: int, indent: int) -> str:
            sl_repr = single_line_repr(elem)
            if len(sl_repr) <= 80 - curr_col:
                return sl_repr
            elif isinstance(elem, list):
                return (
                    '[\n'
                    + ' ' * (indent + 2)
                    + (',\n' + ' ' * (indent + 2)).join(
                        repr_in_context(e, indent + 2, indent + 2)
                        for e in elem
                    )
                    + '\n' + ' ' * indent + ']'
                )
            elif isinstance(elem, Namespace):
                return (
                    'Namespace(\n'
                    + ' ' * (indent + 2)
                    + (',\n' + ' ' * (indent + 2)).join(
                        f'{k} = '
                        + repr_in_context(v, indent + 5 + len(k), indent + 2)
                        for k, v in elem.items()
                    )
                    + '\n' + ' ' * indent + ')'
                )
            else:
                return repr(elem)

        return repr_in_context(self, 0, 0)


def namespacify(obj: object) -> object:
    '''
    Recursively convert mappings (item access only) and ad-hoc namespaces
    (attribute access only) to `Namespace`s (both item and element access).
    '''
    if isinstance(obj, (type(None), bool, int, float, str)):
        return obj
    elif isinstance(obj, type):
        return next(
            (sym for sym, t in get_conf().scope.items() if t is obj),
            '<UnknownType>'
        )
    elif isinstance(obj, list):
        return [namespacify(v) for v in obj]
    elif isinstance(obj, Mapping):
        return Namespace({k: namespacify(obj[k]) for k in obj})
    else:
        return namespacify(vars(obj))
