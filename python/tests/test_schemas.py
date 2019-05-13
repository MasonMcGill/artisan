# WIP
from artisan._schemas import schema_from_type


'''
Things to test:

- no docstring/single-line docstring/multi-line docstring
- yes/no docstrings extensions
- yes/no conf
- conf props
    - type:
        - primitives (bool, int, float, str)
        - List[T]
        - Dict[str, T]
        - Optional[T]
        - Union[T...]
        - Specs
        - none
    - default value:
        - primitives (bool, int, float, str)
        - List[T]
        - Dict[str, T]
        - Optional[T]
        - Union[T...]
        - none
    - postfix annotation:
        - str
        - dict
        - (str, dict)
        - (dict, str)
        - none
- yes/no ignored statements
'''


class TypeWithPropTypeAnnotations:
    class Conf:
        my_bool: bool
        my_int: int
        my_float: float
        my_str: str
        my_list_of_bool: List[bool]
        my_dict_of_bool: Dict[str, bool]
        my_optional_bool: Optional[bool]
        my_bool_or_int: Union[bool, int]


def test_prop_type_annotations():
    assert schema_from_type(ArtifactWithPropTypeAnnotations) == {
        ...
    }


...